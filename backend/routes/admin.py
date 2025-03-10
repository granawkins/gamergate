from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
from uuid import uuid4

from db import db, Transaction
from routes.user import AuthenticatedUser, get_current_user

app = FastAPI()


class UserStats(BaseModel):
    id: str
    username: Optional[str]
    email: Optional[str]
    created_at: str
    credits: int
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
    credits_to_add: int  # Can be negative to remove credits


@app.get("/stats")
async def get_admin_stats(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Get statistics for all users and transactions.
    Only accessible by admin users.
    """
    if not current_user.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    users = await db.get_all_users()
    games = await db.get_all_games()
    messages = await db.get_all_messages()
    transactions = await db.get_all_transactions()

    # Process user stats
    user_stats = []
    for user in users:
        # Calculate number of projects for this user
        user_games = {g.id for g in games if g.owner_id == user.id}
        n_projects = len(user_games)
        total_messages = sum(1 for m in messages if m.game_id in user_games)

        user_stats.append(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at,
                "credits": user.credits,
                "total_messages": total_messages,
                "n_projects": n_projects,
            }
        )

    # Process transaction data
    transaction_stats = []
    for transaction in transactions:
        # Get the email for the user
        user_email = None
        user_id = transaction.user_id
        user = next((u for u in users if u.id == user_id), None)
        if user:
            user_email = user.email

        transaction_stats.append(
            {
                "id": transaction.id,
                "user_id": user_id,
                "email": user_email,
                "status": transaction.status,
                "created_at": transaction.created_at,
                "updated_at": transaction.updated_at,
                "amount": transaction.amount,
                "description": transaction.description,
            }
        )

    # Sort transactions by updated_at (newest first)
    transaction_stats.sort(key=lambda x: x["updated_at"], reverse=True)

    # Collect message costs by model
    message_costs_by_model: Dict[str, List[float]] = {}
    for message in messages:
        cost = message.cost
        model = message.model
        if cost is not None and cost > 0 and model:
            if model not in message_costs_by_model:
                message_costs_by_model[model] = []
            message_costs_by_model[model].append(cost)

    # Calculate cost statistics for each model
    cost_stats = {}
    for model, costs in message_costs_by_model.items():
        if costs:
            costs.sort()
            count = len(costs)
            total = sum(costs)
            mean = total / count

            # Calculate percentiles manually
            if count >= 10:
                p10_idx = max(0, int(count * 0.1) - 1)
                p25_idx = max(0, int(count * 0.25) - 1)
                p75_idx = min(count - 1, int(count * 0.75))
                p90_idx = min(count - 1, int(count * 0.9))
                p10 = costs[p10_idx]
                p25 = costs[p25_idx]
                p75 = costs[p75_idx]
                p90 = costs[p90_idx]
            else:
                p10, p25, p75, p90 = 0, 0, 0, 0

            cost_stats[model] = {
                "count": count,
                "total": round(total, 6),
                "mean": round(mean, 6),
                "p90": round(p90, 6),
                "p75": round(p75, 6),
                "p25": round(p25, 6),
                "p10": round(p10, 6),
            }

    return {
        "users": user_stats,
        "transactions": transaction_stats,
        "message_costs": cost_stats,
    }


@app.post("/update-credits")
async def update_user_credits(
    request: MessageUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Update a user's credits count.
    Only accessible by admin users.
    """
    if not current_user.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    target_user = await db.get_user_by_id(request.user_id)
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    target_credits = max(0, target_user.credits + request.credits_to_add)
    await db.update_user_by_id(request.user_id, credits=target_credits)

    current_time = datetime.now().isoformat()
    transaction_id = str(uuid4())
    await db.create_transaction(
        Transaction(
            id=transaction_id,
            user_id=request.user_id,
            session_id="",
            amount=request.credits_to_add,
            created_at=current_time,
            updated_at=current_time,
            status="complete",
            description="Manual adjustment",
        )
    )

    return {
        "user_id": request.user_id,
        "credits": target_credits,
    }
