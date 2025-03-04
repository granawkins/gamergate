import asyncio
import os
import re
import subprocess
from datetime import datetime
from typing import List, Tuple

from anthropic import AsyncAnthropic, AnthropicError
from anthropic.types import MessageParam

from db import db, GAMES_PATH


client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


MODEL = "claude-3-5-sonnet-20241022"
RETRIES = 3
MOST_RECENT_N_MESSAGES = 5


model_costs = {
    "claude-3-5-sonnet-20240620": {
        "cache_creation_input_tokens": 0.00015,
        "cache_read_input_tokens": 0.00001,
        "input_tokens": 0.00015,
        "output_tokens": 0.0006,
    },
    "claude-3-5-sonnet-20241022": {
        "cache_creation_input_tokens": 0.00015,
        "cache_read_input_tokens": 0.00001,
        "input_tokens": 0.00015,
        "output_tokens": 0.0006,
    },
}


def get_cost(model: str, usage: dict) -> float:
    cost = 0.0
    for key, value in model_costs[model].items():
        if key in usage:
            cost += value * usage.get(key, 0)
    return cost


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

Respond with an xml block with the following format:

<gg_message>
# The text to display to the user.
</gg_message>
<gg_find>
# A snipped of original code (with spacing!) to be replaced. The parser will 
# literally replace this text with the text in <gg_replace>.
</gg_find>
<gg_replace>
# New code to replace the text in <gg_find>.
</gg_replace>

Follow these guidelines absolutely:
- Only respond in the above format. Any text before or after the xml block, or xml tags other than those above, will be ignored.
- You can provide no find/replace paris, one, or multiple.
- Make sure each xml tag is on its own line with no spaces before/after the tag name.
- Make sure the xml block is properly terminated.
- Edits will be applied in the order they are given.
- Once again, you must match the spacing of the original code exactly in your find blocks.

Here is the current code:

{code}
"""


class BadRequestError(Exception):
    pass


class BadResponseError(Exception):
    pass


def extract_message(response: str, allow_incomplete: bool = False) -> str:
    """Extract the message text from the response"""
    message_match = re.search(
        r"<gg_message>\s*(.*?)\s*</gg_message>", response, re.DOTALL
    )

    if message_match:
        if len(message_match.groups()) > 1:
            raise BadResponseError("Multiple message tags found")
        return message_match.group(1)

    if not allow_incomplete:
        raise BadResponseError("No closing message tag found")

    message_start = re.search(r"<gg_message>(.*)", response, re.DOTALL)
    if message_start:
        # Return everything after the opening tag, stripping whitespace
        return message_start.group(1).strip()

    return ""


def extract_edits(
    response: str, allow_incomplete: bool = False
) -> List[Tuple[str, str]]:
    """Extract find/replace pairs from the response"""
    find_blocks = re.findall(r"<gg_find>\s*(.*?)\s*</gg_find>", response, re.DOTALL)
    replace_blocks = re.findall(
        r"<gg_replace>\s*(.*?)\s*</gg_replace>", response, re.DOTALL
    )

    if not allow_incomplete:
        if len(find_blocks) != len(replace_blocks):
            raise BadResponseError("Unequal number of find and replace tags")
        if response.count("<gg_find>") != response.count("</gg_find>"):
            raise BadResponseError("Unequal number of find tags")
        if response.count("<gg_replace>") != response.count("</gg_replace>"):
            raise BadResponseError("Unequal number of replace tags")

    pairs = []
    for i in range(min(len(find_blocks), len(replace_blocks))):
        pairs.append((find_blocks[i], replace_blocks[i]))

    return pairs


def apply_edit(code: str, find: str, replace: str) -> str:
    """Apply a single edit to the code"""
    if code.count(find) == 0:
        raise BadResponseError("Find text not found in code")
    elif code.count(find) > 1:
        raise BadResponseError("Find text found multiple times in code")
    return code.replace(find, replace)


async def generate_completion(game_id: str):
    """
    Generate a completion for the last assistant message in the game.
    Uses streaming API to incrementally update the response.
    Parses response into text and edits.
    Applies edits to the codebase.
    Updates the message with the completion text, diff, commit sha, cost, and status.
    """

    _db = await db.get()
    game = _db["games"].get(game_id)
    if game is None:
        raise BadRequestError(f"Game {game_id} not found")

    # Build system prompt
    file_path = GAMES_PATH / game["id"] / "index.html"
    if not file_path.exists():
        raise BadRequestError("Game code not found")
    with open(file_path, "r") as f:
        code = f.read()
    system_prompt = SYSTEM_PROMPT.format(code=code)

    # Build messages
    messages = game["messages"]
    last_message = messages[-1]
    if last_message["role"] != "assistant":
        raise BadRequestError("Last message must be an assistant message")
    if last_message["text"]:
        raise BadRequestError("Last message must be empty")
    messages = [
        MessageParam(role=message["role"], content=message["text"])
        for message in messages[
            -(MOST_RECENT_N_MESSAGES + 1) : -1
        ]  # Last message is placeholder for assistant response
    ]

    for try_num in range(RETRIES):
        full_response = ""
        try:
            # Stream response directly into db
            stream = await client.messages.create(
                max_tokens=8192,
                messages=messages,
                model=MODEL,
                stream=True,
                system=system_prompt,
            )
            async for event in stream:  # type: ignore
                # Update cost
                chunk_dict = (
                    event.model_dump() if hasattr(event, "model_dump") else dict(event)
                )
                usage = None
                if "message" in chunk_dict and "usage" in chunk_dict["message"]:
                    usage = chunk_dict["message"]["usage"]
                elif "usage" in chunk_dict:
                    usage = chunk_dict["usage"]
                elif "delta" in chunk_dict and "usage" in chunk_dict["delta"]:
                    usage = chunk_dict["delta"]["usage"]
                if usage is not None:
                    last_message["cost"] += get_cost(MODEL, usage)

                # Get text
                if (
                    event.type == "content_block_delta"
                    and event.delta.type == "text_delta"
                ):
                    full_response += event.delta.text
                    last_message["text"] = full_response
                    _db["games"][game_id]["messages"][-1] = last_message
                    await db.set(_db)

            # Check that message and edits are valid
            extract_message(full_response)
            edits = extract_edits(full_response)

            # Apply edits
            if len(edits) > 0:
                modified_code = code
                for find, replace in edits:
                    modified_code = apply_edit(modified_code, find, replace)
                with open(file_path, "w") as f:
                    f.write(modified_code)

                # Apply to codebase
                subprocess.run(
                    ["git", "add", "index.html"], cwd=GAMES_PATH / game["id"]
                )
                # First make the commit
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"message {last_message['id']}",
                    ],
                    cwd=GAMES_PATH / game["id"],
                )
                # Then get the commit hash
                commit_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=GAMES_PATH / game["id"],
                    capture_output=True,
                )
                last_message["commit_sha"] = commit_result.stdout.strip().decode(
                    "utf-8"
                )

                # Update the updated_at field
                _db["games"][game_id]["updated_at"] = datetime.now().isoformat()

            # Success!
            last_message["status"] = "completed"
            break
        except AnthropicError as e:
            last_message["text"] += f"Error generating response: {str(e)}"
            last_message["status"] = "error"
            break
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            if try_num < RETRIES - 1:
                print("Retrying...")
                last_message["text"] = ""  # Try again
            else:
                last_message["text"] += f"Error generating response: {str(e)}"
                last_message["status"] = "error"

    _db["games"][game_id]["messages"][-1] = last_message
    await db.set(_db)


# Run up to 10 completions concurrently
completion_semaphore = asyncio.Semaphore(10)


async def run_completion_with_semaphore(game_id: str):
    async with completion_semaphore:
        await generate_completion(game_id)


def get_completion_background(game_id: str):
    asyncio.create_task(run_completion_with_semaphore(game_id))
