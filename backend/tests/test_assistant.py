import sys
import os
import re

# Add the parent directory to the path so we can import modules from the backend package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assistant import apply_edit, extract_message, extract_edits


def test_apply_edit():
    """Test applying edits to code."""
    code = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
    </head>
    <body>
        <script>
            function test() {
                return 1;
            }
        </script>
    </body>
    </html>
    """

    edits = [
        (
            "function test() {\n                return 1;\n            }",
            "function test() {\n                return 2;\n            }",
        )
    ]

    modified_code = code
    for find, replace in edits:
        modified_code = apply_edit(modified_code, find, replace)

    assert "return 1" not in modified_code
    assert "return 2" in modified_code


def test_apply_edit_with_multiple_edits():
    """Test applying multiple edits to code."""
    code = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
    </head>
    <body>
        <script>
            function test1() {
                return 1;
            }
            
            function test2() {
                return 3;
            }
        </script>
    </body>
    </html>
    """

    edits = [
        (
            "function test1() {\n                return 1;\n            }",
            "function test1() {\n                return 2;\n            }",
        ),
        (
            "function test2() {\n                return 3;\n            }",
            "function test2() {\n                return 4;\n            }",
        ),
    ]

    modified_code = code
    for find, replace in edits:
        modified_code = apply_edit(modified_code, find, replace)

    assert "return 1" not in modified_code
    assert "return 2" in modified_code
    assert "return 3" not in modified_code
    assert "return 4" in modified_code


def test_apply_edit_with_no_edits():
    """Test applying no edits to code."""
    code = "<!DOCTYPE html><html></html>"
    edits = []

    modified_code = code
    for find, replace in edits:
        modified_code = apply_edit(modified_code, find, replace)

    assert modified_code == code


def test_extract_message_with_valid_message():
    """Test extracting a message from a valid response."""
    response = """
    <gg_message>
    This is a test message.
    </gg_message>
    """

    message = extract_message(response)

    assert message == "This is a test message."


def test_extract_message_with_multiline_message():
    """Test extracting a multiline message."""
    response = """
    <gg_message>
    This is a test message
    with multiple lines.
    
    It has paragraphs too.
    </gg_message>
    """

    message = extract_message(response)

    # Use a more flexible comparison that ignores exact whitespace
    assert re.sub(r"\s+", " ", message.strip()) == re.sub(
        r"\s+",
        " ",
        "This is a test message with multiple lines. It has paragraphs too.".strip(),
    )


def test_extract_message_with_no_message():
    """Test extracting a message when there is no message tag."""
    response = """
    <gg_find>
    function test() {
        return 1;
    }
    </gg_find>
    <gg_replace>
    function test() {
        return 2;
    }
    </gg_replace>
    """

    message = extract_message(response, allow_incomplete=True)

    assert message == ""


def test_extract_message_with_no_closing_tag():
    """Test extracting a message when there's no closing tag (streaming case)."""
    response = """
    <gg_message>
    This is a streaming message that hasn't finished yet.
    """

    message = extract_message(response, allow_incomplete=True)

    assert message == "This is a streaming message that hasn't finished yet."


def test_extract_edits_with_one_pair():
    """Test extracting one find/replace pair."""
    response = """
    <gg_message>
    This is a test message.
    </gg_message>
    <gg_find>
    function test() {
        return 1;
    }
    </gg_find>
    <gg_replace>
    function test() {
        return 2;
    }
    </gg_replace>
    """

    pairs = extract_edits(response)

    assert len(pairs) == 1
    assert pairs[0][0] == "function test() {\n        return 1;\n    }"
    assert pairs[0][1] == "function test() {\n        return 2;\n    }"


def test_extract_edits_with_multiple_pairs():
    """Test extracting multiple find/replace pairs."""
    response = """
    <gg_message>
    This is a test message.
    </gg_message>
    <gg_find>
    function test1() {
        return 1;
    }
    </gg_find>
    <gg_replace>
    function test1() {
        return 2;
    }
    </gg_replace>
    <gg_find>
    function test2() {
        return 3;
    }
    </gg_find>
    <gg_replace>
    function test2() {
        return 4;
    }
    </gg_replace>
    """

    pairs = extract_edits(response)

    assert len(pairs) == 2
    assert pairs[0][0] == "function test1() {\n        return 1;\n    }"
    assert pairs[0][1] == "function test1() {\n        return 2;\n    }"
    assert pairs[1][0] == "function test2() {\n        return 3;\n    }"
    assert pairs[1][1] == "function test2() {\n        return 4;\n    }"


def test_extract_edits_with_no_pairs():
    """Test extracting find/replace pairs when there are none."""
    response = """
    <gg_message>
    This is a test message.
    </gg_message>
    """

    pairs = extract_edits(response)

    assert len(pairs) == 0


def test_extract_edits_with_mismatched_pairs():
    """Test extracting find/replace pairs when there are mismatched pairs."""
    response = """
    <gg_message>
    This is a test message.
    </gg_message>
    <gg_find>
    function test1() {
        return 1;
    }
    </gg_find>
    <gg_replace>
    function test1() {
        return 2;
    }
    </gg_replace>
    <gg_find>
    function test2() {
        return 3;
    }
    </gg_find>
    """

    pairs = extract_edits(response, allow_incomplete=True)

    # Should only include complete pairs
    assert len(pairs) == 1
    assert pairs[0][0] == "function test1() {\n        return 1;\n    }"
    assert pairs[0][1] == "function test1() {\n        return 2;\n    }"


def test_extract_edits_with_incomplete_streaming():
    """Test extracting find/replace pairs in a streaming response."""
    response = """
    <gg_message>
    This is a test message.
    </gg_message>
    <gg_find>
    function test1() {
        return 1;
    }
    </gg_find>
    <gg_replace>
    function test1() {
        return 2;
    }
    </gg_replace>
    <gg_find>
    function test2() {
        return 3;
    }
    """

    pairs = extract_edits(response, allow_incomplete=True)

    # Should only include complete pairs
    assert len(pairs) == 1
    assert pairs[0][0] == "function test1() {\n        return 1;\n    }"
    assert pairs[0][1] == "function test1() {\n        return 2;\n    }"
