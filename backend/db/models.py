from __future__ import annotations

from aiosqlite import Row

from dataclasses import dataclass
from typing import Optional, Literal


@dataclass
class User:
    id: str
    created_at: str  # ISO format string of datetime
    messages_left: int
    username: Optional[str]
    email: Optional[str]
    avatar_id: Optional[str]

    @classmethod
    def from_row(cls, row: Row) -> "User":
        return cls(
            id=row[0],
            created_at=row[1],
            messages_left=row[2],
            username=row[3],
            email=row[4],
            avatar_id=row[5],
        )


@dataclass
class Message:
    id: str
    text: str
    role: Literal["user", "assistant"]
    timestamp: str
    cost: Optional[float]
    status: Literal["processing", "completed", "error"]
    commit_sha: Optional[str]
    model: Optional[str]

    @classmethod
    def from_row(cls, row: Row) -> "Message":
        return cls(
            id=row[0],
            text=row[1],
            role=row[2],
            timestamp=row[3],
            cost=row[4],
            status=row[5],
            commit_sha=row[6],
            model=row[7],
        )


@dataclass
class Game:
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    parent_id: Optional[str]
    created_at: str  # ISO format string of datetime
    updated_at: str  # ISO format string of datetime
    cover_image: Optional[str]  # Base64 encoded image string
    version: int  # Version number of the game

    @classmethod
    def from_row(cls, row: Row) -> "Game":
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
        )


@dataclass
class Transaction:
    id: str
    user_id: str
    session_id: str
    status: str
    created_at: str
    updated_at: str
    amount: int
    description: str

    @classmethod
    def from_row(cls, row: Row) -> "Transaction":
        return cls(
            id=row[0],
            user_id=row[1],
            session_id=row[2],
            status=row[3],
            created_at=row[4],
            updated_at=row[5],
            amount=row[6],
            description=row[7],
        )


@dataclass
class PlaySession:
    id: str
    user_id: str
    game_id: str
    created_at: str
    seconds: int

    @classmethod
    def from_row(cls, row: Row) -> "PlaySession":
        return cls(
            id=row[0],
            user_id=row[1],
            game_id=row[2],
            created_at=row[3],
            seconds=row[4],
        )
