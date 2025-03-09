import os
import json
import requests
import uuid
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass
from dotenv import load_dotenv
from urllib.parse import urlencode

import jwt
from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.responses import RedirectResponse, Response
from fastapi.security import APIKeyCookie
from pydantic import BaseModel

from db import db, User, ADMIN_EMAIL
from routes.utils import BASE_URL, FRONTEND_URL

load_dotenv()


SECRET_KEY = os.getenv("SALT", "gamergate-salt")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


app = FastAPI()

cookie_scheme = APIKeyCookie(name="session_token", auto_error=False)


class AuthError(Exception):
    pass


@dataclass
class AuthenticatedUser(User):
    admin: bool

    def to_dict(self):
        # Convert to dictionary for JSON serialization
        user_dict = vars(self)
        return user_dict


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


async def get_current_user(request: Request) -> AuthenticatedUser:
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = verify_session_token(token)
        user = await db.get_user_by_id(user_id)
        if user is None:
            raise AuthError("User not found")

        # Add admin field to the user object, determined by email
        is_admin = user.email == ADMIN_EMAIL

        # Create AuthenticatedUser with explicit typing to satisfy PyRight
        user_with_admin = AuthenticatedUser(admin=is_admin, **vars(user))
        return user_with_admin
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/me")
async def user_me(request: Request):
    token = request.cookies.get("session_token")
    user_id = None
    user = None

    # Try to get user from token if it exists
    if token:
        try:
            user_id = verify_session_token(token)
            user = await db.get_user_by_id(user_id)
        except AuthError:
            # Invalid token, will create a dummy user
            pass

    # If no valid user found, create a dummy user
    if user is None:
        # Create a dummy user for non-authenticated visitors
        dummy_id = str(uuid.uuid4())
        dummy_user = User(
            id=dummy_id,
            created_at=datetime.now().isoformat(),
            messages_left=0,
            username=None,
            email=None,
            avatar_id=None,
        )

        # Store the dummy user in the database
        await db.create_user(dummy_user)

        # Create a session token for the dummy user
        auth_token = create_session_token(dummy_id)

        # Add admin field to the dummy user (will be False)
        dummy_user_with_admin = AuthenticatedUser(admin=False, **vars(dummy_user))

        response = {
            "user": dummy_user_with_admin.to_dict(),
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

    # Add admin field to the user object for existing users
    is_admin = user.email == ADMIN_EMAIL
    games = await db.get_games_by_owner_id(user.id)

    # Return existing user data with admin field
    return {
        "user": AuthenticatedUser(admin=is_admin, **vars(user)).to_dict(),
        "games": games,
    }


class UpdateInfoRequest(BaseModel):
    field: str
    username: str = None


@app.post("/update-info")
async def update_user_info(
    request: UpdateInfoRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update user information (currently only username)."""
    if request.field != "username" or not request.username:
        raise HTTPException(
            status_code=400, detail="Currently only username updates are supported"
        )

    # Check if the username is already taken
    users = await db.get_all_users()
    for user in users:
        if user.username == request.username and user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Username is already taken")

    # Update the username
    await db.update_user_by_id(current_user.id, username=request.username)
    return {"successful": True}


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
        "redirect_uri": f"{BASE_URL}/api/user/google/callback",
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

    user_id = None
    existing_user = await db.get_user_by_email(email)
    if existing_user is not None:
        # If it's an existing user, pass through
        user_id = existing_user.id
        user = existing_user

        # Update avatar if needed
        if user.avatar_id != avatar_id:
            await db.update_user_by_id(user_id, avatar_id=avatar_id)

    else:
        # If it's a new user, check for a dummy user_id passed through
        session_token = request.cookies.get("session_token")
        if session_token:
            try:
                user_id = verify_session_token(session_token)
            except AuthError:
                # If token is invalid, we'll still proceed with the state parameter
                pass

        # If no session token or invalid, try to get from state parameter
        if not user_id:
            user_id = request.query_params.get("state")

        user = None if not user_id else await db.get_user_by_id(user_id)
        if user is not None and user_id is not None:
            await db.update_user_by_id(
                user_id,
                avatar_id=avatar_id if avatar_id else None,
                email=email,
                username=email.split("@")[0],
            )
        else:
            # Otherwise, create a new user. This shouldn't ever happen tbh.
            user_id = user_id or str(uuid.uuid4())
            new_user = User(
                id=user_id,
                username=email.split("@")[0],
                email=email,
                created_at=datetime.now().isoformat(),
                avatar_id=avatar_id if avatar_id else None,
                messages_left=10,
            )
            await db.create_user(new_user)

    assert user_id is not None
    auth_token = create_session_token(user_id)
    response = RedirectResponse(f"{FRONTEND_URL}/")
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
        "redirect_uri": f"{BASE_URL}/api/user/google/callback",
        "response_type": "code",
        "scope": "email",
        "state": state,  # Pass the user_id as state
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(auth_url)


@app.get("/logout")
async def user_logout():
    response = RedirectResponse(f"{FRONTEND_URL}/")
    response.delete_cookie("session_token")
    return response
