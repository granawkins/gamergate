# https://docs.anthropic.com/en/docs/build-with-claude/tool-use/text-editor-tool
import asyncio
import os
import json
from typing import List, Callable, Coroutine, Any, Optional, Tuple

from dotenv import load_dotenv

import anthropic
from anthropic.types import (
    MessageParam,
    ToolTextEditor20250124Param,
    Message,
    Usage,
)

from db import db
from assistant.editor import Editor
from assistant.errors import BadRequestError
from assistant.serialize import serialize_message


load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.AsyncAnthropic(api_key=api_key)

MOST_RECENT_N_MESSAGES = 5
MODEL = "claude-3-7-sonnet-20250219"
MAX_TOKENS = 4096
TOOLS = [
    ToolTextEditor20250124Param(
        type="text_editor_20250124",
        name="str_replace_editor",
    )
]
SYSTEM_PROMPT = """
You are a helpful assistant helping the user develop a one-page browser game in index.html (already created).
Your paths will be routed to the correct cwd, so just use relative paths like `/`, `/index.html`, etc - not `/repo`.
"""


def get_cost(usage: Usage) -> float:
    # https://docs.anthropic.com/en/docs/about-claude/models/all-models#model-comparison-table
    model_costs = {
        "cache_creation_input_tokens": 0.000375,
        "cache_read_input_tokens": 0.00003,
        "input_tokens": 0.0003,
        "output_tokens": 0.0015,
    }
    cost = 0.0
    for key, value in model_costs.items():
        if hasattr(usage, key):
            cost += value * getattr(usage, key)
    return cost


async def generate_completion(
    messages: List[MessageParam],
    editor: Editor,
    max_iterations: int = 10,
    streaming_callback: Optional[
        Callable[[Message | dict], Coroutine[Any, Any, None]]
    ] = None,
) -> Tuple[str, float]:
    """Run the tool use loop until complete and stream the final response"""
    total_cost = 0.0
    response_text = ""

    # Pre-add first assistant/tool-call message to view file
    initial_input = {"command": "view", "path": "/index.html"}
    messages.append(
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "I'll help you with that. First lets take a look at the current code.",
                },
                {
                    "type": "tool_use",
                    "id": "1234567890",
                    "input": initial_input,
                    "name": "str_replace_editor",
                },
            ],
        }
    )  # type: ignore
    if streaming_callback:
        await streaming_callback(dict(messages[-1]))

    file_content = editor.handle_editor_tool(initial_input)
    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "1234567890",
                    "content": file_content,
                }
            ],
        }
    )
    if streaming_callback:
        await streaming_callback(dict(messages[-1]))

    for _ in range(max_iterations):
        response = await client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=TOOLS,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        messages.append(
            {
                "role": "assistant",
                "content": response.content,
            }
        )
        if streaming_callback:
            await streaming_callback(response)
        tool_result_content = []
        for chunk in response.content:
            if chunk.type == "text":
                response_text = chunk.text
            elif chunk.type == "tool_use":
                try:
                    content = editor.handle_editor_tool(chunk.input)  # type: ignore
                    tool_result_content.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": chunk.id,
                            "content": content,
                        }
                    )
                except Exception as e:
                    tool_result_content.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": chunk.id,
                            "content": f"Error: {e}",
                            "is_error": True,
                        }
                    )
        if len(tool_result_content) > 0:
            messages.append(
                {
                    "role": "user",
                    "content": tool_result_content,
                }
            )
            if streaming_callback:
                await streaming_callback(dict(messages[-1]))
        else:
            break
    return response_text, total_cost


async def generate_assistant_message(game_id: str):
    # Confirm db model and codebase exist
    game = await db.get_game_by_id(game_id)
    if game is None:
        raise BadRequestError(f"Game {game_id} not found")
    editor = Editor(game_id)
    if not editor.cwd.exists():
        raise BadRequestError("Game code not found")

    # Build messages
    messages = await db.get_messages_by_game_id(game_id)
    last_message = messages[-1]
    if last_message.role != "assistant":
        raise BadRequestError("Last message must be an assistant message")
    if last_message.text:
        raise BadRequestError("Last message must be empty")
    last_message_id = last_message.id

    # Format messages for the LLM
    messages_for_llm = [
        MessageParam(role=message.role, content=message.text)
        for message in messages[
            -(MOST_RECENT_N_MESSAGES + 1) : -1
        ]  # Last message is placeholder for assistant response
    ]

    total_cost: float = 0.0
    sub_messages: List[dict[str, Any]] = []

    async def streaming_callback(message: Message | dict):
        """Call after each LLM response (not technically streaming)

        If result includes a tool call, the 'text' is used as a processing message.
        """
        nonlocal sub_messages
        serialized_message = serialize_message(message)
        sub_messages.append(serialized_message)
        json_sub_messages = json.dumps(sub_messages)
        updates: dict[str, Any] = {"messages": json_sub_messages}
        if isinstance(message, Message):
            nonlocal total_cost
            total_cost += get_cost(message.usage)
            updates["cost"] = total_cost
            if not any(chunk.type == "tool_use" for chunk in message.content):
                text = next(
                    (chunk.text for chunk in message.content if chunk.type == "text"),
                    "",
                )
                if text:
                    updates["text"] = text
        await db.update_message_by_id(last_message_id, **updates)

    try:
        await generate_completion(
            messages=messages_for_llm,
            editor=editor,
            streaming_callback=streaming_callback,
        )
        commit_sha = await editor.commit_changes(last_message_id)
        await db.update_message_by_id(
            last_message_id, status="completed", cost=total_cost, commit_sha=commit_sha
        )
        user = await db.get_user_by_id(game.owner_id)
        if user:
            await db.update_user_by_id(user.id, credits=int(user.credits - total_cost))
    except Exception as e:
        await db.update_message_by_id(
            last_message_id, text=str(e), status="error", cost=total_cost
        )


# Run up to 10 completions concurrently
completion_semaphore = asyncio.Semaphore(10)


async def run_completion_with_semaphore(game_id: str):
    async with completion_semaphore:
        await generate_assistant_message(game_id)


def get_completion_background(game_id: str):
    asyncio.create_task(run_completion_with_semaphore(game_id))


if __name__ == "__main__":
    messages = [MessageParam(role="user", content="Make the car blue")]
    editor = Editor("driver")

    async def streaming_callback(message: Message | dict):
        if isinstance(message, Message):
            text = next(
                (chunk.text for chunk in message.content if chunk.type == "text"), ""
            )
            print(text)

    asyncio.run(
        generate_completion(
            messages=messages, editor=editor, streaming_callback=streaming_callback
        )
    )
