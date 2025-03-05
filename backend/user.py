import os
import json
import requests
import uuid
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
from urllib.parse import urlencode

import jwt
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse, Response
from fastapi.security import APIKeyCookie

from db import db, User

load_dotenv()


SECRET_KEY = os.getenv("SALT", "gamergate-salt")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


app = FastAPI()

cookie_scheme = APIKeyCookie(name="session_token", auto_error=False)


class AuthError(Exception):
    pass


def create_session_token(user_id: str) -> str:
    expires_delta = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    expire = datetime.now(UTC) + expires_delta
    to_encode = {"sub": user_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_session_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthError("Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise AuthError("Invalid token")


async def get_current_user(request: Request) -> User:
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = verify_session_token(token)
        _db = await db.get()
        user = _db["users"].get(user_id)
        if user is None:
            raise AuthError("User not found")
        return user
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/me")
async def user_me(request: Request):
    token = request.cookies.get("session_token")
    _db = await db.get()

    user_id = None
    user = None

    # Try to get user from token if it exists
    if token:
        try:
            user_id = verify_session_token(token)
            user = _db["users"].get(user_id)
        except AuthError:
            # Invalid token, will create a dummy user
            pass

    # If no valid user found, create a dummy user
    if user is None:
        # Create a dummy user for non-authenticated visitors
        dummy_id = str(uuid.uuid4())
        dummy_user: User = {
            "id": dummy_id,
            "created_at": datetime.now().isoformat(),
            "messages_left": 0,
            "username": None,
            "email": None,
            "avatar_id": None,
        }

        # Store the dummy user in the database
        _db["users"][dummy_id] = dummy_user
        await db.set(_db)

        # Create a session token for the dummy user
        auth_token = create_session_token(dummy_id)
        response = {
            "user": dummy_user,
            "games": [],
        }

        # Return the response with the session token cookie
        return_response = Response(
            content=json.dumps(response), media_type="application/json"
        )
        return_response.set_cookie(
            key="session_token",
            value=auth_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=3600 * 24 * 30,
        )
        return return_response

    # Return existing user data
    return {
        "user": user,
        "games": [g for g in _db["games"].values() if g["owner_id"] == user["id"]],
    }


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


@app.get("/google/callback")
async def user_google_callback(request: Request):
    token_params = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": request.query_params["code"],
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost:8000/api/user/google/callback",
    }
    token_response = requests.post(GOOGLE_TOKEN_URL, data=token_params)
    token = token_response.json().get("access_token")

    user_response = requests.get(
        GOOGLE_USER_INFO_URL,
        headers={"Authorization": f"Bearer {token}"},
    )
    user_data = user_response.json()
    email = user_data.get("email")
    avatar_id = user_data.get("picture")  # Get avatar URL from Google

    _db = await db.get()

    # Get the dummy user ID from the session token
    # We assume we always have a dummy user at this point
    dummy_user_id = ""
    session_token = request.cookies.get("session_token")
    if session_token:
        try:
            dummy_user_id = verify_session_token(session_token)
        except AuthError:
            # If token is invalid, we'll still proceed with the state parameter
            pass

    # If no session token or invalid, try to get from state parameter
    if not dummy_user_id:
        dummy_user_id = request.query_params.get("state", "")

    # Check if a user with this email already exists
    existing_user = next(
        (u for u in _db["users"].values() if u.get("email") == email), None
    )

    # Variable to store the user ID for the token
    user_id: str

    if existing_user:
        # User with this email already exists
        user_id = existing_user["id"]
        user = existing_user

        # Update avatar if needed
        if "avatar_id" not in user or user["avatar_id"] != avatar_id:
            user["avatar_id"] = avatar_id if avatar_id else None
            _db["users"][user_id] = user
            await db.set(_db)
    elif dummy_user_id and dummy_user_id in _db["users"]:
        # Update the dummy user with the Google account info
        user_id = dummy_user_id
        dummy_user = _db["users"][dummy_user_id]

        # This is a first-time login for this dummy user, update with Google info
        dummy_user["email"] = email
        dummy_user["username"] = email.split("@")[0]
        dummy_user["avatar_id"] = avatar_id if avatar_id else None

        # Set messages_left to 10 for first-time login
        dummy_user["messages_left"] = 10

        _db["users"][user_id] = dummy_user
        await db.set(_db)
    else:
        # Create a new user with all fields
        user_id = str(uuid.uuid4())
        new_user: User = {
            "id": user_id,
            "username": email.split("@")[0],
            "email": email,
            "created_at": datetime.now().isoformat(),
            "avatar_id": avatar_id if avatar_id else None,
            "messages_left": 10,
        }

        _db["users"][user_id] = new_user
        await db.set(_db)

    auth_token = create_session_token(user_id)
    response = RedirectResponse("http://localhost:5173/")
    response.set_cookie(
        key="session_token",
        value=auth_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=3600 * 24 * 30,
    )
    return response


@app.get("/login")
async def user_login(request: Request):
    # Get the current user ID from the session token if it exists
    user_id = None
    session_token = request.cookies.get("session_token")
    if session_token:
        try:
            user_id = verify_session_token(session_token)
        except AuthError:
            # Invalid token, proceed without user_id
            pass

    # Include the user_id in the state parameter if it exists
    state = user_id if user_id else ""

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": "http://localhost:8000/api/user/google/callback",
        "response_type": "code",
        "scope": "email",
        "state": state,  # Pass the user_id as state
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(auth_url)


@app.get("/logout")
async def user_logout():
    response = RedirectResponse("http://localhost:5173/")
    response.delete_cookie("session_token")
    return response
