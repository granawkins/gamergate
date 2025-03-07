import os
import zipfile
import tempfile

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from datetime import datetime
import subprocess
import shutil
from uuid import uuid4

from db import db, GAMES_PATH, Message, User
from routes.user import app as user_app, get_current_user
from routes.admin import app as admin_app
from routes.stripe import app as stripe_app
from assistant import get_completion_background, extract_message

app = FastAPI()

app.mount("/user", user_app)
app.mount("/admin", admin_app)
app.mount("/stripe", stripe_app)

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
async def get_games(search: str = "", sort: str = "newest"):
    """
    Get all games, separated into Play and Templates sections.

    Parameters:
    - search: Filter games by name (case-insensitive)
    - sort: Sort games by "newest", "oldest", or "most_played"

    Returns:
    - play: games where owner_id is not empty
    - templates: games where owner_id is empty
    """
    _db = await db.get()
    games = [{**game, "seconds_played": 0} for game in _db["games"].values()]
    for play_session in _db["play_sessions"]:
        for game in games:
            if game["id"] == play_session["game_id"]:
                game["seconds_played"] += play_session["seconds"]

    # Filter by search query if provided
    if search:
        search = search.lower()
        games = [
            game
            for game in games
            if search in game["name"].lower()
            or (game.get("description") and search in game["description"].lower())
        ]

    # Separate games into Play and Templates sections
    play_games = [game for game in games if game["owner_id"] != ""]
    template_games = [game for game in games if game["owner_id"] == ""]

    # Sort the play games based on the sort parameter
    if sort == "newest":
        play_games.sort(key=lambda x: x["created_at"], reverse=True)
    elif sort == "oldest":
        play_games.sort(key=lambda x: x["created_at"])
    elif sort == "most_played":
        # For now, we'll sort by updated_at as a proxy for popularity
        play_games.sort(key=lambda x: x["seconds_played"], reverse=True)

    return {"play": play_games, "templates": template_games}


@app.post("/games/update-info")
async def update_game_info(request: Request):
    """Update the game info (name and/or description)."""
    data = await request.json()
    name = data.get("name")
    description = data.get("description")
    current_game_id = data.get("current_game_id")
    field_to_update = data.get(
        "field", "name"
    )  # Default to name for backward compatibility

    if field_to_update == "name" and not name:
        raise HTTPException(status_code=400, detail="Name is required")

    _db = await db.get()

    # If updating name, check if it's already taken by another game
    if field_to_update == "name":
        for id, game in _db["games"].items():
            if game["name"] == name and id != current_game_id:
                return {"successful": False}

    # If current_game_id is provided, update the game's info
    if current_game_id and current_game_id in _db["games"]:
        if field_to_update == "name" and name:
            _db["games"][current_game_id]["name"] = name
        elif field_to_update == "description" and description is not None:
            _db["games"][current_game_id]["description"] = description

        _db["games"][current_game_id]["updated_at"] = datetime.now().isoformat()
        await db.set(_db)
        return {"successful": True}

    # For backward compatibility
    return {"available": True}


@app.get("/games/{game_name}/info")
async def get_game_info(game_name: str):
    """Get game information including the owner username."""
    _db = await db.get()
    game_id = None
    game = None

    # Find the game by name
    for id, g in _db["games"].items():
        if g["name"] == game_name:
            game_id = id
            game = g
            break

    if game_id is None or game is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

    # Get the owner's username
    owner_username = None
    if game["owner_id"]:
        for user_id, user in _db["users"].items():
            if user_id == game["owner_id"]:
                owner_username = user.get("username", "Anonymous")
                break

    # Create a copy of the game info with the owner username
    game_info = {
        "id": game["id"],
        "name": game["name"],
        "description": game.get("description", ""),
        "owner_id": game["owner_id"],
        "owner_username": owner_username,
        "created_at": game["created_at"],
        "updated_at": game["updated_at"],
    }

    # Add parent name if applicable
    parent_id = game.get("parent_id")
    if parent_id and parent_id in _db["games"]:
        game_info["parent_name"] = _db["games"][parent_id]["name"]

    # Add seconds played if applicable
    seconds_played = 0
    for play_session in _db["play_sessions"]:
        if play_session["game_id"] == game_id:
            seconds_played += play_session["seconds"]
    game_info["seconds_played"] = seconds_played

    return game_info


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
        "description": source_game.get(
            "description", ""
        ),  # Copy description from source game
        "owner_id": current_user["id"],
        "parent_id": source_game_id,
        "created_at": now,
        "updated_at": now,
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
            game["seconds_played"] = 0
            for play_session in _db["play_sessions"]:
                if play_session["game_id"] == game["id"]:
                    game["seconds_played"] += play_session["seconds"]
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
    # Check if the user has messages left
    _db = await db.get()
    if current_user["messages_left"] <= 0:
        raise HTTPException(
            status_code=403, detail="You have no messages left. Please try again later."
        )

    # Check if the game exists
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

    # Process the remaining messages to extract human-readable text from assistant messages
    remaining_messages = _db["games"][game_id]["messages"]
    for message in remaining_messages:
        if message.get("role") == "assistant" and message.get("status") != "error":
            message["text"] = extract_message(message["text"], allow_incomplete=True)

    return {"success": True, "messages": remaining_messages}


@app.get("/games/{game_name}/download")
async def download_game(
    game_name: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Download a game's directory as a zip file.
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

    # Create a zip file of the game directory
    game_dir = GAMES_PATH / game_id

    # Create a temporary file for the zip
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
        temp_path = tmp_file.name

    # Create the zip file
    with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(game_dir):
            # Skip the .git directory
            if ".git" in dirs:
                dirs.remove(".git")

            for file in files:
                file_path = os.path.join(root, file)
                # Add file to zip with a path relative to the game directory
                arcname = os.path.relpath(file_path, game_dir)
                zipf.write(file_path, arcname)

    # Add task to delete temporary file after response is sent
    background_tasks.add_task(os.unlink, temp_path)

    # Return the zip file as a download
    return FileResponse(
        path=temp_path, filename=f"{game_name}.zip", media_type="application/zip"
    )


@app.post("/record-play-session")
async def record_play_session(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Record a play session for a game.
    """
    data = await request.json()
    game_name = data.get("game_name")
    seconds = data.get("seconds")
    _db = await db.get()

    # Check if the game exists
    game = next((g for g in _db["games"].values() if g["name"] == game_name), None)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

    # Check if the user exists
    if current_user["id"] not in _db["users"]:
        raise HTTPException(status_code=404, detail="User not found")

    # Record the play session
    _db["play_sessions"].append(
        {
            "id": str(uuid4()),
            "user_id": current_user["id"],
            "game_id": game["id"],
            "created_at": datetime.now().isoformat(),
            "seconds": seconds,
        }
    )
    await db.set(_db)
    return {"success": True}


@app.get("/{full_path:path}")
async def serve_index(request: Request, full_path: str):
    public_file_path = os.path.join("../frontend/dist", full_path)
    if os.path.exists(public_file_path) and os.path.isfile(public_file_path):
        return FileResponse(public_file_path)
    with open("../frontend/dist/index.html") as file:
        return HTMLResponse(content=file.read())
