from pathlib import Path
from typing import Optional

import aiosqlite
from aiosqlite import Connection, Cursor

from db.models import User, Message, Game, Transaction, PlaySession  # noqa: F401


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: Optional[Connection] = None
        self._cursor: Optional[Cursor] = None

    async def connect(self):
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._cursor = await self._connection.cursor()

    async def close(self):
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            self._cursor = None

    async def execute(self, query: str, params: tuple = ()):
        assert self._connection is not None and self._cursor is not None
        await self._cursor.execute(query, params)
        await self._connection.commit()

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Fetch a user by ID"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, created_at, messages_left, username, email, avatar_id FROM users WHERE id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return User.from_row(row) if row else None

    async def create_user(self, user: User) -> None:
        """Create a new user"""
        assert self._connection is not None and self._cursor is not None
        await self._connection.execute(
            """
            INSERT INTO users (id, created_at, messages_left, username, email, avatar_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user.id,
                user.created_at,
                user.messages_left,
                user.username,
                user.email,
                user.avatar_id,
            ),
        )
        await self._connection.commit()

    async def get_game_by_id(self, game_id: str) -> Optional[Game]:
        """Fetch a game by ID"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, name, description, owner_id, parent_id, created_at, updated_at, cover_image, version FROM games WHERE id = ?",
            (game_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return Game.from_row(row) if row else None
