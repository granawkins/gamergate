from typing import TypedDict

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


def parse_response(response: str) -> ParsedResponse:
    return ParsedResponse(text="", diff="", status=MessageStatus.PROCESSING)
