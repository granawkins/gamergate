from datetime import datetime
import subprocess
import json
from uuid import uuid4
from typing import TypedDict

from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel

from assistant import get_completion_background, MODEL
from db import db, GAMES_PATH, Message
from routes.user import AuthenticatedUser, get_current_user

app = FastAPI()


class ParsedChatMessage(TypedDict):
    id: str
    text: str
    role: str
    timestamp: str
    cost: float | None
    status: str
    commit_sha: str | None
    model: str | None
    messages: str | None
    processing_text: list[str] | None


def get_processing_text(messages: str) -> list[str]:
    try:
        output = []
        messages = json.loads(messages)
        assert isinstance(messages, list)
        for message in messages:
            assert isinstance(message, dict)
            contents = message.get("content", [])
            for content in contents:
                text = content.get("text", "")
                if text:
                    output.append(text)
        return output
    except Exception:
        return []


def parse_chat_message(message: Message, admin: bool = False) -> ParsedChatMessage:
    output = ParsedChatMessage(
        id=message.id,
        text=message.text,
        role=message.role,
        timestamp=message.timestamp,
        cost=message.cost,
        status=message.status,
        commit_sha=message.commit_sha,
        model=message.model,
        messages=None,
        processing_text=None,
    )
    if message.messages:
        output["processing_text"] = get_processing_text(message.messages)
    if admin:
        output["messages"] = message.messages
    return output


@app.get("/{game_name}")
async def get_chat_messages(
    game_name: str, current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get all chat messages and game info for a specific game.
    """
    game = await db.get_game_by_name(game_name)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

    if current_user.id != game.owner_id:
        raise HTTPException(
            status_code=403, detail="You are not the owner of this game"
        )

    messages = await db.get_messages_by_game_id(game.id)
    game_data = await db.get_game_data_by_id(game.id)
    return {
        "messages": [
            parse_chat_message(message, current_user.admin) for message in messages
        ],
        "gameInfo": game_data,
    }


@app.post("/{game_name}")
async def handle_chat(
    game_name: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Handle chat messages for the game editor.
    Store the message and return a response with the game info immediately,
    then run the completion in the background with a semaphore.
    """
    # Check if the user has messages left
    if current_user.messages_left <= 0:
        raise HTTPException(
            status_code=403, detail="You have no messages left. Please try again later."
        )

    # Check if the game exists
    game = await db.get_game_by_name(game_name)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")

    if current_user.id != game.owner_id:
        raise HTTPException(
            status_code=403, detail="You are not the owner of this game"
        )

    body = await request.json()
    user_message_text = body["message"]

    user_message: Message = Message(
        id=str(uuid4()),
        game_id=game.id,
        text=user_message_text,
        role="user",
        timestamp=datetime.now().isoformat(),
        cost=0,
        status="completed",
        commit_sha=None,
        model=None,
        messages=None,
    )
    await db.create_message(user_message)

    assistant_message = Message(
        id=str(uuid4()),
        game_id=game.id,
        text="",
        role="assistant",
        timestamp=datetime.now().isoformat(),
        cost=0,
        status="processing",
        commit_sha=None,
        model=MODEL,
        messages=None,
    )
    await db.create_message(assistant_message)

    # Start the completion in the background
    get_completion_background(game.id)

    # Return the empty assistant message and game info immediately
    return {
        "message": parse_chat_message(assistant_message, current_user.admin),
        "gameInfo": game,
    }


@app.get("/{game_name}/message/{message_id}")
async def get_message(
    game_name: str,
    message_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Get a specific message by ID.
    Used for polling the status of an assistant message.
    """
    message = await db.get_message_by_id(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail=f"Message '{message_id}' not found")
    return {"message": parse_chat_message(message, current_user.admin)}


class UndoRequest(BaseModel):
    message_id: str


@app.post("/{game_name}/undo")
async def undo_last_commit(
    game_name: str,
    request: UndoRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Undo the commit associated with a specific message and delete that message,
    the user message that prompted it, and all messages that came after it.
    """
    game = await db.get_game_by_name(game_name)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game '{game_name}' not found")
    if current_user.id != game.owner_id:
        raise HTTPException(
            status_code=403, detail="You are not the owner of this game"
        )

    messages = await db.get_messages_by_game_id(game.id)
    if len(messages) < 2:
        raise HTTPException(
            status_code=400, detail="Not enough messages to perform undo operation"
        )

    # Find the message with the given ID
    message_index = -1
    target_message = None
    for i, message in enumerate(messages):
        if message.id == request.message_id:
            message_index = i
            target_message = message
            break

    if message_index == -1 or target_message is None:
        raise HTTPException(
            status_code=404, detail=f"Message with ID {request.message_id} not found"
        )

    # Check if the message is from the assistant and has a commit_sha
    if target_message.role != "assistant" or not target_message.commit_sha:
        raise HTTPException(
            status_code=400,
            detail="Selected message is not an assistant message with a commit",
        )

    # Undo the commit in the game's repo
    try:
        subprocess.run(
            ["git", "reset", "--hard", "HEAD~1"],
            cwd=GAMES_PATH / game.id,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to undo commit: {str(e)}")

    messages_to_delete = messages[message_index - 1 :]
    for message in messages_to_delete:
        await db.delete_message_by_id(message.id)

    messages = await db.get_messages_by_game_id(game.id)
    return {
        "success": True,
        "messages": [
            parse_chat_message(message, current_user.admin) for message in messages
        ],
    }
