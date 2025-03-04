from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime
import subprocess
from uuid import uuid4

from db import db, GAMES_PATH, Message, User
from user import app as user_app, get_current_user
from assistant import get_completion_background, extract_message

app = FastAPI(root_path="/api")

app.mount("/user", user_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Default Vite dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageRequest(BaseModel):
    message: str


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/games")
async def get_games():
    _db = await db.get()
    return list(_db["games"].values())


@app.get("/games/{game_id}/play")
async def serve_game(game_id: str):
    """Serve the HTML file for a specific game with added resize handling."""
    # Check if the game exists
    _db = await db.get()
    if game_id not in _db["games"]:
        raise HTTPException(
            status_code=404, detail=f"Game with ID '{game_id}' not found"
        )

    game = _db["games"][game_id]
    game_dir = GAMES_PATH / game_id

    # First check if there's a file named after the game
    game_file = game_dir / f"{game['name']}.html"
    if not game_file.exists():
        # If not, look for any HTML file in the directory
        html_files = list(game_dir.glob("*.html"))
        if html_files:
            game_file = html_files[0]
        else:
            # If no HTML file is found, return 404
            raise HTTPException(
                status_code=404, detail=f"Game '{game['name']}' not found"
            )

    # Read the HTML content
    with open(game_file, "r") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)


@app.delete("/games/{game_id}")
async def delete_game(game_id: str, current_user: User = Depends(get_current_user)):
    """
    Delete a game by ID. Only the owner can delete their game.
    """
    _db = await db.get()

    # Check if the game exists
    if game_id not in _db["games"]:
        raise HTTPException(
            status_code=404, detail=f"Game with ID '{game_id}' not found"
        )

    game = _db["games"][game_id]

    # Check if the user is the owner
    if current_user["id"] != game["owner_id"]:
        raise HTTPException(
            status_code=403, detail="You are not the owner of this game"
        )

    # Delete the game from the database
    del _db["games"][game_id]
    await db.set(_db)

    return JSONResponse(
        status_code=200,
        content={"message": f"Game '{game['name']}' deleted successfully"},
    )


@app.get("/chat/{game_id}")
async def get_chat_messages(
    game_id: str, current_user: User = Depends(get_current_user)
):
    """
    Get all chat messages and game info for a specific game.
    """
    _db = await db.get()

    # Check if the game exists
    if game_id not in _db["games"]:
        raise HTTPException(
            status_code=404, detail=f"Game with ID '{game_id}' not found"
        )

    game = _db["games"][game_id]

    # Check if the user is the owner
    if current_user["id"] != game["owner_id"]:
        raise HTTPException(
            status_code=403, detail="You are not the owner of this game"
        )

    messages = game.get("messages")
    for message in messages:
        if message.get("role") == "assistant" and message.get("status") != "error":
            message["text"] = extract_message(message["text"], allow_incomplete=True)
    return {"messages": messages, "gameInfo": game}


@app.post("/chat/{game_id}")
async def handle_chat(
    game_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Handle chat messages for the game editor.
    Store the message and return a response with the game info immediately,
    then run the completion in the background with a semaphore.
    """
    # Check if the game exists
    _db = await db.get()
    body = await request.json()
    user_message_text = body["message"]

    # Check if the game exists
    if game_id not in _db["games"]:
        raise HTTPException(
            status_code=404, detail=f"Game with ID '{game_id}' not found"
        )

    game = _db["games"][game_id]

    # Check if the user is the owner
    if current_user["id"] != game["owner_id"]:
        raise HTTPException(
            status_code=403, detail="You are not the owner of this game"
        )

    # Create user message
    user_message: Message = {
        "id": str(uuid4()),
        "text": user_message_text,
        "role": "user",
        "timestamp": datetime.now().isoformat(),
        "cost": 0,
    }
    _db["games"][game_id]["messages"].append(user_message)

    assistant_message: Message = {
        "id": str(uuid4()),
        "text": "",
        "role": "assistant",
        "timestamp": datetime.now().isoformat(),
        "cost": 0,
        "status": "processing",
    }
    _db["games"][game_id]["messages"].append(assistant_message)
    await db.set(_db)

    # Start the completion in the background
    get_completion_background(game_id)

    # Return the empty assistant message and game info immediately
    return {"message": assistant_message, "gameInfo": game}


@app.get("/chat/{game_id}/message/{message_id}")
async def get_message(
    game_id: str, message_id: str, current_user: User = Depends(get_current_user)
):
    """
    Get a specific message by ID.
    Used for polling the status of an assistant message.
    """
    _db = await db.get()

    # Check if the game exists
    if game_id not in _db["games"]:
        raise HTTPException(
            status_code=404, detail=f"Game with ID '{game_id}' not found"
        )

    game = _db["games"][game_id]

    # Check if the user is the owner
    if current_user["id"] != game["owner_id"]:
        raise HTTPException(
            status_code=403, detail="You are not the owner of this game"
        )

    # Find the message by ID
    for message in game.get("messages", []):
        if message["id"] == message_id:
            if message.get("role") == "assistant" and message.get("status") != "error":
                message["text"] = extract_message(
                    message["text"], allow_incomplete=True
                )
            return {"message": message}

    raise HTTPException(status_code=404, detail=f"Message '{message_id}' not found")


class UndoRequest(BaseModel):
    message_id: str


@app.post("/chat/{game_id}/undo")
async def undo_last_commit(
    game_id: str, request: UndoRequest, current_user: User = Depends(get_current_user)
):
    """
    Undo the commit associated with a specific message and delete that message,
    the user message that prompted it, and all messages that came after it.
    """
    _db = await db.get()

    # Check if the game exists
    if game_id not in _db["games"]:
        raise HTTPException(
            status_code=404, detail=f"Game with ID '{game_id}' not found"
        )

    game = _db["games"][game_id]

    # Check if the user is the owner
    if current_user["id"] != game["owner_id"]:
        raise HTTPException(
            status_code=403, detail="You are not the owner of this game"
        )

    # Check if there are messages to undo
    messages = game.get("messages", [])
    if len(messages) < 2:
        raise HTTPException(
            status_code=400, detail="Not enough messages to perform undo operation"
        )

    # Find the message with the given ID
    message_index = -1
    target_message = None
    for i, message in enumerate(messages):
        if message["id"] == request.message_id:
            message_index = i
            target_message = message
            break

    if message_index == -1 or target_message is None:
        raise HTTPException(
            status_code=404, detail=f"Message with ID {request.message_id} not found"
        )

    # Check if the message is from the assistant and has a commit_sha
    if target_message["role"] != "assistant" or not target_message.get("commit_sha"):
        raise HTTPException(
            status_code=400,
            detail="Selected message is not an assistant message with a commit",
        )

    # Check if there's a user message before it
    if message_index == 0 or messages[message_index - 1]["role"] != "user":
        raise HTTPException(
            status_code=400,
            detail="No user message found before the selected assistant message",
        )

    # Undo the commit in the game's repo
    try:
        subprocess.run(
            ["git", "reset", "--hard", "HEAD~1"],
            cwd=GAMES_PATH / game_id,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to undo commit: {str(e)}")

    # Remove the assistant message, the user message before it, and all messages after it
    _db["games"][game_id]["messages"] = messages[: message_index - 1]
    await db.set(_db)

    return {"success": True, "messages": _db["games"][game_id]["messages"]}
