import os
from datetime import datetime
from uuid import uuid4

import stripe
from fastapi import FastAPI, Depends, Request, HTTPException

from db import User, db
from routes.utils import FRONTEND_URL, ENV
from routes.user import get_current_user

# This is your test secret API key.
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = FastAPI()

price_ids = {
    "gamergate-100-messages": {
        "PROD": "price_1QzVQpL7uUhJKkiA5UOiCuK8",
        "DEV": "price_1QzVi5L7uUhJKkiAHWDtfXrR",
        "QA": "price_1QzVi5L7uUhJKkiAHWDtfXrR",
    }
}


@app.post("/create-checkout-session")
async def create_checkout_session(
    request: Request, current_user: User = Depends(get_current_user)
):
    data = await request.json()
    product_id = data["product_id"]
    quantity = data.get("quantity", 1)
    price_id = price_ids.get(product_id, {}).get(ENV)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Invalid price ID: {product_id}")

    try:
        session = stripe.checkout.Session.create(
            ui_mode="embedded",
            line_items=[
                {
                    "price": price_id,
                    "quantity": quantity,
                },
            ],
            mode="payment",
            return_url=FRONTEND_URL + "/return?session_id={CHECKOUT_SESSION_ID}",
            metadata={"user_id": current_user["id"]},
        )
    except Exception as e:
        return str(e)

    return {"clientSecret": session.client_secret}


@app.get("/session-status")
async def session_status(request: Request):
    # Get session_id from query parameters instead of request body
    session_id = request.query_params.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id parameter")
    session = await stripe.checkout.Session.retrieve_async(session_id)
    assert hasattr(session, "metadata") and isinstance(session.metadata, dict)

    # Validate the user_id
    user_id = session.metadata.get("user_id")
    _db = await db.get()
    if not user_id or user_id not in _db["users"]:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    current_time = datetime.now().isoformat()

    # Create or update the transaction record
    transaction = next(
        (tx for tx in _db["transactions"].values() if tx["session_id"] == session_id),
        None,
    )
    credit_user = session.status == "complete" and (
        not transaction or transaction["status"] != "complete"
    )
    if not transaction:
        transaction_id = str(uuid4())
        transaction = {
            "id": transaction_id,
            "user_id": user_id,
            "session_id": session_id,
            "status": session.status,
            "created_at": current_time,
            "updated_at": current_time,
        }
        _db["transactions"][transaction_id] = transaction
        await db.set(_db)
    elif credit_user:
        transaction["status"] = session.status
        transaction["updated_at"] = current_time
        _db["transactions"][transaction["id"]] = transaction
        await db.set(_db)

    # Update the user's message count if the transaction is complete
    messages_left = _db["users"][user_id]["messages_left"]
    if credit_user:
        messages_left += 100
        _db["users"][user_id]["messages_left"] = messages_left
        await db.set(_db)
    # Get the user's email from stripe
    customer_email = None
    if hasattr(session, "customer_details") and session.customer_details is not None:
        if hasattr(session.customer_details, "email"):
            customer_email = session.customer_details.email

    return {
        "status": session.status,
        "customer_email": customer_email,
        "session_id": session.id,
        "messages_left": messages_left,
    }
