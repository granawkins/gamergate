from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime
from uuid import uuid4
import socketio
import asyncio
import time

from db import db, GAMES_PATH, ChatMessage, User
from user import app as user_app, get_current_user

# Create a Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["http://localhost:5173"]  # Default Vite dev server port
)

# Create FastAPI app
app = FastAPI(root_path="/api")

# Create an ASGI app from the Socket.IO server
socket_app = socketio.ASGIApp(sio)

# Mount the Socket.IO app to the FastAPI app
app.mount("/ws", socket_app)

app.mount("/user", user_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Default Vite dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event
async def send_message(sid, data):
    """
    Handle incoming messages from the client via Socket.IO.
    Store the user message and stream back an assistant response.
    """
    try:
        game_name = data.get('game_name')
        message_text = data.get('message')
        user_id = data.get('user_id')
        
        if not all([game_name, message_text, user_id]):
            await sio.emit('error', {'message': 'Missing required fields'}, room=sid)
            return
            
        # Check if the game exists
        _db = await db.get()
        game_id = None
        game = None

        # Find the game by name
        for id, g in _db["games"].items():
            if g["name"] == game_name:
                if user_id != g["owner_id"]:
                    await sio.emit('error', {'message': 'You are not the owner of this game'}, room=sid)
                    return
                game_id = id
                game = g
                break

        if game_id is None:
            await sio.emit('error', {'message': f"Game '{game_name}' not found"}, room=sid)
            return

        # Create user message
        user_message_id = str(uuid4())
        user_message: ChatMessage = {
            "id": user_message_id,
            "text": message_text,
            "sender": "user",
            "timestamp": datetime.now().isoformat(),
        }
        _db["games"][game_id]["messages"].append(user_message)

        # Create assistant message with empty text initially
        assistant_message_id = str(uuid4())
        assistant_message: ChatMessage = {
            "id": assistant_message_id,
            "text": "",  # Start with empty text, will be filled character by character
            "sender": "assistant",
            "timestamp": datetime.now().isoformat(),
        }
        _db["games"][game_id]["messages"].append(assistant_message)
        
        # Save the initial state to the database
        await db.set(_db)
        
        # Emit the user and initial assistant messages
        await sio.emit('message_received', {
            'user_message': user_message,
            'assistant_message': assistant_message,
            'game_info': game
        }, room=sid)
        
        # Prepare the full response text
        full_response = f"Echo: {message_text}"
        
        # Start a background task to stream the response
        # Pass the sid to ensure the response is sent only to this client
        asyncio.create_task(
            stream_response(game_id, assistant_message_id, full_response, game, sid=sid)
        )
        
    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        await sio.emit('error', {'message': f"An error occurred: {str(e)}"}, room=sid)


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
            return {"messages": game.get("messages", []), "gameInfo": game}

    raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")


@app.post("/chat/{game_name}")
async def handle_chat(
    game_name: str,
    chat_message: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Handle chat messages for the game editor via HTTP POST.
    This endpoint is kept for backward compatibility.
    For new implementations, use the Socket.IO 'send_message' event.
    
    Store the message and return a response with the game info.
    Stream the assistant message character by character using Socket.IO.
    """
    # Check if the game exists
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

    if game_id is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

    # Create user message
    user_message: ChatMessage = {
        "id": str(uuid4()),
        "text": chat_message.message,
        "sender": "user",
        "timestamp": datetime.now().isoformat(),
    }
    _db["games"][game_id]["messages"].append(user_message)

    # Create assistant message with empty text initially
    message_id = str(uuid4())
    assistant_message: ChatMessage = {
        "id": message_id,
        "text": "",  # Start with empty text, will be filled character by character
        "sender": "assistant",
        "timestamp": datetime.now().isoformat(),
    }
    _db["games"][game_id]["messages"].append(assistant_message)
    
    # Save the initial state to the database
    await db.set(_db)
    
    # Prepare the full response text
    full_response = f"Echo: {chat_message.message}"
    
    # Start a background task to stream the response
    asyncio.create_task(
        stream_response(game_id, message_id, full_response, game)
    )
    
    # Return immediately with the initial empty message and game info
    return {"message": assistant_message, "gameInfo": game}

async def stream_response(game_id: str, message_id: str, full_response: str, game, sid=None):
    """
    Stream the assistant response character by character.
    Updates the database and sends updates via Socket.IO.
    
    Args:
        game_id: The ID of the game
        message_id: The ID of the message to update
        full_response: The complete response text to stream
        game: The game object
        sid: Optional Socket.IO session ID for directed messages
    """
    current_text = ""
    
    # Stream at approximately 20 characters per second
    delay = 0.05  # 50ms delay between characters
    
    for char in full_response:
        current_text += char
        
        # Update the message in the database
        _db = await db.get()
        for msg in _db["games"][game_id]["messages"]:
            if msg["id"] == message_id:
                msg["text"] = current_text
                break
        
        await db.set(_db)
        
        # Prepare the update data
        update_data = {
            "message_id": message_id,
            "text": current_text,
            "game_name": game["name"]
        }
        
        # Emit the updated message via Socket.IO
        if sid:
            # If sid is provided, send only to that client
            await sio.emit("message_update", update_data, room=sid)
        else:
            # Otherwise broadcast to all clients
            await sio.emit("message_update", update_data)
        
        # Wait before sending the next character
        await asyncio.sleep(delay)
