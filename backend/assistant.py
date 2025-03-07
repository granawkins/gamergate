import asyncio
import os
import re
import subprocess
from datetime import datetime
from typing import (
    List,
    Tuple,
    Callable,
    Optional,
    Dict,
)

from anthropic import AsyncAnthropic, AnthropicError
from anthropic.types import MessageParam

from db import db, GAMES_PATH

# Global flag for OpenAI availability
HAS_OPENAI = False
try:
    import openai

    HAS_OPENAI = True
except ImportError:
    pass

# Initialize Anthropic client
anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Initialize OpenAI client if available
openai_client = None
if HAS_OPENAI:
    try:
        from openai import AsyncOpenAI

        openai_client = AsyncOpenAI()
    except (ImportError, AttributeError):
        pass

DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
RETRIES = 3
MOST_RECENT_N_MESSAGES = 5

model_costs = {
    # Anthropic models
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
    # OpenAI models
    "gpt-4o": {
        "input_tokens": 0.00005,
        "output_tokens": 0.00015,
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


async def anthropic_completion(
    messages: List[Dict[str, str]],
    model: str,
    system_prompt: str,
    streaming_callback: Callable[[str, Optional[Dict[str, int]]], None],
) -> float:
    """
    Generate a completion using Anthropic's API.
    Returns the total cost in cents.
    """
    total_cost = 0.0

    # Convert messages to Anthropic's MessageParam format
    anthropic_messages = []
    for msg in messages:
        # Convert the role to a valid Anthropic role
        msg_role = str(msg["role"])
        role = "assistant" if msg_role == "assistant" else "user"

        anthropic_messages.append(MessageParam(role=role, content=str(msg["content"])))

    stream = await anthropic_client.messages.create(
        max_tokens=8192,
        messages=anthropic_messages,
        model=model,
        stream=True,
        system=system_prompt,
    )

    full_response = ""
    async for event in stream:
        # Update cost
        chunk_dict = event.model_dump() if hasattr(event, "model_dump") else dict(event)
        usage = None
        if "message" in chunk_dict and "usage" in chunk_dict["message"]:
            usage = chunk_dict["message"]["usage"]
        elif "usage" in chunk_dict:
            usage = chunk_dict["usage"]
        elif "delta" in chunk_dict and "usage" in chunk_dict["delta"]:
            usage = chunk_dict["delta"]["usage"]

        if usage is not None:
            total_cost += get_cost(model, usage)

        # Get text
        if event.type == "content_block_delta" and event.delta.type == "text_delta":
            full_response += event.delta.text
            streaming_callback(full_response, usage)

    return total_cost


async def openai_completion(
    messages: List[Dict[str, str]],
    model: str,
    system_prompt: str,
    streaming_callback: Callable[[str, Optional[Dict[str, int]]], None],
) -> float:
    """
    Generate a completion using OpenAI's API.
    Returns the total cost in cents.
    """
    if not HAS_OPENAI or openai_client is None:
        raise ImportError("OpenAI package is not installed or client not initialized")

    total_cost = 0.0

    # Convert messages to OpenAI format and add system message
    openai_messages = [{"role": "system", "content": system_prompt}]

    for msg in messages:
        # Ensure role is valid for OpenAI
        role = str(msg["role"])
        if role not in ["user", "assistant", "system"]:
            role = "user"  # Default to user for safety
        openai_messages.append({"role": role, "content": str(msg["content"])})

    # Use the OpenAI client dynamically to avoid type checking issues
    if hasattr(openai_client, "chat") and hasattr(openai_client.chat, "completions"):
        completion_create = getattr(openai_client.chat.completions, "create")
        stream = await completion_create(
            model=model,
            messages=openai_messages,
            stream=True,
        )

        full_response = ""
        async for chunk in stream:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                if hasattr(chunk.choices[0], "delta") and hasattr(
                    chunk.choices[0].delta, "content"
                ):
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response += content
                        streaming_callback(
                            full_response, None
                        )  # OpenAI doesn't provide per-chunk token counts
    else:
        raise ImportError("OpenAI client does not have expected attributes")

    # Calculate the cost after completion
    # We need to estimate token counts
    input_tokens = sum(
        len(str(m["content"])) // 4 for m in openai_messages
    )  # Rough estimate
    output_tokens = len(full_response) // 4  # Rough estimate

    usage = {"input_tokens": input_tokens, "output_tokens": output_tokens}

    total_cost = get_cost(model, usage)
    return total_cost


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

    # Check if model parameter exists, otherwise use default
    model = last_message.get("model", DEFAULT_MODEL)

    # Format messages for the LLM
    messages_for_llm = [
        {"role": message["role"], "content": message["text"]}
        for message in messages[
            -(MOST_RECENT_N_MESSAGES + 1) : -1
        ]  # Last message is placeholder for assistant response
    ]

    for try_num in range(RETRIES):
        full_response = ""
        try:
            # Define streaming callback
            def streaming_callback(
                response_text: str, usage: Optional[Dict[str, int]]
            ) -> None:
                nonlocal full_response
                full_response = response_text
                last_message["text"] = full_response
                if usage is not None:
                    last_message["cost"] += get_cost(model, usage)
                _db["games"][game_id]["messages"][-1] = last_message
                # Create a task to set the DB asynchronously without awaiting
                asyncio.create_task(db.set(_db))

            # Choose the appropriate completion function based on the model
            if model.startswith("claude"):
                last_message["cost"] += await anthropic_completion(
                    messages_for_llm, model, system_prompt, streaming_callback
                )
            elif model.startswith("gpt"):
                if not HAS_OPENAI:
                    raise ImportError(
                        "OpenAI package is not installed but required for GPT models"
                    )
                last_message["cost"] += await openai_completion(
                    messages_for_llm, model, system_prompt, streaming_callback
                )
            else:
                raise ValueError(f"Unsupported model: {model}")

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

            # Decrement messages_left for the user
            _db = await db.get()
            user_id = _db["games"][game_id]["owner_id"]
            if user_id in _db["users"]:
                if _db["users"][user_id]["messages_left"] > 0:
                    _db["users"][user_id]["messages_left"] -= 1
                    await db.set(_db)
            break
        except AnthropicError as e:
            last_message["text"] += f"Error generating response: {str(e)}"
            last_message["status"] = "error"
            break
        except Exception as e:
            # Check if it's an OpenAI error
            if HAS_OPENAI and "openai" in str(type(e)).lower():
                last_message["text"] += f"Error generating response: {str(e)}"
                last_message["status"] = "error"
                break

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
