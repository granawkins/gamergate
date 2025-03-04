from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime
import subprocess
import shutil
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


@app.post("/games/update-name")
async def update_game_name(request: Request):
    """Update the name, if it's not a duplicate of another game."""
    data = await request.json()
    name = data.get("name")
    current_game_id = data.get("current_game_id")

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    _db = await db.get()

    # Check if the name is already taken by another game
    for id, game in _db["games"].items():
        if game["name"] == name and id != current_game_id:
            return {"successful": False}

    # If current_game_id is provided, update the game's name
    if current_game_id and current_game_id in _db["games"]:
        _db["games"][current_game_id]["name"] = name
        _db["games"][current_game_id]["updated_at"] = datetime.now().isoformat()
        await db.set(_db)
        return {"successful": True}

    # For backward compatibility
    return {"available": True}


@app.get("/games/{game_name}/play")
async def serve_game(game_name: str):
    """Serve the HTML file for a specific game with added resize handling."""
    # Find the game ID from the name in the database
    _db = await db.get()
    game_id = None

    for id, game in _db["games"].items():
        if game["name"] == game_name:
            game_id = id
            break

    if game_id is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

    # Use the game ID to locate the game directory
    game_dir = GAMES_PATH / game_id

    # First check if there's a file named index.html (most common)
    game_file = game_dir / "index.html"
    if not game_file.exists():
        # If not, look for any HTML file in the directory
        html_files = list(game_dir.glob("*.html"))
        if html_files:
            game_file = html_files[0]
        else:
            # If no HTML file is found, return 404
            raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

    # Read the HTML content
    with open(game_file, "r") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)


@app.delete("/games/{game_name}")
async def delete_game(game_name: str, current_user: User = Depends(get_current_user)):
    """
    Delete a game by name. Only the owner can delete their game.
    """
    _db = await db.get()
    game_id = None

    # Find the game by name
    for id, game in _db["games"].items():
        if game["name"] == game_name:
            if current_user["id"] != game["owner_id"]:
                raise HTTPException(
                    status_code=403, detail="You are not the owner of this game"
                )
            game_id = id
            break

    if game_id is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

    # Delete the game from the database
    del _db["games"][game_id]
    await db.set(_db)

    return JSONResponse(
        status_code=200, content={"message": f"Game '{game_name}' deleted successfully"}
    )


class CloneGameRequest(BaseModel):
    new_name: str


@app.post("/games/{game_name}/clone")
async def clone_game(
    game_name: str,
    request: CloneGameRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Clone a game with a new name.
    1. Check if the name is available
    2. Create a new database entry with parent_id set to the cloned project
    3. Copy the game directory to a new one with the new ID
    4. Return the new game information
    """
    new_name = request.new_name

    if not new_name or not new_name.strip():
        raise HTTPException(status_code=400, detail="New game name cannot be empty")

    # Check if the name is available
    _db = await db.get()
    for game in _db["games"].values():
        if game["name"] == new_name:
            raise HTTPException(
                status_code=400, detail=f"Game name '{new_name}' is already taken"
            )

    # Find the source game
    source_game_id = None
    source_game = None
    for id, game in _db["games"].items():
        if game["name"] == game_name:
            source_game_id = id
            source_game = game
            break

    if source_game_id is None or source_game is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

    # Create a new game entry
    new_game_id = str(uuid4())
    now = datetime.now().isoformat()

    new_game = {
        "id": new_game_id,
        "name": new_name,
        "owner_id": current_user["id"],
        "parent_id": source_game_id,
        "created_at": now,
        "updated_at": now,
        "plays": 0,
        "messages": [],
    }

    # Copy the game directory
    source_dir = GAMES_PATH / source_game_id
    target_dir = GAMES_PATH / new_game_id

    try:
        shutil.copytree(source_dir, target_dir)

        # Initialize git repo for the new game
        subprocess.run(["git", "init"], cwd=target_dir)
        subprocess.run(["git", "add", "."], cwd=target_dir)
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "Initial commit (cloned from {})".format(game_name),
            ],
            cwd=target_dir,
        )

        # Add the new game to the database
        _db["games"][new_game_id] = new_game
        await db.set(_db)

        return {"success": True, "game": new_game, "redirect": f"/editor/{new_name}"}

    except Exception as e:
        # Clean up if something went wrong
        if target_dir.exists():
            shutil.rmtree(target_dir)
        raise HTTPException(status_code=500, detail=f"Failed to clone game: {str(e)}")


@app.get("/chat/{game_name}")
async def get_chat_messages(
    game_name: str, current_user: User = Depends(get_current_user)
):
    """
    Get all chat messages and game info for a specific game.
    """
    _db = await db.get()
    for game in _db["games"].values():
        if game["name"] == game_name:
            if current_user["id"] != game["owner_id"]:
                raise HTTPException(
                    status_code=403, detail="You are not the owner of this game"
                )
            messages = game.pop("messages")
            for message in messages:
                if (
                    message.get("role") == "assistant"
                    and message.get("status") != "error"
                ):
                    message["text"] = extract_message(
                        message["text"], allow_incomplete=True
                    )
            parent_id = game.pop("parent_id")
            game["parent_name"] = (
                None if parent_id is None else _db["games"][parent_id].get("name", None)
            )
            return {"messages": messages, "gameInfo": game}

    raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")


@app.post("/chat/{game_name}")
async def handle_chat(
    game_name: str,
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
    game_id = None
    game = None
    body = await request.json()
    user_message_text = body["message"]

    # Find the game by name
    for id, g in _db["games"].items():
        if g["name"] == game_name:
            if current_user["id"] != g["owner_id"]:
                raise HTTPException(
                    status_code=403, detail="You are not the owner of this game"
                )
            game_id = id
            game = g
            break

    if game_id is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

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


@app.get("/chat/{game_name}/message/{message_id}")
async def get_message(
    game_name: str, message_id: str, current_user: User = Depends(get_current_user)
):
    """
    Get a specific message by ID.
    Used for polling the status of an assistant message.
    """
    _db = await db.get()

    # Find the game by name
    for game in _db["games"].values():
        if game["name"] == game_name:
            if current_user["id"] != game["owner_id"]:
                raise HTTPException(
                    status_code=403, detail="You are not the owner of this game"
                )

            # Find the message by ID
            for message in game.get("messages", []):
                if message["id"] == message_id:
                    if (
                        message.get("role") == "assistant"
                        and message.get("status") != "error"
                    ):
                        message["text"] = extract_message(
                            message["text"], allow_incomplete=True
                        )
                    return {"message": message}

            raise HTTPException(
                status_code=404, detail=f"Message '{message_id}' not found"
            )

    raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")


class UndoRequest(BaseModel):
    message_id: str


@app.post("/chat/{game_name}/undo")
async def undo_last_commit(
    game_name: str, request: UndoRequest, current_user: User = Depends(get_current_user)
):
    """
    Undo the commit associated with a specific message and delete that message,
    the user message that prompted it, and all messages that came after it.
    """
    _db = await db.get()
    game_id = None
    game = None

    # Find the game by name
    for id, g in _db["games"].items():
        if g["name"] == game_name:
            if current_user["id"] != g["owner_id"]:
                raise HTTPException(
                    status_code=403, detail="You are not the owner of this game"
                )
            game_id = id
            game = g
            break

    if game_id is None or game is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

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
            cwd=GAMES_PATH / game["id"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to undo commit: {str(e)}")

    # Remove the assistant message, the user message before it, and all messages after it
    _db["games"][game_id]["messages"] = messages[: message_index - 1]

    # Update the updated_at field
    _db["games"][game_id]["updated_at"] = datetime.now().isoformat()

    await db.set(_db)

    return {"success": True, "messages": _db["games"][game_id]["messages"]}
