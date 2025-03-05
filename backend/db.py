import json
import shutil
import subprocess
from asyncio import Lock
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Optional, List, Literal, Dict
from uuid import uuid4


class User(TypedDict):
    id: str
    created_at: str  # ISO format string of datetime
    messages_left: int
    username: Optional[str]
    email: Optional[str]
    avatar_id: Optional[str]


class Message(TypedDict, total=False):
    id: str
    text: str
    role: Literal["user", "assistant"]
    timestamp: str
    cost: Optional[float]
    status: Literal["processing", "completed", "error"]
    commit_sha: Optional[str]


class PlaySession(TypedDict):
    id: str
    user_id: str
    game_id: str
    seconds_played: int
    timestamp: str  # ISO format string of datetime


class Game(TypedDict):
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    parent_id: Optional[str]
    created_at: str  # ISO format string of datetime
    updated_at: str  # ISO format string of datetime
    messages: List[Message]


class Database(TypedDict):
    users: Dict[str, User]
    games: Dict[str, Game]
    play_sessions: Dict[str, PlaySession]


DB_PATH = Path(__file__).parent / "db.json"
GAMES_PATH = Path(__file__).parent / "games"
ADMIN_EMAIL = "granthawkins88@gmail.com"


class DB:
    def __init__(self):
        if not DB_PATH.exists():
            _db = {"users": {}, "games": {}, "play_sessions": {}}

            # Setup Admin user
            admin_id = str(uuid4())
            _db["users"][admin_id] = {
                "id": admin_id,
                "username": "admin",
                "email": ADMIN_EMAIL,
                "created_at": datetime.now().isoformat(),
                "avatar_id": None,
                "messages_left": 10,
            }

            for dir in GAMES_PATH.iterdir():
                id = str(uuid4())
                _db["games"][id] = {
                    "id": id,
                    "name": dir.name,
                    "description": "",
                    "owner_id": admin_id,
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
        else:
            # Check if play_sessions exists in the DB, add it if not
            self._ensure_play_sessions_exists()
        self.lock = Lock()

    def _ensure_play_sessions_exists(self):
        """Ensure the play_sessions table exists in the database."""
        try:
            with open(DB_PATH, "r") as f:
                data = json.load(f)

            if "play_sessions" not in data:
                data["play_sessions"] = {}
                with open(DB_PATH, "w") as f:
                    json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error ensuring play_sessions exists: {e}")

    async def get(self) -> dict:
        async with self.lock:
            with open(DB_PATH, "r") as f:
                return json.load(f)

    async def set(self, data: dict) -> None:
        async with self.lock:
            with open(DB_PATH, "w") as f:
                json.dump(data, f, indent=4)


db = DB()
