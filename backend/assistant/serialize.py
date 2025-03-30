from anthropic.types import Message, ContentBlock, Usage


def serialize_input(input: object) -> dict:
    if isinstance(input, dict):
        return input

    fields = [
        "command",
        "path",
        "view_range",
        "old_str",
        "new_str",
        "file_text",
        "insert_line",
    ]
    return {field: getattr(input, field) for field in fields}


def serialize_usage(usage: Usage) -> dict:
    if isinstance(usage, dict):
        return usage

    fields = [
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    ]
    return {field: getattr(usage, field) for field in fields}


def serialize_chunk(chunk: ContentBlock) -> dict:
    if isinstance(chunk, dict):
        return chunk

    fields = ["type", "text", "tool_use_id", "name", "input", "is_error"]
    output = {}
    for field in fields:
        if hasattr(chunk, field):
            value = getattr(chunk, field)
            if field == "input":
                value = serialize_input(value)
            output[field] = value
    return output


def serialize_message(message: Message | dict) -> dict:
    if isinstance(message, dict):
        return message

    fields = ["id", "role", "content", "usage"]
    output = {}
    for field in fields:
        if hasattr(message, field):
            value = getattr(message, field)
            if field == "content":
                value = [serialize_chunk(chunk) for chunk in value]
            elif field == "usage":
                value = serialize_usage(value)
            output[field] = value
    return output
