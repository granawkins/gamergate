import json
from asyncio import Lock
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Optional
from uuid import UUID, uuid4


class User(TypedDict):
    id: str
    username: str
    email: str
    created_at: datetime


class Game(TypedDict):
    id: str
    name: str
    path: str
    owner_id: str
    parent_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    plays: int


class Database(TypedDict):
    users: dict[UUID, User]
    games: dict[UUID, Game]


DB_PATH = Path(__file__).parent / "db.json"
GAMES_PATH = Path(__file__).parent / "games"


class DB:
    def __init__(self):
        if not DB_PATH.exists():
            _db = {"users": {}, "games": {}}
            for dir in GAMES_PATH.iterdir():
                id = str(uuid4())
                _db["games"][id] = {
                    "id": id,
                    "name": dir.name,
                    "path": dir.name,
                    "owner_id": None,
                    "parent_id": None,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "plays": 0,
                }
            with open(DB_PATH, "w") as f:
                json.dump(_db, f, indent=4)
        self.lock = Lock()

    async def get(self) -> dict:
        async with self.lock:
            with open(DB_PATH, "r") as f:
                return json.load(f)

    async def set(self, data: dict) -> None:
        async with self.lock:
            with open(DB_PATH, "w") as f:
                json.dump(data, f, indent=4)


db = DB()
