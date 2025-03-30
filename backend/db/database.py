from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

import aiosqlite
from aiosqlite import Connection, Cursor, Row

from db.models import User, Message, Game, Transaction, PlaySession  # noqa: F401


@dataclass
class GameWithData(Game):
    seconds_played: int
    owner_username: str
    parent_name: str

    @classmethod
    def from_row(cls, row: Row) -> "GameWithData":
        return cls(
            id=row[0],
            name=row[1],
            description=row[2],
            owner_id=row[3],
            parent_id=row[4],
            created_at=row[5],
            updated_at=row[6],
            cover_image=row[7],
            version=row[8],
            seconds_played=row[9],
            owner_username=row[10],
            parent_name=row[11],
        )


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
            INSERT INTO users (id, created_at, credits, username, email, avatar_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user.id,
                user.created_at,
                user.credits,
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
            "SELECT id, created_at, credits, username, email, avatar_id FROM users"
        ) as cursor:
            rows = await cursor.fetchall()
            return [User.from_row(row) for row in rows]

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by email"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, created_at, credits, username, email, avatar_id FROM users WHERE email = ?",
            (email,),
        ) as cursor:
            row = await cursor.fetchone()
            return User.from_row(row) if row else None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Fetch a user by ID"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, created_at, credits, username, email, avatar_id FROM users WHERE id = ?",
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

    async def create_game(self, game: Game) -> None:
        """Create a new game"""
        assert self._connection is not None and self._cursor is not None
        await self._connection.execute(
            """
            INSERT INTO games (id, name, description, owner_id, parent_id, created_at, updated_at, cover_image, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game.id,
                game.name,
                game.description,
                game.owner_id,
                game.parent_id,
                game.created_at,
                game.updated_at,
                game.cover_image,
                game.version,
            ),
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

    async def get_all_game_data(self) -> List[GameWithData]:
        """Return all games with seconds_played and owner_username"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            """
            SELECT g.*, COALESCE(SUM(ps.seconds), 0) as seconds_played, COALESCE(u.username, '') as owner_username, COALESCE(p.name, '') as parent_name
            FROM games g
            LEFT JOIN play_sessions ps ON g.id = ps.game_id
            LEFT JOIN users u ON g.owner_id = u.id
            LEFT JOIN games p ON g.parent_id = p.id
            GROUP BY g.id
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [GameWithData.from_row(row) for row in rows]

    async def get_game_data_by_id(self, game_id: str) -> Optional[GameWithData]:
        """Return game with seconds_played, owner_username, and parent_name"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            """
            SELECT g.*, COALESCE(SUM(ps.seconds), 0) as seconds_played, COALESCE(u.username, '') as owner_username, COALESCE(p.name, '') as parent_name
            FROM games g
            LEFT JOIN play_sessions ps ON g.id = ps.game_id
            LEFT JOIN users u ON g.owner_id = u.id
            LEFT JOIN games p ON g.parent_id = p.id
            WHERE g.id = ?
            """,
            (game_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return GameWithData.from_row(row) if row else None

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

    async def delete_game_by_id(self, id: str) -> None:
        """Delete a game by ID"""
        assert self._connection is not None and self._cursor is not None
        await self._connection.execute("DELETE FROM games WHERE id = ?", (id,))
        await self._connection.commit()

    async def get_game_by_name(self, name: str) -> Optional[Game]:
        """Fetch a game by name"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, name, description, owner_id, parent_id, created_at, updated_at, cover_image, version FROM games WHERE name = ?",
            (name,),
        ) as cursor:
            row = await cursor.fetchone()
            return Game.from_row(row) if row else None

    async def get_games_by_owner_id(self, owner_id: str) -> List[Game]:
        """Fetch all games by owner ID"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, name, description, owner_id, parent_id, created_at, updated_at, cover_image, version FROM games WHERE owner_id = ?",
            (owner_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [Game.from_row(row) for row in rows]

    async def create_message(self, message: Message) -> None:
        """Create a new message"""
        assert self._connection is not None and self._cursor is not None
        await self._connection.execute(
            """
            INSERT INTO messages (id, game_id, text, role, timestamp, cost, status, commit_sha, model, messages)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                message.messages,
            ),
        )
        await self._connection.commit()

    async def get_all_messages(self) -> List[Message]:
        """Fetch all messages"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, game_id, text, role, timestamp, cost, status, commit_sha, model, messages FROM messages"
        ) as cursor:
            rows = await cursor.fetchall()
            return [Message.from_row(row) for row in rows]

    async def get_messages_by_game_id(self, game_id: str) -> List[Message]:
        """Fetch all messages for a game"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, game_id, text, role, timestamp, cost, status, commit_sha, model, messages FROM messages WHERE game_id = ?",
            (game_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [Message.from_row(row) for row in rows]

    async def get_message_by_id(self, message_id: str) -> Optional[Message]:
        """Fetch a message by ID"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, game_id, text, role, timestamp, cost, status, commit_sha, model, messages FROM messages WHERE id = ?",
            (message_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return Message.from_row(row) if row else None

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

    async def delete_message_by_id(self, id: str) -> None:
        """Delete a message by ID"""
        assert self._connection is not None and self._cursor is not None
        await self._connection.execute("DELETE FROM messages WHERE id = ?", (id,))
        await self._connection.commit()

    async def create_transaction(self, transaction: Transaction) -> None:
        """Create a new transaction"""
        assert self._connection is not None and self._cursor is not None
        await self._connection.execute(
            """
            INSERT INTO transactions (id, user_id, session_id, status, created_at, updated_at, amount, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction.id,
                transaction.user_id,
                transaction.session_id,
                transaction.status,
                transaction.created_at,
                transaction.updated_at,
                transaction.amount,
                transaction.description,
            ),
        )
        await self._connection.commit()

    async def get_all_transactions(self) -> List[Transaction]:
        """Fetch all transactions"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, user_id, session_id, status, created_at, updated_at, amount, description FROM transactions"
        ) as cursor:
            rows = await cursor.fetchall()
            return [Transaction.from_row(row) for row in rows]

    async def get_transaction_by_session_id(
        self, session_id: str
    ) -> Optional[Transaction]:
        """Fetch a transaction by session ID"""
        assert self._connection is not None and self._cursor is not None
        async with self._connection.execute(
            "SELECT id, user_id, session_id, status, created_at, updated_at, amount, description FROM transactions WHERE session_id = ?",
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return Transaction.from_row(row) if row else None

    async def update_transaction_by_id(self, id: str, **kwargs) -> None:
        """Update a transaction"""
        assert self._connection is not None and self._cursor is not None
        assert all(key in Transaction.__annotations__ for key in kwargs)
        await self._connection.execute(
            """
            UPDATE transactions SET {} WHERE id = ?
            """.format(", ".join([f"{key} = ?" for key in kwargs])),
            tuple(kwargs.values()) + (id,),
        )
        await self._connection.commit()

    async def create_play_session(self, play_session: PlaySession) -> None:
        """Create a new play session"""
        assert self._connection is not None and self._cursor is not None
        await self._connection.execute(
            """
            INSERT INTO play_sessions (id, user_id, game_id, created_at, seconds)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                play_session.id,
                play_session.user_id,
                play_session.game_id,
                play_session.created_at,
                play_session.seconds,
            ),
        )
        await self._connection.commit()
