import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Optional, List, Dict, Literal, Any, cast, TypeVar
from uuid import uuid4

import aiosqlite

# Constants
GAME_VERSION = 1
GAMES_PATH = Path(__file__).parent / "games"
ADMIN_EMAIL = "granthawkins88@gmail.com"
DB_PATH = Path(__file__).parent / "gamergate.db"


# Type definitions
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
    model: Optional[str]


class Game(TypedDict):
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


class Transaction(TypedDict):
    id: str
    user_id: str
    session_id: str
    status: str
    created_at: str
    updated_at: str
    amount: int
    description: str


class PlaySession(TypedDict):
    id: str
    user_id: str
    game_id: str
    created_at: str
    seconds: int


# Type variable for any dictionary
T = TypeVar("T", bound=Dict[str, Any])


class DBSQLite:
    def __init__(self):
        self.conn = None
        self.lock = asyncio.Lock()
        self._schema_version = 0

    async def initialize(self):
        """Initialize the database connection and run migrations if needed."""
        # Ensure we only initialize once
        if self.conn is not None:
            return

        async with self.lock:
            # Create database directory if it doesn't exist
            DB_PATH.parent.mkdir(exist_ok=True)

            # Connect to the database
            self.conn = await aiosqlite.connect(DB_PATH)

            # Enable foreign keys
            await self.conn.execute("PRAGMA foreign_keys = ON")

            # Run migrations
            await self._run_migrations()

            # Import data from JSON if needed (first-time setup)
            if self._schema_version == 1:  # First migration completed
                await self._import_json_data()

    async def close(self):
        """Close the database connection."""
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def _run_migrations(self):
        """Run any pending database migrations."""
        # Check if schema_version table exists
        cursor = await self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        if not await cursor.fetchone():
            # Create schema_version table
            await self.conn.execute(
                "CREATE TABLE schema_version (version INTEGER PRIMARY KEY)"
            )
            await self.conn.execute("INSERT INTO schema_version VALUES (0)")
            await self.conn.commit()
            self._schema_version = 0
        else:
            # Get current schema version
            cursor = await self.conn.execute("SELECT version FROM schema_version")
            row = await cursor.fetchone()
            self._schema_version = row[0] if row else 0

        # Run migrations
        if self._schema_version < 1:
            await self._migration_001()
            self._schema_version = 1
            await self.conn.execute("UPDATE schema_version SET version = 1")
            await self.conn.commit()

    async def _migration_001(self):
        """Initial database schema setup."""
        await self.conn.executescript("""
            -- Users table
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                messages_left INTEGER NOT NULL DEFAULT 0,
                username TEXT,
                email TEXT,
                avatar_id TEXT
            );

            -- Games table
            CREATE TABLE games (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                owner_id TEXT,
                parent_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                cover_image TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(owner_id) REFERENCES users(id),
                FOREIGN KEY(parent_id) REFERENCES games(id)
            );

            -- Messages table
            CREATE TABLE messages (
                id TEXT PRIMARY KEY,
                game_id TEXT NOT NULL,
                text TEXT NOT NULL,
                role TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                cost REAL,
                status TEXT,
                commit_sha TEXT,
                model TEXT,
                FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE
            );

            -- Transactions table
            CREATE TABLE transactions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                amount INTEGER NOT NULL,
                description TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            -- Play sessions table
            CREATE TABLE play_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                seconds INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(game_id) REFERENCES games(id)
            );
        """)

    async def _import_json_data(self):
        """Import data from the JSON file if it exists."""
        json_path = Path(__file__).parent / "db.json"
        if not json_path.exists():
            return

        with open(json_path, "r") as f:
            data = json.load(f)

        # Begin transaction
        await self.conn.execute("BEGIN TRANSACTION")

        try:
            # Import users
            for user_id, user in data.get("users", {}).items():
                await self.conn.execute(
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

            # Import games
            for game_id, game in data.get("games", {}).items():
                # First insert game without messages
                await self.conn.execute(
                    """
                    INSERT INTO games (id, name, description, owner_id, parent_id, 
                                      created_at, updated_at, cover_image, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        game_id,
                        game.get("name", ""),
                        game.get("description"),
                        game.get("owner_id", ""),
                        game.get("parent_id"),
                        game.get("created_at", datetime.now().isoformat()),
                        game.get("updated_at", datetime.now().isoformat()),
                        game.get("cover_image"),
                        game.get("version", GAME_VERSION),
                    ),
                )

                # Then insert messages
                for message in game.get("messages", []):
                    await self.conn.execute(
                        """
                        INSERT INTO messages (id, game_id, text, role, timestamp, cost, status, commit_sha, model)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        ),
                    )

            # Import transactions
            for tx_id, tx in data.get("transactions", {}).items():
                await self.conn.execute(
                    """
                    INSERT INTO transactions (id, user_id, session_id, status, 
                                              created_at, updated_at, amount, description)
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

            # Import play sessions
            for session in data.get("play_sessions", []):
                await self.conn.execute(
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

            # Commit transaction
            await self.conn.commit()

            # Backup the JSON file
            backup_path = json_path.with_suffix(".json.bak")
            shutil.copy2(json_path, backup_path)

        except Exception as e:
            # Rollback on error
            await self.conn.rollback()
            raise e

    # User operations
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        await self._ensure_connected()
        cursor = await self.conn.execute(
            "SELECT id, created_at, messages_left, username, email, avatar_id FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "created_at": row[1],
            "messages_left": row[2],
            "username": row[3],
            "email": row[4],
            "avatar_id": row[5],
        }

    async def get_users(self) -> Dict[str, User]:
        """Get all users."""
        await self._ensure_connected()
        cursor = await self.conn.execute(
            "SELECT id, created_at, messages_left, username, email, avatar_id FROM users"
        )
        rows = await cursor.fetchall()

        users = {}
        for row in rows:
            users[row[0]] = {
                "id": row[0],
                "created_at": row[1],
                "messages_left": row[2],
                "username": row[3],
                "email": row[4],
                "avatar_id": row[5],
            }

        return users

    async def create_user(self, user: User) -> None:
        """Create a new user."""
        await self._ensure_connected()
        await self.conn.execute(
            """
            INSERT INTO users (id, created_at, messages_left, username, email, avatar_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                user.get("created_at", datetime.now().isoformat()),
                user.get("messages_left", 0),
                user.get("username"),
                user.get("email"),
                user.get("avatar_id"),
            ),
        )
        await self.conn.commit()

    async def update_user(self, user: User) -> None:
        """Update an existing user."""
        await self._ensure_connected()
        await self.conn.execute(
            """
            UPDATE users
            SET messages_left = ?, username = ?, email = ?, avatar_id = ?
            WHERE id = ?
            """,
            (
                user.get("messages_left", 0),
                user.get("username"),
                user.get("email"),
                user.get("avatar_id"),
                user["id"],
            ),
        )
        await self.conn.commit()

    # Game operations
    async def get_game(self, game_id: str) -> Optional[Game]:
        """Get a game by ID, including its messages."""
        await self._ensure_connected()

        # Get game details
        cursor = await self.conn.execute(
            """
            SELECT id, name, description, owner_id, parent_id, created_at, updated_at, cover_image, version
            FROM games WHERE id = ?
            """,
            (game_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        # Get messages for the game
        messages_cursor = await self.conn.execute(
            """
            SELECT id, text, role, timestamp, cost, status, commit_sha, model
            FROM messages WHERE game_id = ? ORDER BY timestamp
            """,
            (game_id,),
        )
        message_rows = await messages_cursor.fetchall()

        messages = []
        for msg_row in message_rows:
            message: Message = {
                "id": msg_row[0],
                "text": msg_row[1],
                "role": cast(Literal["user", "assistant"], msg_row[2]),
                "timestamp": msg_row[3],
            }
            if msg_row[4] is not None:
                message["cost"] = msg_row[4]
            if msg_row[5]:
                message["status"] = cast(
                    Literal["processing", "completed", "error"], msg_row[5]
                )
            if msg_row[6]:
                message["commit_sha"] = msg_row[6]
            if msg_row[7]:
                message["model"] = msg_row[7]
            messages.append(message)

        # Construct game object
        game: Game = {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "owner_id": row[3] or "",
            "parent_id": row[4],
            "created_at": row[5],
            "updated_at": row[6],
            "messages": messages,
            "cover_image": row[7],
            "version": row[8],
        }

        return game

    async def get_game_by_name(self, game_name: str) -> Optional[Game]:
        """Get a game by name, including its messages."""
        await self._ensure_connected()

        # Get game ID
        cursor = await self.conn.execute(
            "SELECT id FROM games WHERE name = ?",
            (game_name,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        return await self.get_game(row[0])

    async def get_games(self) -> Dict[str, Game]:
        """Get all games with their messages."""
        await self._ensure_connected()

        # Get all games
        cursor = await self.conn.execute("SELECT id FROM games")
        rows = await cursor.fetchall()

        # Get each game with its messages
        games = {}
        for row in rows:
            game_id = row[0]
            game = await self.get_game(game_id)
            if game:
                games[game_id] = game

        return games

    async def create_game(self, game: Game) -> None:
        """Create a new game."""
        await self._ensure_connected()

        async with self.conn.cursor() as cursor:
            # First create the game entry
            await cursor.execute(
                """
                INSERT INTO games (id, name, description, owner_id, parent_id, 
                                  created_at, updated_at, cover_image, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game["id"],
                    game["name"],
                    game.get("description"),
                    game.get("owner_id", ""),
                    game.get("parent_id"),
                    game.get("created_at", datetime.now().isoformat()),
                    game.get("updated_at", datetime.now().isoformat()),
                    game.get("cover_image"),
                    game.get("version", GAME_VERSION),
                ),
            )

            # Then add any messages
            for message in game.get("messages", []):
                await cursor.execute(
                    """
                    INSERT INTO messages (id, game_id, text, role, timestamp, cost, status, commit_sha, model)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.get("id", str(uuid4())),
                        game["id"],
                        message.get("text", ""),
                        message.get("role", "user"),
                        message.get("timestamp", datetime.now().isoformat()),
                        message.get("cost", 0),
                        message.get("status"),
                        message.get("commit_sha"),
                        message.get("model"),
                    ),
                )

            await self.conn.commit()

    async def update_game(self, game: Game) -> None:
        """Update an existing game."""
        await self._ensure_connected()

        # Update the game details
        await self.conn.execute(
            """
            UPDATE games
            SET name = ?, description = ?, owner_id = ?, parent_id = ?, 
                updated_at = ?, cover_image = ?, version = ?
            WHERE id = ?
            """,
            (
                game["name"],
                game.get("description"),
                game.get("owner_id", ""),
                game.get("parent_id"),
                game.get("updated_at", datetime.now().isoformat()),
                game.get("cover_image"),
                game.get("version", GAME_VERSION),
                game["id"],
            ),
        )
        await self.conn.commit()

    async def add_message(self, game_id: str, message: Message) -> None:
        """Add a message to a game."""
        await self._ensure_connected()

        await self.conn.execute(
            """
            INSERT INTO messages (id, game_id, text, role, timestamp, cost, status, commit_sha, model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )

        # Update the game's updated_at field
        await self.conn.execute(
            "UPDATE games SET updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), game_id),
        )

        await self.conn.commit()

    async def update_message(
        self, game_id: str, message_id: str, updates: Dict[str, Any]
    ) -> None:
        """Update a message in a game."""
        await self._ensure_connected()

        # Build the update query dynamically based on what fields are provided
        set_clauses = []
        params = []

        if "text" in updates:
            set_clauses.append("text = ?")
            params.append(updates["text"])

        if "status" in updates:
            set_clauses.append("status = ?")
            params.append(updates["status"])

        if "cost" in updates:
            set_clauses.append("cost = ?")
            params.append(updates["cost"])

        if "commit_sha" in updates:
            set_clauses.append("commit_sha = ?")
            params.append(updates["commit_sha"])

        if not set_clauses:
            return  # Nothing to update

        # Add message ID and game ID to params
        params.append(message_id)
        params.append(game_id)

        query = (
            f"UPDATE messages SET {', '.join(set_clauses)} WHERE id = ? AND game_id = ?"
        )

        await self.conn.execute(query, params)

        # Update the game's updated_at field
        await self.conn.execute(
            "UPDATE games SET updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), game_id),
        )

        await self.conn.commit()

    async def delete_game(self, game_id: str) -> None:
        """Delete a game and all its messages."""
        await self._ensure_connected()

        # Messages will be deleted automatically due to ON DELETE CASCADE
        await self.conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
        await self.conn.commit()

    # Transaction operations
    async def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get a transaction by ID."""
        await self._ensure_connected()

        cursor = await self.conn.execute(
            """
            SELECT id, user_id, session_id, status, created_at, updated_at, amount, description
            FROM transactions WHERE id = ?
            """,
            (transaction_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "user_id": row[1],
            "session_id": row[2],
            "status": row[3],
            "created_at": row[4],
            "updated_at": row[5],
            "amount": row[6],
            "description": row[7],
        }

    async def get_transactions(self) -> Dict[str, Transaction]:
        """Get all transactions."""
        await self._ensure_connected()

        cursor = await self.conn.execute(
            """
            SELECT id, user_id, session_id, status, created_at, updated_at, amount, description
            FROM transactions
            """
        )
        rows = await cursor.fetchall()

        transactions = {}
        for row in rows:
            transactions[row[0]] = {
                "id": row[0],
                "user_id": row[1],
                "session_id": row[2],
                "status": row[3],
                "created_at": row[4],
                "updated_at": row[5],
                "amount": row[6],
                "description": row[7],
            }

        return transactions

    async def create_transaction(self, transaction: Transaction) -> None:
        """Create a new transaction."""
        await self._ensure_connected()

        await self.conn.execute(
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
                transaction.get("description", ""),
            ),
        )
        await self.conn.commit()

    async def update_transaction(self, transaction: Transaction) -> None:
        """Update an existing transaction."""
        await self._ensure_connected()

        await self.conn.execute(
            """
            UPDATE transactions
            SET user_id = ?, session_id = ?, status = ?, updated_at = ?, amount = ?, description = ?
            WHERE id = ?
            """,
            (
                transaction["user_id"],
                transaction["session_id"],
                transaction["status"],
                transaction.get("updated_at", datetime.now().isoformat()),
                transaction["amount"],
                transaction.get("description", ""),
                transaction["id"],
            ),
        )
        await self.conn.commit()

    # Play session operations
    async def get_play_sessions(self) -> List[PlaySession]:
        """Get all play sessions."""
        await self._ensure_connected()

        cursor = await self.conn.execute(
            "SELECT id, user_id, game_id, created_at, seconds FROM play_sessions"
        )
        rows = await cursor.fetchall()

        sessions = []
        for row in rows:
            sessions.append(
                {
                    "id": row[0],
                    "user_id": row[1],
                    "game_id": row[2],
                    "created_at": row[3],
                    "seconds": row[4],
                }
            )

        return sessions

    async def add_play_session(self, session: PlaySession) -> None:
        """Add a new play session."""
        await self._ensure_connected()

        await self.conn.execute(
            """
            INSERT INTO play_sessions (id, user_id, game_id, created_at, seconds)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session.get("id", str(uuid4())),
                session["user_id"],
                session["game_id"],
                session.get("created_at", datetime.now().isoformat()),
                session["seconds"],
            ),
        )
        await self.conn.commit()

    # Utility methods
    async def _ensure_connected(self):
        """Ensure we have a database connection."""
        if self.conn is None:
            await self.initialize()

    # Legacy API compatibility methods
    async def get(self) -> Dict[str, Any]:
        """
        Get the entire database as a dict for compatibility with the old API.
        This assembles a structure matching the original JSON format.
        """
        await self._ensure_connected()

        result = {
            "users": {},
            "games": {},
            "transactions": {},
            "play_sessions": [],
        }

        # Get users
        result["users"] = await self.get_users()

        # Get games
        result["games"] = await self.get_games()

        # Get transactions
        result["transactions"] = await self.get_transactions()

        # Get play sessions
        result["play_sessions"] = await self.get_play_sessions()

        return result

    async def set(self, data: Dict[str, Any]) -> None:
        """
        Set the entire database from a dict for compatibility with the old API.
        This is inefficient and should be replaced with specific update methods.
        """
        await self._ensure_connected()

        # Begin transaction
        await self.conn.execute("BEGIN TRANSACTION")

        try:
            # Process users
            if "users" in data:
                current_users = await self.get_users()

                for user_id, user in data["users"].items():
                    if user_id in current_users:
                        # Update existing user
                        await self.update_user(user)
                    else:
                        # Create new user
                        await self.create_user(user)

            # Process games
            if "games" in data:
                current_games = await self.get_games()

                for game_id, game in data["games"].items():
                    if game_id in current_games:
                        # Handle messages separately
                        old_messages = {
                            m["id"]: m for m in current_games[game_id]["messages"]
                        }
                        new_messages = {m["id"]: m for m in game["messages"]}

                        # Messages to add or update
                        for msg_id, msg in new_messages.items():
                            if msg_id not in old_messages:
                                # New message
                                await self.add_message(game_id, msg)
                            elif msg != old_messages[msg_id]:
                                # Changed message - create diff of changes
                                updates = {}
                                if msg.get("text") != old_messages[msg_id].get("text"):
                                    updates["text"] = msg.get("text", "")
                                if msg.get("status") != old_messages[msg_id].get(
                                    "status"
                                ):
                                    updates["status"] = msg.get("status")
                                if msg.get("cost") != old_messages[msg_id].get("cost"):
                                    updates["cost"] = msg.get("cost", 0)
                                if msg.get("commit_sha") != old_messages[msg_id].get(
                                    "commit_sha"
                                ):
                                    updates["commit_sha"] = msg.get("commit_sha")

                                if updates:
                                    await self.update_message(game_id, msg_id, updates)

                        # Update the game (excluding messages which are handled separately)
                        game_without_msgs = dict(game)
                        game_without_msgs.pop("messages", None)

                        # Only update if something changed
                        old_game_without_msgs = dict(current_games[game_id])
                        old_game_without_msgs.pop("messages", None)

                        if game_without_msgs != old_game_without_msgs:
                            await self.update_game(game)
                    else:
                        # Create new game
                        await self.create_game(game)

            # Process transactions
            if "transactions" in data:
                current_transactions = await self.get_transactions()

                for tx_id, tx in data["transactions"].items():
                    if tx_id in current_transactions:
                        # Update existing transaction
                        await self.update_transaction(tx)
                    else:
                        # Create new transaction
                        await self.create_transaction(tx)

            # Process play sessions
            if "play_sessions" in data:
                # Get existing sessions (using IDs as keys)
                cursor = await self.conn.execute("SELECT id FROM play_sessions")
                rows = await cursor.fetchall()
                existing_session_ids = {row[0] for row in rows}

                # Add any new sessions
                for session in data["play_sessions"]:
                    if session.get("id") not in existing_session_ids:
                        await self.add_play_session(session)

            # Commit transaction
            await self.conn.commit()

        except Exception as e:
            # Rollback on error
            await self.conn.rollback()
            raise e


# Initialize the database singleton
db_sqlite = DBSQLite()
