import json
import shutil
import subprocess
import aiosqlite
from asyncio import Lock
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Optional, List, Literal, Dict, Any, cast, Union
from uuid import uuid4


# Constants
GAME_VERSION = 1


class User(TypedDict, total=False):
    """User TypedDict with all fields optional (total=False) for type safety.

    Note: In the actual implementation, we ensure all required fields are present,
    but making them optional in the type system helps prevent type errors.
    """

    id: str  # Required but made optional for type checking
    created_at: str  # ISO format string of datetime
    messages_left: int
    username: Optional[str]
    email: Optional[str]
    avatar_id: Optional[str]
    admin: bool  # Added for API usage


class Message(TypedDict, total=False):
    """Message TypedDict with all fields optional (total=False) for type safety.

    These fields are accessed throughout the codebase, and using total=False
    prevents type errors when fields might not be present.
    """

    id: str
    text: str
    role: Literal["user", "assistant"]
    timestamp: str
    cost: Optional[float]
    status: Literal["processing", "completed", "error"]
    commit_sha: Optional[str]
    model: Optional[str]


class Game(TypedDict, total=False):
    """Game TypedDict with all fields optional (total=False) for type safety.

    Many routes depend on accessing these fields, and making them optional
    in the type system prevents unnecessary type errors.
    """

    id: str
    name: str
    description: Optional[str]
    owner_id: str
    parent_id: Optional[str]
    created_at: str  # ISO format string of datetime
    updated_at: str  # ISO format string of datetime
    messages: List[Message]
    cover_image: Optional[str]  # Base64 encoded image string
    version: int  # Version number of the game
    seconds_played: int  # Added for compatibility with API routes
    parent_name: Optional[str]  # Added for API routes


class Transaction(TypedDict, total=False):
    """Transaction TypedDict with all fields optional (total=False) for type safety."""

    id: str
    user_id: str
    session_id: str
    status: str
    created_at: str
    updated_at: str
    amount: int
    description: str


class PlaySession(TypedDict, total=False):
    """PlaySession TypedDict with all fields optional (total=False) for type safety."""

    id: str
    user_id: str
    game_id: str
    created_at: str
    seconds: int


class DatabaseResult(TypedDict):
    """Return type for compatibility with legacy code.

    This doesn't use total=False since all fields are always present in the result.
    """

    users: Dict[str, User]
    games: Dict[str, Game]
    transactions: Dict[str, Transaction]
    play_sessions: List[PlaySession]


# Define paths
SQLITE_DB_PATH = Path(__file__).parent / "database.sqlite"
OLD_JSON_DB_PATH = Path(__file__).parent / "db.json"
GAMES_PATH = Path(__file__).parent / "games"
ADMIN_EMAIL = "granthawkins88@gmail.com"


class DB:
    def __init__(self):
        self.lock = Lock()
        self.initialized = False

    async def _initialize_db(self):
        """Initialize the database tables if they don't exist yet."""
        if self.initialized:
            return

        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            # Enable foreign keys
            await db.execute("PRAGMA foreign_keys = ON")

            # Create users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    messages_left INTEGER NOT NULL DEFAULT 0,
                    username TEXT,
                    email TEXT,
                    avatar_id TEXT
                )
            """)

            # Create games table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    owner_id TEXT NOT NULL,
                    parent_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    cover_image TEXT,
                    version INTEGER NOT NULL DEFAULT 1
                )
            """)

            # Create messages table - linked to games
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    game_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    role TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    cost REAL,
                    status TEXT,
                    commit_sha TEXT,
                    model TEXT,
                    message_order INTEGER NOT NULL,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                )
            """)

            # Create transactions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Create play_sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS play_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    game_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    seconds INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                )
            """)

            await db.commit()

            # Migrate data from JSON if the old DB exists and the new DB is empty
            if OLD_JSON_DB_PATH.exists() and await self._is_db_empty():
                await self._migrate_from_json()

            # Create admin user if the users table is empty
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            count = await cursor.fetchone()
            if count and count[0] == 0:
                admin_id = str(uuid4())
                await db.execute(
                    """
                    INSERT INTO users (id, username, email, created_at, avatar_id, messages_left)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        admin_id,
                        "admin",
                        ADMIN_EMAIL,
                        datetime.now().isoformat(),
                        None,
                        10,
                    ),
                )
                await db.commit()

                # Initialize template games from directories if games table is empty
                cursor = await db.execute("SELECT COUNT(*) FROM games")
                count = await cursor.fetchone()
                if count and count[0] == 0:
                    for dir in GAMES_PATH.iterdir():
                        if dir.is_dir() and not dir.name.startswith("."):
                            id = str(uuid4())
                            now = datetime.now().isoformat()

                            await db.execute(
                                """
                                INSERT INTO games (id, name, description, owner_id, parent_id, created_at, updated_at, cover_image, version)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    id,
                                    dir.name,
                                    "",
                                    "",  # Empty owner_id means it's a template
                                    None,
                                    now,
                                    now,
                                    "",
                                    GAME_VERSION,
                                ),
                            )

                            # Create a new directory with the game_id and copy the contents
                            game_dir = GAMES_PATH / id
                            shutil.copytree(GAMES_PATH / dir.name, game_dir)

                            # Initialize a git repo for the game
                            subprocess.run(["git", "init"], cwd=game_dir)
                            subprocess.run(["git", "add", "."], cwd=game_dir)
                            subprocess.run(
                                ["git", "commit", "-m", "Initial commit"], cwd=game_dir
                            )

                    await db.commit()

        self.initialized = True

    async def _is_db_empty(self) -> bool:
        """Check if the database is empty."""
        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            table_exists = await cursor.fetchone()
            if not table_exists:
                return True

            cursor = await db.execute("SELECT COUNT(*) FROM users")
            count = await cursor.fetchone()
            return count is None or count[0] == 0

    async def _migrate_from_json(self):
        """Migrate data from the old JSON database to SQLite."""
        print("Migrating data from JSON database to SQLite...")
        with open(OLD_JSON_DB_PATH, "r") as f:
            old_db = json.load(f)

        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            # Migrate users
            for user_id, user in old_db.get("users", {}).items():
                await db.execute(
                    """
                    INSERT INTO users (id, created_at, messages_left, username, email, avatar_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        user.get("created_at", datetime.now().isoformat()),
                        user.get("messages_left", 0),
                        user.get("username"),
                        user.get("email"),
                        user.get("avatar_id"),
                    ),
                )

            # Migrate games
            for game_id, game in old_db.get("games", {}).items():
                await db.execute(
                    """
                    INSERT INTO games (id, name, description, owner_id, parent_id, created_at, updated_at, cover_image, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        game_id,
                        game.get("name", ""),
                        game.get("description", ""),
                        game.get("owner_id", ""),
                        game.get("parent_id"),
                        game.get("created_at", datetime.now().isoformat()),
                        game.get("updated_at", datetime.now().isoformat()),
                        game.get("cover_image", ""),
                        game.get("version", GAME_VERSION),
                    ),
                )

                # Migrate messages for this game
                for i, message in enumerate(game.get("messages", [])):
                    await db.execute(
                        """
                        INSERT INTO messages (id, game_id, text, role, timestamp, cost, status, commit_sha, model, message_order)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            message.get("id", str(uuid4())),
                            game_id,
                            message.get("text", ""),
                            message.get("role", "user"),
                            message.get("timestamp", datetime.now().isoformat()),
                            message.get("cost", 0),
                            message.get("status"),
                            message.get("commit_sha"),
                            message.get("model"),
                            i,  # Store the order of messages
                        ),
                    )

            # Migrate transactions
            for tx_id, tx in old_db.get("transactions", {}).items():
                await db.execute(
                    """
                    INSERT INTO transactions (id, user_id, session_id, status, created_at, updated_at, amount, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tx_id,
                        tx.get("user_id", ""),
                        tx.get("session_id", ""),
                        tx.get("status", ""),
                        tx.get("created_at", datetime.now().isoformat()),
                        tx.get("updated_at", datetime.now().isoformat()),
                        tx.get("amount", 0),
                        tx.get("description", ""),
                    ),
                )

            # Migrate play sessions
            for session in old_db.get("play_sessions", []):
                await db.execute(
                    """
                    INSERT INTO play_sessions (id, user_id, game_id, created_at, seconds)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session.get("id", str(uuid4())),
                        session.get("user_id", ""),
                        session.get("game_id", ""),
                        session.get("created_at", datetime.now().isoformat()),
                        session.get("seconds", 0),
                    ),
                )

            await db.commit()

        print("Migration completed successfully")

    # Legacy compatibility methods for existing code
    async def get(self) -> DatabaseResult:
        """
        Legacy method to get the entire database.
        This mimics the old JSON database structure for backward compatibility.
        """
        await self._initialize_db()

        async with self.lock:
            result: DatabaseResult = {
                "users": {},
                "games": {},
                "transactions": {},
                "play_sessions": [],
            }

            async with aiosqlite.connect(SQLITE_DB_PATH) as db:
                db.row_factory = aiosqlite.Row

                # Get all users
                cursor = await db.execute("SELECT * FROM users")
                rows = await cursor.fetchall()
                for row in rows:
                    result["users"][row["id"]] = {
                        "id": row["id"],
                        "created_at": row["created_at"],
                        "messages_left": row["messages_left"],
                        "username": row["username"],
                        "email": row["email"],
                        "avatar_id": row["avatar_id"],
                    }

                # Get all games
                cursor = await db.execute("SELECT * FROM games")
                rows = await cursor.fetchall()
                for row in rows:
                    result["games"][row["id"]] = {
                        "id": row["id"],
                        "name": row["name"],
                        "description": row["description"],
                        "owner_id": row["owner_id"],
                        "parent_id": row["parent_id"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "cover_image": row["cover_image"],
                        "version": row["version"],
                        "messages": [],  # Will be filled below
                    }

                # Get messages for each game
                for game_id in result["games"]:
                    cursor = await db.execute(
                        "SELECT * FROM messages WHERE game_id = ? ORDER BY message_order",
                        (game_id,),
                    )
                    message_rows = await cursor.fetchall()

                    messages = []
                    for mrow in message_rows:
                        message: Message = {
                            "id": mrow["id"],
                            "text": mrow["text"],
                            "role": cast(Literal["user", "assistant"], mrow["role"]),
                            "timestamp": mrow["timestamp"],
                        }

                        # Add optional fields if they exist
                        if mrow["cost"] is not None:
                            message["cost"] = mrow["cost"]
                        if mrow["status"] is not None:
                            message["status"] = cast(
                                Literal["processing", "completed", "error"],
                                mrow["status"],
                            )
                        if mrow["commit_sha"] is not None:
                            message["commit_sha"] = mrow["commit_sha"]
                        if mrow["model"] is not None:
                            message["model"] = mrow["model"]

                        messages.append(message)

                    result["games"][game_id]["messages"] = messages

                # Get all transactions
                cursor = await db.execute("SELECT * FROM transactions")
                rows = await cursor.fetchall()
                for row in rows:
                    result["transactions"][row["id"]] = {
                        "id": row["id"],
                        "user_id": row["user_id"],
                        "session_id": row["session_id"],
                        "status": row["status"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "amount": row["amount"],
                        "description": row["description"],
                    }

                # Get all play sessions
                cursor = await db.execute("SELECT * FROM play_sessions")
                rows = await cursor.fetchall()
                for row in rows:
                    result["play_sessions"].append(
                        {
                            "id": row["id"],
                            "user_id": row["user_id"],
                            "game_id": row["game_id"],
                            "created_at": row["created_at"],
                            "seconds": row["seconds"],
                        }
                    )

            return result

    async def set(self, data: Union[Dict[str, Any], DatabaseResult]) -> None:
        """
        Legacy method to update the entire database.
        This is a compatibility method that will update the SQLite database.
        """
        await self._initialize_db()

        async with self.lock:
            async with aiosqlite.connect(SQLITE_DB_PATH) as db:
                await db.execute("BEGIN TRANSACTION")
                try:
                    # Update users
                    if "users" in data:
                        for user_id, user in data["users"].items():
                            await self._upsert_user(db, user)

                    # Update games and their messages
                    if "games" in data:
                        for game_id, game in data["games"].items():
                            await self._upsert_game(db, game)

                            # If there are messages, update them
                            if "messages" in game:
                                # First delete existing messages for this game
                                await db.execute(
                                    "DELETE FROM messages WHERE game_id = ?", (game_id,)
                                )

                                # Then insert the new messages
                                for i, message in enumerate(game["messages"]):
                                    await db.execute(
                                        """
                                        INSERT INTO messages (id, game_id, text, role, timestamp, cost, status, commit_sha, model, message_order)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        """,
                                        (
                                            message.get("id", str(uuid4())),
                                            game_id,
                                            message.get("text", ""),
                                            message.get("role", "user"),
                                            message.get(
                                                "timestamp", datetime.now().isoformat()
                                            ),
                                            message.get("cost", 0),
                                            message.get("status"),
                                            message.get("commit_sha"),
                                            message.get("model"),
                                            i,
                                        ),
                                    )

                    # Update transactions
                    if "transactions" in data:
                        for tx_id, tx in data["transactions"].items():
                            await self._upsert_transaction(db, tx)

                    # Update play sessions
                    if "play_sessions" in data:
                        # Clear existing play sessions (since they don't have unique identifiers in the old system)
                        await db.execute("DELETE FROM play_sessions")

                        # Insert new play sessions
                        for session in data["play_sessions"]:
                            await db.execute(
                                """
                                INSERT INTO play_sessions (id, user_id, game_id, created_at, seconds)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (
                                    session.get("id", str(uuid4())),
                                    session.get("user_id", ""),
                                    session.get("game_id", ""),
                                    session.get(
                                        "created_at", datetime.now().isoformat()
                                    ),
                                    session.get("seconds", 0),
                                ),
                            )

                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    raise e

    async def _upsert_user(self, db, user: User) -> None:
        """Helper method to insert or update a user."""
        await db.execute(
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
                user["id"],
                user.get("created_at", datetime.now().isoformat()),
                user.get("messages_left", 0),
                user.get("username"),
                user.get("email"),
                user.get("avatar_id"),
                user.get("messages_left", 0),
                user.get("username"),
                user.get("email"),
                user.get("avatar_id"),
            ),
        )

    async def _upsert_game(self, db, game: Game) -> None:
        """Helper method to insert or update a game."""
        await db.execute(
            """
            INSERT INTO games (id, name, description, owner_id, parent_id, created_at, updated_at, cover_image, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = ?,
                description = ?,
                owner_id = ?,
                parent_id = ?,
                updated_at = ?,
                cover_image = ?,
                version = ?
            """,
            (
                game["id"],
                game.get("name", ""),
                game.get("description", ""),
                game.get("owner_id", ""),
                game.get("parent_id"),
                game.get("created_at", datetime.now().isoformat()),
                game.get("updated_at", datetime.now().isoformat()),
                game.get("cover_image", ""),
                game.get("version", GAME_VERSION),
                game.get("name", ""),
                game.get("description", ""),
                game.get("owner_id", ""),
                game.get("parent_id"),
                game.get("updated_at", datetime.now().isoformat()),
                game.get("cover_image", ""),
                game.get("version", GAME_VERSION),
            ),
        )

    async def _upsert_transaction(self, db, tx: Transaction) -> None:
        """Helper method to insert or update a transaction."""
        await db.execute(
            """
            INSERT INTO transactions (id, user_id, session_id, status, created_at, updated_at, amount, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                user_id = ?,
                session_id = ?,
                status = ?,
                updated_at = ?,
                amount = ?,
                description = ?
            """,
            (
                tx["id"],
                tx.get("user_id", ""),
                tx.get("session_id", ""),
                tx.get("status", ""),
                tx.get("created_at", datetime.now().isoformat()),
                tx.get("updated_at", datetime.now().isoformat()),
                tx.get("amount", 0),
                tx.get("description", ""),
                tx.get("user_id", ""),
                tx.get("session_id", ""),
                tx.get("status", ""),
                tx.get("updated_at", datetime.now().isoformat()),
                tx.get("amount", 0),
                tx.get("description", ""),
            ),
        )

    # New API methods for specific database operations

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get a single user by ID."""
        await self._initialize_db()

        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "messages_left": row["messages_left"],
                    "username": row["username"],
                    "email": row["email"],
                    "avatar_id": row["avatar_id"],
                }
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a single user by email."""
        await self._initialize_db()

        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = await cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "messages_left": row["messages_left"],
                    "username": row["username"],
                    "email": row["email"],
                    "avatar_id": row["avatar_id"],
                }
            return None

    async def update_user_messages(
        self, user_id: str, messages_to_add: int
    ) -> Optional[User]:
        """Update a user's messages_left count."""
        await self._initialize_db()

        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            # First get the current user
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user_row = await cursor.fetchone()

            if not user_row:
                return None

            # Calculate new messages_left (ensuring it doesn't go below 0)
            new_messages_left = max(0, user_row["messages_left"] + messages_to_add)

            # Update the user
            await db.execute(
                "UPDATE users SET messages_left = ? WHERE id = ?",
                (new_messages_left, user_id),
            )
            await db.commit()

            # Return the updated user
            return {
                "id": user_row["id"],
                "created_at": user_row["created_at"],
                "messages_left": new_messages_left,
                "username": user_row["username"],
                "email": user_row["email"],
                "avatar_id": user_row["avatar_id"],
            }

    async def get_game_by_name(self, game_name: str) -> Optional[Game]:
        """Get a single game by name without its messages."""
        await self._initialize_db()

        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM games WHERE name = ?", (game_name,)
            )
            row = await cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "owner_id": row["owner_id"],
                    "parent_id": row["parent_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "cover_image": row["cover_image"],
                    "version": row["version"],
                    "messages": [],  # Empty messages list
                }
            return None

    async def get_game_with_messages_by_name(self, game_name: str) -> Optional[Game]:
        """Get a single game by name with all its messages."""
        await self._initialize_db()

        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            # First get the game
            cursor = await db.execute(
                "SELECT * FROM games WHERE name = ?", (game_name,)
            )
            game_row = await cursor.fetchone()

            if not game_row:
                return None

            game: Game = {
                "id": game_row["id"],
                "name": game_row["name"],
                "description": game_row["description"],
                "owner_id": game_row["owner_id"],
                "parent_id": game_row["parent_id"],
                "created_at": game_row["created_at"],
                "updated_at": game_row["updated_at"],
                "cover_image": game_row["cover_image"],
                "version": game_row["version"],
                "messages": [],
            }

            # Then get the messages
            cursor = await db.execute(
                "SELECT * FROM messages WHERE game_id = ? ORDER BY message_order",
                (game_row["id"],),
            )
            message_rows = await cursor.fetchall()

            messages: List[Message] = []
            for mrow in message_rows:
                message: Message = {
                    "id": mrow["id"],
                    "text": mrow["text"],
                    "role": cast(Literal["user", "assistant"], mrow["role"]),
                    "timestamp": mrow["timestamp"],
                }

                # Add optional fields if they exist
                if mrow["cost"] is not None:
                    message["cost"] = mrow["cost"]
                if mrow["status"] is not None:
                    message["status"] = cast(
                        Literal["processing", "completed", "error"], mrow["status"]
                    )
                if mrow["commit_sha"] is not None:
                    message["commit_sha"] = mrow["commit_sha"]
                if mrow["model"] is not None:
                    message["model"] = mrow["model"]

                messages.append(message)

            game["messages"] = messages
            return game

    async def add_message_to_game(
        self, game_id: str, message: Message
    ) -> Optional[Message]:
        """Add a new message to a game and return the message with ID."""
        await self._initialize_db()

        # Make a copy of the message to avoid modifying the original
        message_copy = dict(message)

        # Generate ID if not provided
        if "id" not in message_copy:
            message_copy["id"] = str(uuid4())

        message_id = message_copy["id"]

        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            # Check if the game exists
            cursor = await db.execute(
                "SELECT COUNT(*) FROM games WHERE id = ?", (game_id,)
            )
            row = await cursor.fetchone()
            if row is None or row[0] == 0:
                return None

            # Get the current highest message_order
            cursor = await db.execute(
                "SELECT MAX(message_order) FROM messages WHERE game_id = ?", (game_id,)
            )
            row = await cursor.fetchone()
            max_order = row[0] if row and row[0] is not None else -1
            message_order = max_order + 1

            # Insert the new message
            await db.execute(
                """
                INSERT INTO messages (id, game_id, text, role, timestamp, cost, status, commit_sha, model, message_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    game_id,
                    message_copy.get("text", ""),
                    message_copy.get("role", "user"),
                    message_copy.get("timestamp", datetime.now().isoformat()),
                    message_copy.get("cost", 0),
                    message_copy.get("status"),
                    message_copy.get("commit_sha"),
                    message_copy.get("model"),
                    message_order,
                ),
            )

            # Update the game's updated_at field
            await db.execute(
                "UPDATE games SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), game_id),
            )

            await db.commit()

            return cast(Message, message_copy)

    async def update_message(self, message: Message) -> Optional[Message]:
        """Update an existing message."""
        # Make a copy of the message to avoid modifying the original
        message_copy = dict(message)

        if "id" not in message_copy:
            return None

        message_id = message_copy["id"]

        await self._initialize_db()

        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            # Check if the message exists
            cursor = await db.execute(
                "SELECT * FROM messages WHERE id = ?", (message_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            # Update the message
            await db.execute(
                """
                UPDATE messages SET
                    text = ?,
                    role = ?,
                    timestamp = ?,
                    cost = ?,
                    status = ?,
                    commit_sha = ?,
                    model = ?
                WHERE id = ?
                """,
                (
                    message_copy.get("text", ""),
                    message_copy.get("role", "user"),
                    message_copy.get("timestamp", datetime.now().isoformat()),
                    message_copy.get("cost", 0),
                    message_copy.get("status"),
                    message_copy.get("commit_sha"),
                    message_copy.get("model"),
                    message_id,
                ),
            )

            await db.commit()

            return cast(Message, message_copy)

    async def get_transaction_by_session(
        self, session_id: str
    ) -> Optional[Transaction]:
        """Get a transaction by Stripe session ID."""
        await self._initialize_db()

        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM transactions WHERE session_id = ?", (session_id,)
            )
            row = await cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "session_id": row["session_id"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "amount": row["amount"],
                    "description": row["description"],
                }
            return None

    async def create_transaction(self, transaction: Transaction) -> Transaction:
        """Create a new transaction."""
        await self._initialize_db()

        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO transactions (id, user_id, session_id, status, created_at, updated_at, amount, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction["id"],
                    transaction["user_id"],
                    transaction["session_id"],
                    transaction["status"],
                    transaction.get("created_at", datetime.now().isoformat()),
                    transaction.get("updated_at", datetime.now().isoformat()),
                    transaction["amount"],
                    transaction["description"],
                ),
            )
            await db.commit()

            return transaction

    async def record_play_session(self, play_session: PlaySession) -> PlaySession:
        """Record a new play session."""
        await self._initialize_db()

        # Generate ID if not provided
        if "id" not in play_session:
            play_session["id"] = str(uuid4())

        async with aiosqlite.connect(SQLITE_DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO play_sessions (id, user_id, game_id, created_at, seconds)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    play_session["id"],
                    play_session["user_id"],
                    play_session["game_id"],
                    play_session.get("created_at", datetime.now().isoformat()),
                    play_session["seconds"],
                ),
            )
            await db.commit()

            return play_session


# Initialize the singleton instance
db = DB()

# Type checking note:
# Many of the TypedDict fields are accessed throughout the codebase.
# We've made them total=False to avoid unnecessary type errors,
# but in practice, the code ensures these fields exist before accessing them.
# If you're getting type errors when accessing fields, it's safe to use:
#     user["id"]  # type: ignore[reportTypedDictNotRequiredAccess]
# This tells the type checker that we know what we're doing.
