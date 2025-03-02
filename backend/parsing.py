import re
from typing import TypedDict, List, Tuple

from db import MessageStatus


class ParsedResponse(TypedDict):
    text: str
    diff: str
    status: MessageStatus


response_format_prompt = """\
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
"""


def extract_message(response: str) -> str:
    """Extract the message text from the response."""
    message_match = re.search(
        r"<gg_message>\s*(.*?)\s*</gg_message>", response, re.DOTALL
    )
    return message_match.group(1) if message_match else ""


def extract_find_replace_pairs(response: str) -> List[Tuple[str, str]]:
    """Extract find/replace pairs from the response."""
    find_blocks = re.findall(r"<gg_find>\s*(.*?)\s*</gg_find>", response, re.DOTALL)
    replace_blocks = re.findall(
        r"<gg_replace>\s*(.*?)\s*</gg_replace>", response, re.DOTALL
    )

    # Ensure we have matching pairs
    if len(find_blocks) != len(replace_blocks):
        return []

    return list(zip(find_blocks, replace_blocks))


def generate_diff(find_replace_pairs: List[Tuple[str, str]]) -> str:
    """Generate a diff representation of the find/replace pairs."""
    if not find_replace_pairs:
        return ""

    diff = ""
    for i, (find, replace) in enumerate(find_replace_pairs):
        diff += f"--- Find Block {i + 1}\n"
        diff += f"+++ Replace Block {i + 1}\n"
        diff += f"@@ -1,{len(find.splitlines())} +1,{len(replace.splitlines())} @@\n"

        for line in find.splitlines():
            diff += f"- {line}\n"
        for line in replace.splitlines():
            diff += f"+ {line}\n"

        diff += "\n"

    return diff


def parse_response(response: str) -> ParsedResponse:
    """
    Parse the XML response from the AI assistant.

    Extracts the message text and find/replace pairs, and generates a diff representation.

    Args:
        response: The XML response from the AI assistant

    Returns:
        A ParsedResponse object containing the message text, diff, and status
    """
    try:
        # Extract message text
        text = extract_message(response)

        # Extract find/replace pairs
        find_replace_pairs = extract_find_replace_pairs(response)

        # Generate diff representation
        diff = generate_diff(find_replace_pairs)

        # Determine status
        if text or find_replace_pairs:
            status = MessageStatus.COMPLETED
        else:
            status = MessageStatus.ERROR

        return ParsedResponse(text=text, diff=diff, status=status)
    except Exception as e:
        # If any error occurs during parsing, return an error response
        return ParsedResponse(
            text=f"Error parsing response: {str(e)}",
            diff="",
            status=MessageStatus.ERROR,
        )


def apply_changes(code: str, find_replace_pairs: List[Tuple[str, str]]) -> str:
    """
    Apply the find/replace changes to the game code.

    Args:
        code: The original game code
        find_replace_pairs: A list of (find, replace) tuples

    Returns:
        The modified game code
    """
    result = code
    for find, replace in find_replace_pairs:
        result = result.replace(find, replace)
    return result
