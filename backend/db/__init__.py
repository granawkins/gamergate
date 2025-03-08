from pathlib import Path
from typing import Optional

import aiosqlite
from aiosqlite import Connection, Cursor

from db.models import User, Message, Game, Transaction, PlaySession  # noqa: F401
from db.migrations import migrate  # noqa: F401


DB_PATH = Path(__file__).parent / "db.sqlite"


class Database:
    def __init__(self, db_path: Path = DB_PATH):
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

    async def get_user(self, user_id: str) -> Optional[User]:
        """Fetch a user by ID"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, created_at, messages_left, username, email, avatar_id FROM users WHERE id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return User.from_row(row) if row else None

    async def upsert_user(self, user: User) -> None:
        """Insert or update a user"""
        assert self._connection is not None and self._cursor is not None
        await self._connection.execute(
            """
            INSERT INTO users (id, created_at, messages_left, username, email, avatar_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                messages_left = ?,
                username = ?,
                email = ?,
                avatar_id = ?
            """,
            (
                user.id,
                user.created_at,
                user.messages_left,
                user.username,
                user.email,
                user.avatar_id,
                # Values for UPDATE
                user.messages_left,
                user.username,
                user.email,
                user.avatar_id,
            ),
        )
        await self._connection.commit()
