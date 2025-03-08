"""
Tests for the SQLAlchemy database implementation.
"""

import os
import sys
import asyncio
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add the parent directory to the path so we can import modules from the backend package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db_sqlalchemy import (
    db_sqlalchemy,
    User,
    Game,
    Message,
)


class TestDBSQLAlchemy(unittest.TestCase):
    """Test the SQLAlchemy database implementation."""

    def setUp(self):
        """Set up a temporary database for testing."""
        # Create a temporary file for the database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_db_path = Path(self.temp_dir.name) / "test.db"

        # Override the database path
        db_sqlalchemy.engine = None
        db_sqlalchemy.async_session = None
        db_sqlalchemy._initialized = False

        # We'll use a separate event loop for async tests
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up after the test."""
        # Close the database connection
        self.loop.run_until_complete(db_sqlalchemy.close())

        # Remove the temporary directory
        self.temp_dir.cleanup()

        # Close the event loop
        self.loop.close()

    def test_initialization(self):
        """Test that the database can be initialized."""

        async def test_init():
            await db_sqlalchemy.initialize()
            self.assertTrue(db_sqlalchemy._initialized)

        self.loop.run_until_complete(test_init())

    def test_create_and_get_user(self):
        """Test creating and retrieving a user."""

        async def test_user():
            await db_sqlalchemy.initialize()

            # Create a test user
            user_id = str(uuid4())
            user = User(
                id=user_id,
                created_at=datetime.now().isoformat(),
                messages_left=10,
                username="testuser",
                email="test@example.com",
                avatar_id="avatar1",
            )

            # Add the user to the database
            await db_sqlalchemy.create_user(user)

            # Retrieve the user
            retrieved_user = await db_sqlalchemy.get_user(user_id)

            # Check that the user was retrieved correctly
            self.assertIsNotNone(retrieved_user)
            self.assertEqual(retrieved_user.id, user_id)
            self.assertEqual(retrieved_user.username, "testuser")
            self.assertEqual(retrieved_user.email, "test@example.com")
            self.assertEqual(retrieved_user.messages_left, 10)

        self.loop.run_until_complete(test_user())

    def test_create_and_get_game_with_messages(self):
        """Test creating and retrieving a game with messages."""

        async def test_game():
            await db_sqlalchemy.initialize()

            # Create a test user
            user_id = str(uuid4())
            user = User(
                id=user_id,
                created_at=datetime.now().isoformat(),
                messages_left=10,
                username="testuser",
                email="test@example.com",
            )
            await db_sqlalchemy.create_user(user)

            # Create a test game
            game_id = str(uuid4())
            now = datetime.now().isoformat()

            # Create messages for the game
            message1 = Message(
                id=str(uuid4()),
                game_id=game_id,
                text="Hello, world!",
                role="user",
                timestamp=now,
            )

            message2 = Message(
                id=str(uuid4()),
                game_id=game_id,
                text="Hello, user!",
                role="assistant",
                timestamp=datetime.now().isoformat(),
                status="completed",
            )

            game = Game(
                id=game_id,
                name="Test Game",
                owner_id=user_id,
                created_at=now,
                updated_at=now,
                description="A test game",
                messages=[message1, message2],
            )

            # Add the game to the database
            await db_sqlalchemy.create_game(game)

            # Retrieve the game
            retrieved_game = await db_sqlalchemy.get_game(game_id)

            # Check that the game was retrieved correctly
            self.assertIsNotNone(retrieved_game)
            self.assertEqual(retrieved_game.id, game_id)
            self.assertEqual(retrieved_game.name, "Test Game")
            self.assertEqual(retrieved_game.owner_id, user_id)
            self.assertEqual(len(retrieved_game.messages), 2)

            # Check that the messages were retrieved correctly
            self.assertEqual(retrieved_game.messages[0].text, "Hello, world!")
            self.assertEqual(retrieved_game.messages[0].role, "user")
            self.assertEqual(retrieved_game.messages[1].text, "Hello, user!")
            self.assertEqual(retrieved_game.messages[1].role, "assistant")
            self.assertEqual(retrieved_game.messages[1].status, "completed")

        self.loop.run_until_complete(test_game())

    def test_legacy_get_set(self):
        """Test the legacy get() and set() methods."""

        async def test_legacy():
            await db_sqlalchemy.initialize()

            # Create test data
            user_id = str(uuid4())
            game_id = str(uuid4())
            now = datetime.now().isoformat()

            # Build a data structure matching the old format
            data = {
                "users": {
                    user_id: {
                        "id": user_id,
                        "created_at": now,
                        "messages_left": 10,
                        "username": "testuser",
                        "email": "test@example.com",
                        "avatar_id": None,
                    }
                },
                "games": {
                    game_id: {
                        "id": game_id,
                        "name": "Test Game",
                        "owner_id": user_id,
                        "created_at": now,
                        "updated_at": now,
                        "description": "A test game",
                        "parent_id": None,
                        "cover_image": None,
                        "version": 1,
                        "messages": [
                            {
                                "id": str(uuid4()),
                                "text": "Hello, world!",
                                "role": "user",
                                "timestamp": now,
                            }
                        ],
                    }
                },
                "transactions": {},
                "play_sessions": [],
            }

            # Set the data
            await db_sqlalchemy.set(data)

            # Get the data
            retrieved_data = await db_sqlalchemy.get()

            # Check that the data was retrieved correctly
            self.assertIn(user_id, retrieved_data["users"])
            self.assertIn(game_id, retrieved_data["games"])
            self.assertEqual(retrieved_data["users"][user_id].username, "testuser")
            self.assertEqual(retrieved_data["games"][game_id].name, "Test Game")
            self.assertEqual(len(retrieved_data["games"][game_id].messages), 1)
            self.assertEqual(
                retrieved_data["games"][game_id].messages[0].text, "Hello, world!"
            )

        self.loop.run_until_complete(test_legacy())


if __name__ == "__main__":
    unittest.main()
