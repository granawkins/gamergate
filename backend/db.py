import json
import shutil
import subprocess
from asyncio import Lock
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Optional, List, Literal
from uuid import UUID, uuid4


class User(TypedDict):
    id: str
    created_at: str  # ISO format string of datetime
    messages_left: int
    username: Optional[str]
    email: Optional[str]
    avatar_id: Optional[str]
    admin: bool


class Message(TypedDict, total=False):
    id: str
    text: str
    role: Literal["user", "assistant"]
    timestamp: str
    cost: Optional[float]
    status: Literal["processing", "completed", "error"]
    commit_sha: Optional[str]


class Game(TypedDict):
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    parent_id: Optional[str]
    created_at: str  # ISO format string of datetime
    updated_at: str  # ISO format string of datetime
    messages: List[Message]


class Transaction(TypedDict):
    id: str
    user_id: str
    session_id: str
    status: str
    created_at: str
    updated_at: str


class Database(TypedDict):
    users: dict[UUID, User]
    games: dict[UUID, Game]
    transactions: dict[str, Transaction]


DB_PATH = Path(__file__).parent / "db.json"
GAMES_PATH = Path(__file__).parent / "games"
ADMIN_EMAIL = "granthawkins88@gmail.com"


class DB:
    def __init__(self):
        if not DB_PATH.exists():
            _db = {"users": {}, "games": {}, "transactions": {}}

            # Setup Admin user
            admin_id = str(uuid4())
            _db["users"][admin_id] = {
                "id": admin_id,
                "username": "admin",
                "email": ADMIN_EMAIL,
                "created_at": datetime.now().isoformat(),
                "avatar_id": None,
                "messages_left": 10,
                "admin": True,
            }

            for dir in GAMES_PATH.iterdir():
                id = str(uuid4())
                _db["games"][id] = {
                    "id": id,
                    "name": dir.name,
                    "description": "",
                    "owner_id": "",  # Empty owner_id means it's a template
                    "parent_id": None,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "messages": [],
                }

                # Create a new directory with the game_id and copy the contents
                game_dir = GAMES_PATH / id
                shutil.copytree(GAMES_PATH / dir.name, game_dir)

                # Initialize a git repo for the game
                subprocess.run(["git", "init"], cwd=game_dir)
                subprocess.run(["git", "add", "."], cwd=game_dir)
                subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=game_dir)
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
