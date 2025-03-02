import asyncio
import os

from anthropic import Anthropic
from anthropic.types import Usage

from db import db, GAMES_PATH
from parsing import response_format_prompt


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


async def generate_completion(game_id: str):
    """
    Generate a completion for the last assistant message in the game.
    Updates the message with the completion text, cost, and status.
    """
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

    with open(GAMES_PATH / game["path"] / "index.html", "r") as f:
        code = f.read()
    system_prompt = SYSTEM_PROMPT.format(
        response_format_prompt=response_format_prompt, code=code
    )

    try:
        response = client.messages.create(
            max_tokens=1000,
            model=MODEL,
            system=system_prompt,
            messages=[
                {"role": message["role"], "content": message["text"]}
                for message in messages[-11:-1]
            ],
        )

        text_block = next((b for b in response.content if hasattr(b, "text")), None)
        last_message["text"] = text_block.text if text_block else "Missing text block"  # type: ignore
        last_message["cost"] = get_cost(MODEL, response.usage)
        last_message["status"] = "completed"  # Update status to completed
    except Exception as e:
        # Handle any errors during completion generation
        last_message["text"] = f"Error generating response: {str(e)}"
        last_message["status"] = "error"  # Update status to error

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
