"""
SQLite-based database module for Gamergate.

This module provides SQLite database functionality using SQLAlchemy and Pydantic
while maintaining the same interface as the old JSON-based database module for compatibility.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from db_sqlalchemy import (
    db_sqlalchemy,
    GAMES_PATH,
    ADMIN_EMAIL,
    User,
    Game,
    Message,
    Transaction,
    PlaySession,
)

# Constants
GAME_VERSION = 1
DB_PATH = Path(__file__).parent / "gamergate.db"

# Re-export types for backward compatibility
__all__ = [
    "DB",
    "db",
    "User",
    "Game",
    "Message",
    "Transaction",
    "PlaySession",
    "GAME_VERSION",
    "GAMES_PATH",
    "ADMIN_EMAIL",
]


class DB:
    """
    SQLite database interface that maintains compatibility with the old JSON-based interface.

    This class delegates all operations to the SQLAlchemy implementation while keeping
    the same API (`get()`, `set()`) to minimize changes to the rest of the codebase.
    """

    def __init__(self):
        """Initialize the database connection."""
        self.lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the database connection and ensure tables exist."""
        await db_sqlalchemy.initialize()

    async def get(self) -> Dict[str, Any]:
        """
        Get the entire database as a dict, compatible with the old JSON-based format.

        Returns:
            A dictionary with keys for "users", "games", "transactions", and "play_sessions".
        """
        return await db_sqlalchemy.get()

    async def set(self, data: Dict[str, Any]) -> None:
        """
        Update the database with the provided data.

        Args:
            data: A dictionary with keys for "users", "games", "transactions", and "play_sessions".
        """
        await db_sqlalchemy.set(data)

    # Additional helper methods that can be used for more efficient operations

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return await db_sqlalchemy.get_user(user_id)

    async def get_game(self, game_id: str) -> Optional[Game]:
        """Get a game by ID."""
        return await db_sqlalchemy.get_game(game_id)

    async def get_game_by_name(self, game_name: str) -> Optional[Game]:
        """Get a game by name."""
        return await db_sqlalchemy.get_game_by_name(game_name)

    async def add_message(self, game_id: str, message: Message) -> None:
        """Add a message to a game."""
        await db_sqlalchemy.add_message(game_id, message)

    async def update_message(self, message_id: str, updates: Dict[str, Any]) -> None:
        """Update a message's properties."""
        await db_sqlalchemy.update_message(message_id, updates)

    async def add_play_session(self, session: PlaySession) -> None:
        """Add a new play session."""
        await db_sqlalchemy.add_play_session(session)


# Initialize the database singleton
db = DB()
