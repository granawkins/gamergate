import sys
import os

# Add the parent directory to the path so we can import modules from the backend package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assistant import apply_edits


def test_apply_edits():
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

    modified_code = apply_edits(code, edits)

    assert "return 1" not in modified_code
    assert "return 2" in modified_code


def test_apply_edits_with_multiple_edits():
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

    modified_code = apply_edits(code, edits)

    assert "return 1" not in modified_code
    assert "return 2" in modified_code
    assert "return 3" not in modified_code
    assert "return 4" in modified_code


def test_apply_edits_with_no_edits():
    """Test applying no edits to code."""
    code = "<!DOCTYPE html><html></html>"
    edits = []

    modified_code = apply_edits(code, edits)

    assert modified_code == code
