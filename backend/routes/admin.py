from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import uuid4

from db import db, User
from routes.user import get_current_user

app = FastAPI()


class UserStats(BaseModel):
    id: str
    username: Optional[str]
    email: Optional[str]
    created_at: str
    messages_left: int
    total_messages: int
    n_projects: int


class TransactionInfo(BaseModel):
    id: str
    user_id: str
    email: Optional[str]
    status: str
    created_at: str
    updated_at: str
    amount: int
    description: str


class MessageUpdateRequest(BaseModel):
    user_id: str
    messages_to_add: int  # Can be negative to remove messages


@app.get("/stats")
async def get_admin_stats(current_user: User = Depends(get_current_user)):
    """
    Get statistics for all users and transactions.
    Only accessible by admin users.
    """
    if not current_user.get("admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    _db = await db.get()
    users = _db["users"]
    games = _db["games"]
    transactions = _db.get("transactions", {})

    # Process user stats
    user_stats = []
    for user_id, user in users.items():
        # Calculate number of projects for this user
        user_projects = [g for g in games.values() if g["owner_id"] == user_id]
        n_projects = len(user_projects)

        # Calculate total messages sent by this user
        total_messages = 0
        for game in user_projects:
            user_messages = [
                m for m in game.get("messages", []) if m.get("role") == "user"
            ]
            total_messages += len(user_messages)

        user_stats.append(
            {
                "id": user_id,
                "username": user.get("username"),
                "email": user.get("email"),
                "created_at": user.get("created_at"),
                "messages_left": user.get("messages_left", 0),
                "total_messages": total_messages,
                "n_projects": n_projects,
            }
        )

    # Process transaction data
    transaction_stats = []
    for transaction_id, transaction in transactions.items():
        # Get the email for the user
        user_email = None
        user_id = transaction.get("user_id")
        if user_id and user_id in users:
            user_email = users[user_id].get("email")

        transaction_stats.append(
            {
                "id": transaction_id,
                "user_id": user_id,
                "email": user_email,
                "status": transaction.get("status", "unknown"),
                "created_at": transaction.get("created_at", ""),
                "updated_at": transaction.get("updated_at", ""),
                "amount": transaction.get("amount", 0),
                "description": transaction.get("description", "Unknown transaction"),
            }
        )

    # Sort transactions by updated_at (newest first)
    transaction_stats.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

    return {"users": user_stats, "transactions": transaction_stats}


@app.post("/update-messages")
async def update_user_messages(
    request: MessageUpdateRequest, current_user: User = Depends(get_current_user)
):
    """
    Update a user's messages_left count.
    Only accessible by admin users.
    """
    if not current_user.get("admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    _db = await db.get()
    users = _db["users"]

    if request.user_id not in users:
        raise HTTPException(status_code=404, detail="User not found")

    # Update the user's message count
    users[request.user_id]["messages_left"] += request.messages_to_add

    # Ensure messages_left doesn't go below 0
    if users[request.user_id]["messages_left"] < 0:
        users[request.user_id]["messages_left"] = 0

    # Create a transaction record for this adjustment
    current_time = datetime.now().isoformat()
    transaction_id = str(uuid4())
    transaction = {
        "id": transaction_id,
        "user_id": request.user_id,
        "session_id": "manual",  # Use "manual" to indicate it's not from Stripe
        "status": "complete",
        "created_at": current_time,
        "updated_at": current_time,
        "amount": request.messages_to_add,
        "description": "Manual adjustment",
    }

    # Add the transaction to the database
    if "transactions" not in _db:
        _db["transactions"] = {}
    _db["transactions"][transaction_id] = transaction

    await db.set(_db)

    return {
        "user_id": request.user_id,
        "messages_left": users[request.user_id]["messages_left"],
    }
