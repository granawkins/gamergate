import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
    Any,
    Literal,
    ClassVar,
    Type,
    TypeVar,
    get_type_hints,
)
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import (
    String,
    Integer,
    Float,
    ForeignKey,
    select,
    update,
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Constants
GAME_VERSION = 1
GAMES_PATH = Path(__file__).parent / "games"
ADMIN_EMAIL = "granthawkins88@gmail.com"
DB_PATH = Path(__file__).parent / "gamergate.db"

# Database location
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"


# Base SQLAlchemy model
class Base(DeclarativeBase):
    pass


# Base Pydantic model with common conversion methods
T = TypeVar("T", bound="BasePydanticModel")


class BasePydanticModel(BaseModel):
    """Base Pydantic model with conversion methods for SQLAlchemy models."""

    # Map each Pydantic model to its corresponding SQLAlchemy model
    __sa_model__: ClassVar[Type[Base]]

    @classmethod
    def from_sa(cls: Type[T], sa_obj: Base) -> T:
        """Convert a SQLAlchemy model instance to a Pydantic model."""
        data = {}
        for field_name, field_type in get_type_hints(cls).items():
            if hasattr(sa_obj, field_name):
                data[field_name] = getattr(sa_obj, field_name)
        return cls(**data)

    def to_sa_dict(self) -> Dict[str, Any]:
        """Convert to a dict suitable for SQLAlchemy model creation/update."""
        return self.model_dump(exclude_none=True)


# Pydantic models for type validation and serialization
class User(BasePydanticModel):
    id: str
    created_at: str  # ISO format string of datetime
    messages_left: int
    username: Optional[str] = None
    email: Optional[str] = None
    avatar_id: Optional[str] = None

    __sa_model__: ClassVar[Type[Base]] = None  # Set after SAUser is defined


class Message(BasePydanticModel):
    id: str
    text: str
    role: Literal["user", "assistant"]
    timestamp: str
    game_id: str
    cost: Optional[float] = None
    status: Optional[Literal["processing", "completed", "error"]] = None
    commit_sha: Optional[str] = None
    model: Optional[str] = None

    __sa_model__: ClassVar[Type[Base]] = None  # Set after SAMessage is defined


class Game(BasePydanticModel):
    id: str
    name: str
    owner_id: str = ""
    created_at: str  # ISO format string of datetime
    updated_at: str  # ISO format string of datetime
    description: Optional[str] = None
    parent_id: Optional[str] = None
    cover_image: Optional[str] = None  # Base64 encoded image string
    version: int = GAME_VERSION  # Version number of the game
    messages: List[Message] = Field(default_factory=list)

    __sa_model__: ClassVar[Type[Base]] = None  # Set after SAGame is defined


class Transaction(BasePydanticModel):
    id: str
    user_id: str
    session_id: str
    status: str
    created_at: str
    updated_at: str
    amount: int
    description: str = ""

    __sa_model__: ClassVar[Type[Base]] = None  # Set after SATransaction is defined


class PlaySession(BasePydanticModel):
    id: str
    user_id: str
    game_id: str
    created_at: str
    seconds: int

    __sa_model__: ClassVar[Type[Base]] = None  # Set after SAPlaySession is defined


# SQLAlchemy models for database schema
class SAUser(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    messages_left: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    avatar_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    games = relationship(
        "SAGame", back_populates="owner", foreign_keys="SAGame.owner_id"
    )
    transactions = relationship("SATransaction", back_populates="user")
    play_sessions = relationship("SAPlaySession", back_populates="user")


class SAGame(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    owner_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("users.id"), nullable=True
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("games.id"), nullable=True
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    cover_image: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=GAME_VERSION)

    owner = relationship("SAUser", back_populates="games", foreign_keys=[owner_id])
    parent = relationship("SAGame", remote_side=[id], backref="children")
    messages = relationship(
        "SAMessage", back_populates="game", cascade="all, delete-orphan"
    )
    play_sessions = relationship("SAPlaySession", back_populates="game")


class SAMessage(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    game_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("games.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    commit_sha: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    game = relationship("SAGame", back_populates="messages")


class SATransaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    user = relationship("SAUser", back_populates="transactions")


class SAPlaySession(Base):
    __tablename__ = "play_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    game_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("games.id"), nullable=False
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    user = relationship("SAUser", back_populates="play_sessions")
    game = relationship("SAGame", back_populates="play_sessions")


# Link Pydantic models to their SQLAlchemy counterparts
User.__sa_model__ = SAUser
Game.__sa_model__ = SAGame
Message.__sa_model__ = SAMessage
Transaction.__sa_model__ = SATransaction
PlaySession.__sa_model__ = SAPlaySession


class DBSQLAlchemy:
    def __init__(self):
        self.engine = None
        self.async_session = None
        self.lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initialize database connection and ensure tables exist."""
        if self._initialized:
            return

        async with self.lock:
            if self._initialized:
                return

            # Create database directory if it doesn't exist
            DB_PATH.parent.mkdir(exist_ok=True)

            # Create engine and session maker
            self.engine = create_async_engine(DATABASE_URL)
            self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)

            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Import data if needed
            await self._import_data_if_empty()

            self._initialized = True

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.async_session = None
            self._initialized = False

    async def _import_data_if_empty(self):
        """Import data from JSON if the database is empty."""
        async with self.async_session() as session:
            # Check if users table is empty
            result = await session.execute(select(SAUser).limit(1))
            if result.scalar_one_or_none() is not None:
                return  # Database already has data

            # Import data from JSON if it exists
            json_path = Path(__file__).parent / "db.json"
            if not json_path.exists():
                return

            with open(json_path, "r") as f:
                data = json.load(f)

            # Begin transaction
            async with session.begin():
                # Import users
                for user_id, user_data in data.get("users", {}).items():
                    user = SAUser(
                        id=user_id,
                        created_at=user_data.get(
                            "created_at", datetime.now().isoformat()
                        ),
                        messages_left=user_data.get("messages_left", 0),
                        username=user_data.get("username"),
                        email=user_data.get("email"),
                        avatar_id=user_data.get("avatar_id"),
                    )
                    session.add(user)

                # Import games without messages first
                for game_id, game_data in data.get("games", {}).items():
                    game = SAGame(
                        id=game_id,
                        name=game_data.get("name", ""),
                        description=game_data.get("description"),
                        owner_id=game_data.get("owner_id", ""),
                        parent_id=game_data.get("parent_id"),
                        created_at=game_data.get(
                            "created_at", datetime.now().isoformat()
                        ),
                        updated_at=game_data.get(
                            "updated_at", datetime.now().isoformat()
                        ),
                        cover_image=game_data.get("cover_image"),
                        version=game_data.get("version", GAME_VERSION),
                    )
                    session.add(game)

                # Commit to ensure games exist before adding messages
                await session.commit()

                # Import messages
                for game_id, game_data in data.get("games", {}).items():
                    for message_data in game_data.get("messages", []):
                        message = SAMessage(
                            id=message_data.get("id", str(uuid4())),
                            game_id=game_id,
                            text=message_data.get("text", ""),
                            role=message_data.get("role", "user"),
                            timestamp=message_data.get(
                                "timestamp", datetime.now().isoformat()
                            ),
                            cost=message_data.get("cost"),
                            status=message_data.get("status"),
                            commit_sha=message_data.get("commit_sha"),
                            model=message_data.get("model"),
                        )
                        session.add(message)

                # Import transactions
                for tx_id, tx_data in data.get("transactions", {}).items():
                    transaction = SATransaction(
                        id=tx_id,
                        user_id=tx_data.get("user_id", ""),
                        session_id=tx_data.get("session_id", ""),
                        status=tx_data.get("status", ""),
                        created_at=tx_data.get(
                            "created_at", datetime.now().isoformat()
                        ),
                        updated_at=tx_data.get(
                            "updated_at", datetime.now().isoformat()
                        ),
                        amount=tx_data.get("amount", 0),
                        description=tx_data.get("description", ""),
                    )
                    session.add(transaction)

                # Import play sessions
                for session_data in data.get("play_sessions", []):
                    play_session = SAPlaySession(
                        id=session_data.get("id", str(uuid4())),
                        user_id=session_data.get("user_id", ""),
                        game_id=session_data.get("game_id", ""),
                        created_at=session_data.get(
                            "created_at", datetime.now().isoformat()
                        ),
                        seconds=session_data.get("seconds", 0),
                    )
                    session.add(play_session)

                # Commit all changes
                await session.commit()

            # Backup the JSON file
            backup_path = json_path.with_suffix(".json.bak")
            shutil.copy2(json_path, backup_path)

    async def _ensure_initialized(self):
        """Ensure database is initialized before any operation."""
        if not self._initialized:
            await self.initialize()

    # User operations
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            result = await session.execute(select(SAUser).where(SAUser.id == user_id))
            sa_user = result.scalar_one_or_none()

            if sa_user is None:
                return None

            return User.from_sa(sa_user)

    async def get_users(self) -> Dict[str, User]:
        """Get all users as a dictionary."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            result = await session.execute(select(SAUser))
            sa_users = result.scalars().all()

            return {str(u.id): User.from_sa(u) for u in sa_users}

    async def create_user(self, user: User) -> None:
        """Create a new user."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            sa_user = SAUser(**user.to_sa_dict())
            session.add(sa_user)
            await session.commit()

    async def update_user(self, user: User) -> None:
        """Update an existing user."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            result = await session.execute(select(SAUser).where(SAUser.id == user.id))
            sa_user = result.scalar_one_or_none()

            if sa_user is None:
                return

            # Update fields
            for key, value in user.to_sa_dict().items():
                if hasattr(sa_user, key):
                    setattr(sa_user, key, value)

            await session.commit()

    # Game operations
    async def get_game(self, game_id: str) -> Optional[Game]:
        """Get a game by ID with all its messages."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            # Get game with messages
            result = await session.execute(select(SAGame).where(SAGame.id == game_id))
            sa_game = result.scalar_one_or_none()

            if sa_game is None:
                return None

            # Get messages for the game
            messages_result = await session.execute(
                select(SAMessage)
                .where(SAMessage.game_id == game_id)
                .order_by(SAMessage.timestamp)
            )
            sa_messages = messages_result.scalars().all()

            # Create Game object
            game_dict = {
                "id": sa_game.id,
                "name": sa_game.name,
                "description": sa_game.description,
                "owner_id": sa_game.owner_id or "",
                "parent_id": sa_game.parent_id,
                "created_at": sa_game.created_at,
                "updated_at": sa_game.updated_at,
                "cover_image": sa_game.cover_image,
                "version": sa_game.version,
                "messages": [Message.from_sa(m) for m in sa_messages],
            }

            return Game(**game_dict)

    async def get_game_by_name(self, game_name: str) -> Optional[Game]:
        """Get a game by name with all its messages."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            # Get game ID from name
            result = await session.execute(
                select(SAGame.id).where(SAGame.name == game_name)
            )
            game_id = result.scalar_one_or_none()

            if game_id is None:
                return None

            return await self.get_game(game_id)

    async def get_games(self) -> Dict[str, Game]:
        """Get all games with their messages."""
        await self._ensure_initialized()

        # Get all game IDs
        async with self.async_session() as session:
            result = await session.execute(select(SAGame.id))
            game_ids = result.scalars().all()

        # Get each game with its messages
        games = {}
        for game_id in game_ids:
            game = await self.get_game(game_id)
            if game:
                games[game_id] = game

        return games

    async def create_game(self, game: Game) -> None:
        """Create a new game with its messages."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            async with session.begin():
                # Extract messages to add separately
                messages = game.messages
                game_dict = game.model_dump(exclude={"messages"})

                # Create game
                sa_game = SAGame(**game_dict)
                session.add(sa_game)

                # Add messages if any
                for message in messages:
                    message_dict = message.model_dump()
                    message_dict["game_id"] = game.id
                    sa_message = SAMessage(**message_dict)
                    session.add(sa_message)

    async def update_game(self, game: Game) -> None:
        """Update a game's properties (excluding messages)."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            # Get the game
            result = await session.execute(select(SAGame).where(SAGame.id == game.id))
            sa_game = result.scalar_one_or_none()

            if sa_game is None:
                return

            # Update game properties (excluding messages)
            game_dict = game.model_dump(exclude={"messages"})
            for key, value in game_dict.items():
                if hasattr(sa_game, key):
                    setattr(sa_game, key, value)

            await session.commit()

    async def add_message(self, game_id: str, message: Message) -> None:
        """Add a message to a game."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            # Check if game exists
            result = await session.execute(select(SAGame).where(SAGame.id == game_id))
            if result.scalar_one_or_none() is None:
                return

            # Add message
            message_dict = message.model_dump()
            message_dict["game_id"] = game_id
            sa_message = SAMessage(**message_dict)
            session.add(sa_message)

            # Update game's updated_at timestamp
            await session.execute(
                update(SAGame)
                .where(SAGame.id == game_id)
                .values(updated_at=datetime.now().isoformat())
            )

            await session.commit()

    async def update_message(self, message_id: str, updates: Dict[str, Any]) -> None:
        """Update a message's properties."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            # Get the message
            result = await session.execute(
                select(SAMessage).where(SAMessage.id == message_id)
            )
            sa_message = result.scalar_one_or_none()

            if sa_message is None:
                return

            # Update message properties
            for key, value in updates.items():
                if hasattr(sa_message, key):
                    setattr(sa_message, key, value)

            # Update game's updated_at timestamp
            await session.execute(
                update(SAGame)
                .where(SAGame.id == sa_message.game_id)
                .values(updated_at=datetime.now().isoformat())
            )

            await session.commit()

    async def delete_game(self, game_id: str) -> None:
        """Delete a game and all its messages."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            # Check if game exists
            result = await session.execute(select(SAGame).where(SAGame.id == game_id))
            sa_game = result.scalar_one_or_none()

            if sa_game is None:
                return

            # Delete game (cascade will delete messages)
            await session.delete(sa_game)
            await session.commit()

    # Transaction operations
    async def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """Get a transaction by ID."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            result = await session.execute(
                select(SATransaction).where(SATransaction.id == tx_id)
            )
            sa_tx = result.scalar_one_or_none()

            if sa_tx is None:
                return None

            return Transaction.from_sa(sa_tx)

    async def get_transactions(self) -> Dict[str, Transaction]:
        """Get all transactions."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            result = await session.execute(select(SATransaction))
            sa_txs = result.scalars().all()

            return {tx.id: Transaction.from_sa(tx) for tx in sa_txs}

    async def create_transaction(self, transaction: Transaction) -> None:
        """Create a new transaction."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            sa_tx = SATransaction(**transaction.to_sa_dict())
            session.add(sa_tx)
            await session.commit()

    async def update_transaction(self, transaction: Transaction) -> None:
        """Update an existing transaction."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            result = await session.execute(
                select(SATransaction).where(SATransaction.id == transaction.id)
            )
            sa_tx = result.scalar_one_or_none()

            if sa_tx is None:
                return

            # Update fields
            for key, value in transaction.to_sa_dict().items():
                if hasattr(sa_tx, key):
                    setattr(sa_tx, key, value)

            await session.commit()

    # Play session operations
    async def get_play_sessions(self) -> List[PlaySession]:
        """Get all play sessions."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            result = await session.execute(select(SAPlaySession))
            sa_sessions = result.scalars().all()

            return [PlaySession.from_sa(s) for s in sa_sessions]

    async def add_play_session(self, session_data: PlaySession) -> None:
        """Add a new play session."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            sa_session = SAPlaySession(**session_data.to_sa_dict())
            session.add(sa_session)
            await session.commit()

    # Legacy API compatibility methods
    async def get(self) -> Dict[str, Any]:
        """Get the entire database as a dict for compatibility with the old API."""
        await self._ensure_initialized()

        result = {
            "users": {},
            "games": {},
            "transactions": {},
            "play_sessions": [],
        }

        # Get users
        result["users"] = await self.get_users()

        # Get games with messages
        result["games"] = await self.get_games()

        # Get transactions
        result["transactions"] = await self.get_transactions()

        # Get play sessions
        result["play_sessions"] = await self.get_play_sessions()

        return result

    async def set(self, data: Dict[str, Any]) -> None:
        """Set the entire database from a dict for compatibility with the old API."""
        await self._ensure_initialized()

        # Process users
        if "users" in data:
            current_users = await self.get_users()

            for user_id, user_data in data["users"].items():
                user = User(**user_data)
                if user_id in current_users:
                    await self.update_user(user)
                else:
                    await self.create_user(user)

        # Process games
        if "games" in data:
            current_games = await self.get_games()

            for game_id, game_data in data["games"].items():
                if game_id in current_games:
                    # Need to handle messages separately
                    old_game = current_games[game_id]
                    old_messages = {m.id: m for m in old_game.messages}

                    # Update the game (excluding messages)
                    game_without_msgs = dict(game_data)
                    game_without_msgs.pop("messages", None)
                    await self.update_game(Game(**game_without_msgs))

                    # Process messages
                    for msg_data in game_data.get("messages", []):
                        msg_id = msg_data["id"]
                        if msg_id not in old_messages:
                            # New message
                            await self.add_message(game_id, Message(**msg_data))
                        else:
                            # Compare and update if different
                            old_msg = old_messages[msg_id]
                            if msg_data != old_msg.model_dump():
                                updates = {}
                                for key, value in msg_data.items():
                                    if (
                                        key != "id"
                                        and key != "game_id"
                                        and getattr(old_msg, key, None) != value
                                    ):
                                        updates[key] = value

                                if updates:
                                    await self.update_message(msg_id, updates)
                else:
                    # Create new game with messages
                    await self.create_game(Game(**game_data))

        # Process transactions
        if "transactions" in data:
            current_txs = await self.get_transactions()

            for tx_id, tx_data in data["transactions"].items():
                tx = Transaction(**tx_data)
                if tx_id in current_txs:
                    await self.update_transaction(tx)
                else:
                    await self.create_transaction(tx)

        # Process play sessions
        if "play_sessions" in data:
            # Get existing session IDs
            current_sessions = await self.get_play_sessions()
            existing_ids = {s.id for s in current_sessions}

            # Add new sessions
            for session_data in data["play_sessions"]:
                if session_data.get("id") not in existing_ids:
                    await self.add_play_session(PlaySession(**session_data))


# Initialize the database singleton
db_sqlalchemy = DBSQLAlchemy()
