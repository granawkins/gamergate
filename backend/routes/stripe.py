import os

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
        "DEV": "price_1QzUGDQ6WPPiKRLMuML4pvOw",
        "QA": "price_1QzUGDQ6WPPiKRLMuML4pvOw",
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

    messages_left = None
    if session.status == "complete":
        _db = await db.get()
        assert hasattr(session, "metadata") and isinstance(session.metadata, dict)
        user_id = session.metadata.get("user_id")
        if user_id and user_id in _db["users"]:
            messages_left = _db["users"][user_id]["messages_left"] + 100
            _db["users"][user_id]["messages_left"] = messages_left
            await db.set(_db)

    return {
        "status": session.status,
        "customer_email": session.customer_details.email,  # type: ignore
        "session_id": session.id,
        "messages_left": messages_left,
    }
