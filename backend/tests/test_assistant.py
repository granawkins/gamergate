import sys
import os
import pytest
from unittest.mock import patch, mock_open

# Add the parent directory to the path so we can import modules from the backend package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assistant import apply_edits, apply_edits_to_game


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


@pytest.mark.asyncio
async def test_apply_edits_to_game_success():
    """Test applying edits to a game file successfully."""
    game_id = "test_game_id"
    edits = [
        (
            "function test() {\n                return 1;\n            }",
            "function test() {\n                return 2;\n            }",
        )
    ]

    # Create a mock for open that returns different file handles for read and write
    mock_open_obj = mock_open(
        read_data="function test() {\n                return 1;\n            }"
    )

    # Mock the database and file operations
    with (
        patch("assistant.db.get") as mock_get,
        patch("assistant.open", mock_open_obj, create=True),
        patch("assistant.GAMES_PATH") as mock_games_path,
    ):
        # Setup the mock database response
        mock_get.return_value = {"games": {game_id: {"path": "test_game"}}}

        # Setup the mock games path
        mock_games_path.__truediv__.return_value.__truediv__.return_value = (
            "test_path/index.html"
        )

        # Call the function
        result = await apply_edits_to_game(game_id, edits)

        # Check the result
        assert result is True

        # Check that the file was opened for writing
        mock_open_obj.assert_any_call("test_path/index.html", "w")

        # Get the file handle that was returned for the write operation
        write_handle = mock_open_obj()

        # Check that write was called with the modified code
        write_handle.write.assert_called_with(
            "function test() {\n                return 2;\n            }"
        )


@pytest.mark.asyncio
async def test_apply_edits_to_game_nonexistent_game():
    """Test applying edits to a nonexistent game."""
    game_id = "nonexistent_game_id"
    edits = [("old", "new")]

    # Mock the database
    with patch("assistant.db.get") as mock_get:
        # Setup the mock database response with no games
        mock_get.return_value = {"games": {}}

        # Call the function
        result = await apply_edits_to_game(game_id, edits)

        # Check the result
        assert result is False


@pytest.mark.asyncio
async def test_apply_edits_to_game_file_not_found():
    """Test applying edits when the game file is not found."""
    game_id = "test_game_id"
    edits = [("old", "new")]

    # Mock the database and file operations
    with (
        patch("assistant.db.get") as mock_get,
        patch("assistant.open", side_effect=FileNotFoundError(), create=True),
        patch("assistant.GAMES_PATH") as mock_games_path,
    ):
        # Setup the mock database response
        mock_get.return_value = {"games": {game_id: {"path": "test_game"}}}

        # Setup the mock games path
        mock_games_path.__truediv__.return_value.__truediv__.return_value = (
            "test_path/index.html"
        )

        # Call the function
        result = await apply_edits_to_game(game_id, edits)

        # Check the result
        assert result is False
