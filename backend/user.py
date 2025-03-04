import os
import requests
import uuid
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
from urllib.parse import urlencode

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse, Response
from fastapi.security import APIKeyCookie

from db import db, User, UserWithOptionalFields

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
async def user_me(current_user: User = Depends(get_current_user)):
    _db = await db.get()
    return {
        "user": current_user,
        "games": [
            g for g in _db["games"].values() if g["owner_id"] == current_user["id"]
        ],
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
    user = next((u for u in _db["users"].values() if u["email"] == email), None)
    
    # Variable to store the user ID for the token
    user_id: str
    
    if not user:
        # Create base user with required fields
        user_id = str(uuid.uuid4())
        base_user: User = {
            "id": user_id,
            "username": email.split("@")[0],
            "email": email,
            "created_at": datetime.now().isoformat(),
        }
        # Add optional fields
        user_with_avatar = dict(base_user)  # Create a copy as a regular dict
        if avatar_id:
            user_with_avatar["avatar_id"] = avatar_id
            
        _db["users"][user_id] = user_with_avatar
        await db.set(_db)
    else:
        user_id = user["id"]
        if avatar_id and user.get("avatar_id") != avatar_id:
            # Update avatar if it has changed
            updated_user = dict(user)  # Create a copy as a regular dict
            updated_user["avatar_id"] = avatar_id
            _db["users"][user_id] = updated_user
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
async def user_login():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": "http://localhost:8000/api/user/google/callback",
        "response_type": "code",
        "scope": "email",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(auth_url)


@app.get("/logout")
async def user_logout():
    response = RedirectResponse("http://localhost:5173/")
    response.delete_cookie("session_token")
    return response


@app.get("/avatar-proxy")
async def avatar_proxy(url: str):
    """
    Proxy endpoint to fetch avatar images from external sources.
    This helps bypass CORS restrictions.
    """
    try:
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch avatar")
        
        # Get the content type from the response
        content_type = response.headers.get("Content-Type", "image/jpeg")
        
        # Return the image with the appropriate content type
        return Response(content=response.content, media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching avatar: {str(e)}")
