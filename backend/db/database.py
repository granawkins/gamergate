from pathlib import Path
from typing import Optional, List

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

    # INTERFACE

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

    async def get_all_users(self) -> List[User]:
        """Fetch all users"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, created_at, messages_left, username, email, avatar_id FROM users"
        ) as cursor:
            rows = await cursor.fetchall()
            return [User.from_row(row) for row in rows]

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by email"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, created_at, messages_left, username, email, avatar_id FROM users WHERE email = ?",
            (email,),
        ) as cursor:
            row = await cursor.fetchone()
            return User.from_row(row) if row else None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Fetch a user by ID"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, created_at, messages_left, username, email, avatar_id FROM users WHERE id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return User.from_row(row) if row else None

    async def update_user_by_id(self, id: str, **kwargs) -> None:
        """Update a user"""
        assert self._connection is not None and self._cursor is not None
        assert all(key in User.__annotations__ for key in kwargs)
        await self._connection.execute(
            """
            UPDATE users SET {} WHERE id = ?
            """.format(", ".join([f"{key} = ?" for key in kwargs])),
            tuple(kwargs.values()) + (id,),
        )
        await self._connection.commit()

    async def get_all_games(self) -> List[Game]:
        """Fetch all games"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, name, description, owner_id, parent_id, created_at, updated_at, cover_image, version FROM games"
        ) as cursor:
            rows = await cursor.fetchall()
            return [Game.from_row(row) for row in rows]

    async def get_game_by_id(self, game_id: str) -> Optional[Game]:
        """Fetch a game by ID"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, name, description, owner_id, parent_id, created_at, updated_at, cover_image, version FROM games WHERE id = ?",
            (game_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return Game.from_row(row) if row else None

    async def update_game_by_id(self, id: str, **kwargs) -> None:
        """Update a game"""
        assert self._connection is not None and self._cursor is not None
        assert all(key in Game.__annotations__ for key in kwargs)
        await self._connection.execute(
            """
            UPDATE games SET {} WHERE id = ?
            """.format(", ".join([f"{key} = ?" for key in kwargs])),
            tuple(kwargs.values()) + (id,),
        )
        await self._connection.commit()

    async def get_games_by_owner_id(self, owner_id: str) -> List[Game]:
        """Fetch all games by owner ID"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, name, description, owner_id, parent_id, created_at, updated_at, cover_image, version FROM games WHERE owner_id = ?",
            (owner_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [Game.from_row(row) for row in rows]

    async def get_all_messages(self) -> List[Message]:
        """Fetch all messages"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, game_id, text, role, timestamp, cost, status, commit_sha, model FROM messages"
        ) as cursor:
            rows = await cursor.fetchall()
            return [Message.from_row(row) for row in rows]

    async def get_messages_by_game_id(self, game_id: str) -> List[Message]:
        """Fetch all messages for a game"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, game_id, text, role, timestamp, cost, status, commit_sha, model FROM messages WHERE game_id = ?",
            (game_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [Message.from_row(row) for row in rows]

    async def create_message(self, message: Message) -> None:
        """Create a new message"""
        assert self._connection is not None and self._cursor is not None
        await self._connection.execute(
            """
            INSERT INTO messages (id, game_id, text, role, timestamp, cost, status, commit_sha, model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.id,
                message.game_id,
                message.text,
                message.role,
                message.timestamp,
                message.cost,
                message.status,
                message.commit_sha,
                message.model,
            ),
        )
        await self._connection.commit()

    async def update_message_by_id(self, id: str, **kwargs) -> None:
        """Update a message"""
        assert self._connection is not None and self._cursor is not None
        assert all(key in Message.__annotations__ for key in kwargs)
        await self._connection.execute(
            """
            UPDATE messages SET {} WHERE id = ?
            """.format(", ".join([f"{key} = ?" for key in kwargs])),
            tuple(kwargs.values()) + (id,),
        )
        await self._connection.commit()

    async def create_transaction(self, transaction: Transaction) -> None:
        """Create a new transaction"""
        assert self._connection is not None and self._cursor is not None
        await self._connection.execute(
            """
            INSERT INTO transactions (id, user_id, amount, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                transaction.id,
                transaction.user_id,
                transaction.session_id,
                transaction.amount,
                transaction.created_at,
                transaction.updated_at,
                transaction.status,
                transaction.description,
            ),
        )
        await self._connection.commit()

    async def get_all_transactions(self) -> List[Transaction]:
        """Fetch all transactions"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, user_id, amount, created_at, updated_at FROM transactions"
        ) as cursor:
            rows = await cursor.fetchall()
            return [Transaction.from_row(row) for row in rows]
