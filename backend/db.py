import json
import subprocess
from asyncio import Lock
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Optional, List, Literal
from uuid import UUID, uuid4


class User(TypedDict):
    id: str
    username: str
    email: str
    created_at: str  # ISO format string of datetime
    avatar_id: Optional[str]


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
    owner_id: str
    parent_id: Optional[str]
    created_at: str  # ISO format string of datetime
    updated_at: str  # ISO format string of datetime
    plays: int
    messages: List[Message]


class Database(TypedDict):
    users: dict[UUID, User]
    games: dict[UUID, Game]


DB_PATH = Path(__file__).parent / "db.json"
GAMES_PATH = Path(__file__).parent / "games"
ADMIN_EMAIL = "granthawkins88@gmail.com"


class DB:
    def __init__(self):
        if not DB_PATH.exists():
            _db = {"users": {}, "games": {}}

            # Setup Admin user
            admin_id = str(uuid4())
            _db["users"][admin_id] = {
                "id": admin_id,
                "username": "admin",
                "email": ADMIN_EMAIL,
                "created_at": datetime.now().isoformat(),
                "avatar_id": None,
            }

            for dir in GAMES_PATH.iterdir():
                id = str(uuid4())
                _db["games"][id] = {
                    "id": id,
                    "name": dir.name,
                    "owner_id": admin_id,
                    "parent_id": None,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "plays": 0,
                    "messages": [],
                }
                # Create a new directory with the game_id and copy the contents
                game_dir = GAMES_PATH / id
                game_dir.mkdir(exist_ok=True)

                # Copy the contents from the original directory to the new one
                import shutil

                for item in (GAMES_PATH / dir.name).iterdir():
                    if item.is_file():
                        shutil.copy2(item, game_dir)
                    elif item.is_dir():
                        shutil.copytree(item, game_dir / item.name)

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
