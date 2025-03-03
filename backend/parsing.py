import re
from typing import TypedDict, List, Tuple


class ParsedResponse(TypedDict):
    text: str
    edits: List[Tuple[str, str]]


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
    """
    Extract the message text from the response.

    If there's no closing tag, assume everything is the message.
    """
    message_match = re.search(
        r"<gg_message>\s*(.*?)\s*</gg_message>", response, re.DOTALL
    )

    if message_match:
        return message_match.group(1)

    # If no closing tag, check if there's an opening tag
    message_start = re.search(r"<gg_message>(.*)", response, re.DOTALL)
    if message_start:
        # Return everything after the opening tag, stripping whitespace
        return message_start.group(1).strip()

    return ""


def extract_find_replace_pairs(response: str) -> List[Tuple[str, str]]:
    """
    Extract find/replace pairs from the response.

    Only include complete pairs.
    """
    find_blocks = re.findall(r"<gg_find>\s*(.*?)\s*</gg_find>", response, re.DOTALL)
    replace_blocks = re.findall(
        r"<gg_replace>\s*(.*?)\s*</gg_replace>", response, re.DOTALL
    )

    # Only include complete pairs
    pairs = []
    for i in range(min(len(find_blocks), len(replace_blocks))):
        pairs.append((find_blocks[i], replace_blocks[i]))

    return pairs


def parse_response(response: str) -> ParsedResponse:
    """
    Parse the XML response from the AI assistant.

    Extracts the message text and find/replace pairs.

    Args:
        response: The XML response from the AI assistant

    Returns:
        A ParsedResponse object containing the message text and edits
    """
    try:
        # Extract message text
        text = extract_message(response)

        # Extract find/replace pairs
        edits = extract_find_replace_pairs(response)

        return ParsedResponse(text=text, edits=edits)
    except Exception as e:
        # If any error occurs during parsing, return an error response
        return ParsedResponse(
            text=f"Error parsing response: {str(e)}",
            edits=[],
        )
