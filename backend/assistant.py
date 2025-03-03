import asyncio
import os
import subprocess
from typing import List, Tuple

from anthropic import Anthropic
from anthropic.types import Usage

from db import db, GAMES_PATH
from parsing import response_format_prompt, parse_response


client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


SYSTEM_PROMPT = """\
You are Gamergate, an AI-powered assistant that helps users create and edit html/javascript games.

You are shown a complete game and a conversation log, and you respond with some text and (optionally) one or more edits to the code.

Follow these general guidelines:
- If the user asks a question, respond with a concise, helpful answer.
- If the user tells you to do something, respond with a summary of what you'll do and your edits.
- Unless the user says otherwise, assume they are not interested in the technical details of your implementation. They may not even know how to code.
- Stick to making games. If the user asks unrelated questions or seems to be building something that's not a game, politely decline and try to guide them back toward making a game.
- The user is looking at / playing a live demo of the game during your discussion. If they say 'it' or 'this' or 'that', this is probably what they're referring to.

When you write code:
- Keep everything in a single html file, and make everything client-side.
- You're in charge of the entire codebase. Don't hesitate to refactor or make major changes if you feel they're appropriate. Leave comments where useful.

{response_format_prompt}

Here is the current code:

{code}

"""


MODEL = "claude-3-5-sonnet-20240620"


model_costs = {
    "claude-3-5-sonnet-20240620": {
        "cache_creation_input_tokens": 0.00015,
        "cache_read_input_tokens": 0.00001,
        "input_tokens": 0.00015,
        "output_tokens": 0.0006,
    },
}


def get_cost(model: str, usage: Usage) -> float:
    return sum(
        model_costs[model][key] * getattr(usage, key, 0) for key in model_costs[model]
    )


def apply_edits(code: str, edits: List[Tuple[str, str]]) -> str:
    """
    Apply a list of edits (find/replace pairs) to the code.

    Args:
        code: The original code
        edits: A list of (find, replace) tuples

    Returns:
        The modified code
    """
    result = code
    for find, replace in edits:
        result = result.replace(find, replace)
    return result


async def generate_completion(game_id: str):
    """
    Generate a completion for the last assistant message in the game.
    Uses streaming API to incrementally update the response.
    Parses response into text and edits.
    Applies edits to the codebase.
    Updates the message with the completion text, diff, commit sha, cost, and status.
    """

    # Build messages
    _db = await db.get()
    game = _db["games"].get(game_id)
    if game is None:
        raise ValueError(f"Game {game_id} not found")
    messages = game["messages"]

    last_message = messages[-1]
    if last_message["role"] != "assistant":
        raise ValueError("Last message must be an assistant message")
    if last_message["text"]:
        raise ValueError("Last message must be empty")

    # Initialize the message with empty text and processing status
    last_message["text"] = ""
    last_message["status"] = "processing"
    _db["games"][game_id]["messages"][-1] = last_message
    await db.set(_db)

    edits = []
    try:
        # Read the code
        with open(GAMES_PATH / game["path"] / "index.html", "r") as f:
            code = f.read()
        system_prompt = SYSTEM_PROMPT.format(
            response_format_prompt=response_format_prompt, code=code
        )

        # Generate streaming completion
        stream = client.messages.create(
            max_tokens=1000,
            model=MODEL,
            system=system_prompt,
            messages=[
                {"role": message["role"], "content": message["text"]}
                for message in messages[-11:-1]
            ],
            stream=True,
        )

        # Process the streaming response
        full_response = ""

        # Process the stream in a synchronous manner
        for event in stream:
            # Try to extract text content from the event safely
            text_content = ""
            try:
                # Use a generic approach to extract text from the event
                # Convert the event to a string representation
                event_str = str(event)

                # Check if this is a content delta event with text
                if "delta" in event_str and "text" in event_str:
                    # Use getattr with a default value to safely access attributes
                    delta = getattr(event, "delta", None)
                    if delta is not None:
                        # Use getattr again to safely access the text attribute
                        text = getattr(delta, "text", "")
                        if text:
                            text_content = text
            except Exception:
                # If we encounter any error accessing attributes, just continue
                pass

            # If we found text content, update the response
            if text_content:
                # Append the new text to the full response
                full_response += text_content

                # Update the message in the database with the partial response
                _db = await db.get()
                game = _db["games"].get(game_id)
                if game is None:
                    raise ValueError(f"Game {game_id} not found")
                last_message = game["messages"][-1]
                last_message["text"] = full_response
                _db["games"][game_id]["messages"][-1] = last_message
                await db.set(_db)

                # Add a 1-second delay to avoid excessive database access
                await asyncio.sleep(1)

        # Parse the complete response to extract message text and edits
        parsed = parse_response(full_response)

        # Get final database state
        _db = await db.get()
        game = _db["games"].get(game_id)
        if game is None:
            raise ValueError(f"Game {game_id} not found")
        last_message = game["messages"][-1]

        # Update with parsed content
        last_message["text"] = parsed["text"]
        edits = parsed["edits"]

        # Set a fixed cost for now since we can't access usage directly
        last_message["cost"] = 0.0  # Placeholder
        last_message["status"] = "completed"

    except Exception as e:
        # Get current database state in case it changed during streaming
        _db = await db.get()
        game = _db["games"].get(game_id)
        if game is None:
            raise ValueError(f"Game {game_id} not found")
        last_message = game["messages"][-1]

        last_message["text"] = f"Error generating response: {str(e)}"
        last_message["edits"] = []
        last_message["status"] = "error"

    # Apply edits, extract diff and commit
    if len(edits) > 0:
        try:
            file_path = GAMES_PATH / game["path"] / "index.html"
            with open(file_path, "r") as f:
                code = f.read()
            modified_code = apply_edits(code, edits)
            with open(file_path, "w") as f:
                f.write(modified_code)

            diff = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=GAMES_PATH / game["path"],
                capture_output=True,
                text=True,
            )
            last_message["diff"] = diff.stdout

            subprocess.run(["git", "add", "."], cwd=GAMES_PATH / game["path"])
            commit_result = subprocess.run(
                ["git", "commit", "-m", f"message {last_message['id']}", "--format=%H"],
                cwd=GAMES_PATH / game["path"],
                capture_output=True,
                text=True,
            )
            last_message["commit_sha"] = commit_result.stdout.strip()
        except Exception as e:
            last_message["text"] += f"\nError applying edits: {str(e)}"

    # Update the message in the database
    _db["games"][game_id]["messages"][-1] = last_message
    await db.set(_db)


# Run up to 10 completions concurrently
completion_semaphore = asyncio.Semaphore(10)


async def run_completion_with_semaphore(game_id: str):
    async with completion_semaphore:
        await generate_completion(game_id)


def get_completion_background(game_id: str):
    asyncio.create_task(run_completion_with_semaphore(game_id))
