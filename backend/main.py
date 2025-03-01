from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from db import db, GAMES_PATH
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


class ChatMessage(BaseModel):
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


@app.post("/games/{game_name}/chat")
async def handle_chat(game_name: str, chat_message: ChatMessage):
    """
    Handle chat messages for the game editor.
    For now, just echo back the message.
    """
    # Check if the game exists
    _db = await db.get()
    game_exists = False
    
    for game in _db["games"].values():
        if game["name"] == game_name:
            game_exists = True
            break
    
    if not game_exists:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")
    
    # For now, just echo back the message
    return {"message": f"Echo: {chat_message.message}"}
