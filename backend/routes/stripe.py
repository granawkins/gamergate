import os
from datetime import datetime
from uuid import uuid4

import stripe
from fastapi import FastAPI, Depends, Request, HTTPException

from db import db, Transaction
from routes.utils import FRONTEND_URL, ENV
from routes.user import get_current_user, AuthenticatedUser

# This is your test secret API key.
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = FastAPI()

price_ids = {
    "gamergate-50-credits": {
        "PROD": "price_1QzVQpL7uUhJKkiA5UOiCuK8",
        "DEV": "price_1QzVi5L7uUhJKkiAHWDtfXrR",
        "QA": "price_1QzVi5L7uUhJKkiAHWDtfXrR",
    }
}


@app.post("/create-checkout-session")
async def create_checkout_session(
    request: Request, current_user: AuthenticatedUser = Depends(get_current_user)
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
            metadata={"user_id": current_user.id},
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
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id in metadata")
    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    current_time = datetime.now().isoformat()

    # Create or update the transaction record
    transaction = await db.get_transaction_by_session_id(session_id)
    credit_user = session.status == "complete" and (
        not transaction or transaction.status != "complete"
    )
    if not transaction:
        transaction_id = str(uuid4())
        transaction = Transaction(
            id=transaction_id,
            user_id=user.id,
            session_id=session_id,
            status=session.status or "error",
            created_at=current_time,
            updated_at=current_time,
            amount=50,
            description="50 credits purchase",
        )
        await db.create_transaction(transaction)
    elif credit_user:
        await db.update_transaction_by_id(
            transaction.id,
            status=session.status,
            updated_at=current_time,
            amount=50,
            description="50 credits purchase",
        )

    # Update the user's credits if the transaction is complete
    credits = user.credits
    if credit_user:
        credits += 50
        await db.update_user_by_id(user.id, credits=credits)

    # Get the user's email from stripe
    customer_email = None
    if hasattr(session, "customer_details") and session.customer_details is not None:
        if hasattr(session.customer_details, "email"):
            customer_email = session.customer_details.email

    return {
        "status": session.status,
        "customer_email": customer_email,
        "session_id": session.id,
        "credits": credits,
    }
