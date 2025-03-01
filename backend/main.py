from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
from uuid import uuid4

from db import db, GAMES_PATH, ChatMessage as DbChatMessage
from user import app as user_app

app = FastAPI(root_path="/api")

app.mount("/user", user_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Default Vite dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessageRequest(BaseModel):
    message: str


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/games")
async def get_games():
    _db = await db.get()
    return list(_db["games"].values())


@app.get("/games/{game_name}/play")
async def serve_game(game_name: str):
    """Serve the HTML file for a specific game with added resize handling."""
    game_dir = GAMES_PATH / game_name

    # First check if there's a file named after the game
    game_file = game_dir / f"{game_name}.html"
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


@app.get("/games/{game_name}/chat")
async def get_chat_messages(game_name: str):
    """
    Get all chat messages for a specific game.
    """
    _db = await db.get()
    game_id = None
    
    # Find the game by name
    for id, game in _db["games"].items():
        if game["name"] == game_name:
            game_id = id
            return game.get("messages", [])
    
    if game_id is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")
    
    return []


@app.post("/games/{game_name}/chat")
async def handle_chat(game_name: str, chat_message: ChatMessageRequest):
    """
    Handle chat messages for the game editor.
    Store the message and return a response.
    """
    # Check if the game exists
    _db = await db.get()
    game_id = None
    
    # Find the game by name
    for id, game in _db["games"].items():
        if game["name"] == game_name:
            game_id = id
            break
    
    if game_id is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")
    
    # Create user message
    user_message: DbChatMessage = {
        "id": str(uuid4()),
        "text": chat_message.message,
        "sender": "user",
        "timestamp": datetime.now().isoformat(),
    }
    
    # Create system response
    system_message: DbChatMessage = {
        "id": str(uuid4()),
        "text": f"Echo: {chat_message.message}",
        "sender": "system",
        "timestamp": datetime.now().isoformat(),
    }
    
    # Add messages to the game
    _db["games"][game_id]["messages"].append(user_message)
    _db["games"][game_id]["messages"].append(system_message)
    
    # Update the database
    await db.set(_db)
    
    # Return the system message
    return {"message": system_message["text"]}
