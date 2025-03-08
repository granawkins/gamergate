import asyncio
import pytest
import tempfile
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone

from db import Database
from db.models import User, Game, Message, Transaction, PlaySession
from db.migrations import migrate, migration_manager, Migration


# Fixture for temporary database path
@pytest.fixture
def temp_db_path():
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a path for our test database
        db_path = Path(temp_dir) / "test_db.sqlite"
        yield db_path
        # Cleanup will happen automatically after the test


# Fixture for a database instance with migrations applied
@pytest.fixture
async def test_db(temp_db_path):
    # Run migrations on the temporary database
    migrate(temp_db_path)
    
    # Create a Database instance
    db = Database(db_path=temp_db_path)
    await db.connect()
    
    yield db
    
    # Clean up
    await db.close()


# Fixture to generate an ISO formatted timestamp
@pytest.fixture
def timestamp():
    return datetime.now(timezone.utc).isoformat()


# Test migrations
def test_migrations(temp_db_path):
    # Run migrations on the temporary database
    migrate(temp_db_path)

    # Connect to the database and check if migrations were applied
    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.cursor()

        # Check if migrations table exists and has entries
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'"
        )
        assert cursor.fetchone() is not None

        # Check if our initial migration (version 1) was applied
        cursor.execute("SELECT version FROM migrations WHERE version=1")
        assert cursor.fetchone() is not None

        # Check if the tables were created
        tables = ["users", "messages", "games", "transactions", "play_sessions"]
        for table in tables:
            cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
            )
            assert cursor.fetchone() is not None, f"Table {table} was not created"


# Test running migrations twice (idempotence)
def test_migrations_idempotence(temp_db_path):
    # Run migrations twice
    migrate(temp_db_path)
    migrate(temp_db_path)

    # Check migration records (should only have one entry per version)
    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM migrations WHERE version=1")
        count = cursor.fetchone()[0]
        assert count == 1, "Migration was applied more than once"


# Test registering and running a new migration
def test_new_migration(temp_db_path):
    # Create a test migration function
    def migration_test(conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE test_table (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)

    # Register our test migration
    migration_manager.register(Migration(999, "Test migration", migration_test))

    # Run migrations
    migrate(temp_db_path)

    # Check if the test table was created
    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
        )
        assert cursor.fetchone() is not None, "Test migration wasn't applied"


# Test concurrent database access
@pytest.mark.asyncio
async def test_concurrent_access(temp_db_path):
    # First run migrations to set up the schema
    migrate(temp_db_path)

    # Create a Database instance
    db = Database(db_path=temp_db_path)
    await db.connect()

    try:
        now = datetime.now(timezone.utc).isoformat()

        # Create 5 users with 10 messages each
        async def create_user(user_id: str):
            user = User(
                id=f"user_{user_id}",
                created_at=now,
                messages_left=10,
                username=f"user_{user_id}",
                email=f"user_{user_id}@example.com",
                avatar_id=None,
            )
            await db.create_user(user)
            return user

        # Launch tasks concurrently
        tasks = [create_user(str(i)) for i in range(5)]
        users = await asyncio.gather(*tasks)

        # Verify all users were created
        for user in users:
            retrieved_user = await db.get_user_by_id(user.id)
            assert retrieved_user is not None
            assert retrieved_user.id == user.id
            assert retrieved_user.username == user.username

    finally:
        # Clean up
        await db.close()


# User tests
class TestUserMethods:
    @pytest.fixture
    async def test_user(self, test_db, timestamp):
        user_id = f"user_{uuid.uuid4()}"
        user = User(
            id=user_id,
            created_at=timestamp,
            messages_left=10,
            username="testuser",
            email="test@example.com",
            avatar_id=None,
        )
        await test_db.create_user(user)
        return user
    
    @pytest.mark.asyncio
    async def test_create_user(self, test_db, timestamp):
        # Create a user
        user_id = f"user_{uuid.uuid4()}"
        user = User(
            id=user_id,
            created_at=timestamp,
            messages_left=10,
            username="createuser",
            email="create@example.com",
            avatar_id=None,
        )
        await test_db.create_user(user)
        
        # Verify user was created
        retrieved_user = await test_db.get_user_by_id(user_id)
        assert retrieved_user is not None
        assert retrieved_user.id == user_id
        assert retrieved_user.username == "createuser"
        assert retrieved_user.email == "create@example.com"
    
    @pytest.mark.asyncio
    async def test_get_all_users(self, test_db, test_user):
        # Get all users
        users = await test_db.get_all_users()
        
        # Verify our test user is included
        assert any(user.id == test_user.id for user in users)
        assert len(users) > 0
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, test_db, test_user):
        # Get user by email
        user = await test_db.get_user_by_email(test_user.email)
        
        # Verify user is found
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, test_db, test_user):
        # Get user by ID
        user = await test_db.get_user_by_id(test_user.id)
        
        # Verify user is found
        assert user is not None
        assert user.id == test_user.id
        assert user.username == test_user.username
    
    @pytest.mark.asyncio
    async def test_update_user_by_id(self, test_db, test_user):
        # Update user
        await test_db.update_user_by_id(
            test_user.id,
            username="updated_username",
            messages_left=20
        )
        
        # Verify user was updated
        updated_user = await test_db.get_user_by_id(test_user.id)
        assert updated_user is not None
        assert updated_user.username == "updated_username"
        assert updated_user.messages_left == 20
        # Other fields should remain unchanged
        assert updated_user.email == test_user.email


# Game tests
class TestGameMethods:
    @pytest.fixture
    async def test_user(self, test_db, timestamp):
        user_id = f"user_{uuid.uuid4()}"
        user = User(
            id=user_id,
            created_at=timestamp,
            messages_left=10,
            username="gameowner",
            email="gameowner@example.com",
            avatar_id=None,
        )
        await test_db.create_user(user)
        return user
    
    @pytest.fixture
    async def test_game(self, test_db, test_user, timestamp):
        game_id = f"game_{uuid.uuid4()}"
        game = Game(
            id=game_id,
            name="Test Game",
            description="A test game",
            owner_id=test_user.id,
            parent_id=None,
            created_at=timestamp,
            updated_at=timestamp,
            cover_image=None,
            version=1
        )
        await test_db.create_game(game)
        return game
    
    @pytest.mark.asyncio
    async def test_create_game(self, test_db, test_user, timestamp):
        # Create a game
        game_id = f"game_{uuid.uuid4()}"
        game = Game(
            id=game_id,
            name="New Game",
            description="A new test game",
            owner_id=test_user.id,
            parent_id=None,
            created_at=timestamp,
            updated_at=timestamp,
            cover_image=None,
            version=1
        )
        await test_db.create_game(game)
        
        # Verify game was created
        retrieved_game = await test_db.get_game_by_id(game_id)
        assert retrieved_game is not None
        assert retrieved_game.id == game_id
        assert retrieved_game.name == "New Game"
        assert retrieved_game.owner_id == test_user.id
    
    @pytest.mark.asyncio
    async def test_get_all_games(self, test_db, test_game):
        # Get all games
        games = await test_db.get_all_games()
        
        # Verify our test game is included
        assert any(game.id == test_game.id for game in games)
        assert len(games) > 0
    
    @pytest.mark.asyncio
    async def test_get_all_game_data(self, test_db, test_game, test_user):
        # Get all game data
        games_data = await test_db.get_all_game_data()
        
        # Verify our test game is included with additional data
        game_data = next((g for g in games_data if g.id == test_game.id), None)
        assert game_data is not None
        assert game_data.seconds_played == 0  # No play sessions yet
        assert game_data.owner_username == test_user.username
    
    @pytest.mark.asyncio
    async def test_get_game_data_by_id(self, test_db, test_game, test_user):
        # Get game data by ID
        game_data = await test_db.get_game_data_by_id(test_game.id)
        
        # Verify game data is returned
        assert game_data is not None
        assert game_data.id == test_game.id
        assert game_data.seconds_played == 0  # No play sessions yet
        assert game_data.owner_username == test_user.username
    
    @pytest.mark.asyncio
    async def test_get_game_by_id(self, test_db, test_game):
        # Get game by ID
        game = await test_db.get_game_by_id(test_game.id)
        
        # Verify game is returned
        assert game is not None
        assert game.id == test_game.id
        assert game.name == test_game.name
    
    @pytest.mark.asyncio
    async def test_update_game_by_id(self, test_db, test_game):
        # Update game
        new_timestamp = datetime.now(timezone.utc).isoformat()
        await test_db.update_game_by_id(
            test_game.id,
            name="Updated Game",
            description="Updated description",
            updated_at=new_timestamp
        )
        
        # Verify game was updated
        updated_game = await test_db.get_game_by_id(test_game.id)
        assert updated_game is not None
        assert updated_game.name == "Updated Game"
        assert updated_game.description == "Updated description"
        assert updated_game.updated_at == new_timestamp
        # Other fields should remain unchanged
        assert updated_game.owner_id == test_game.owner_id
        assert updated_game.created_at == test_game.created_at
    
    @pytest.mark.asyncio
    async def test_delete_game_by_id(self, test_db, timestamp, test_user):
        # Create a game to delete
        game_id = f"game_to_delete_{uuid.uuid4()}"
        game = Game(
            id=game_id,
            name="Game to Delete",
            description="This game will be deleted",
            owner_id=test_user.id,
            parent_id=None,
            created_at=timestamp,
            updated_at=timestamp,
            cover_image=None,
            version=1
        )
        await test_db.create_game(game)
        
        # Verify game exists
        retrieved_game = await test_db.get_game_by_id(game_id)
        assert retrieved_game is not None
        
        # Delete game
        await test_db.delete_game_by_id(game_id)
        
        # Verify game was deleted
        deleted_game = await test_db.get_game_by_id(game_id)
        assert deleted_game is None
    
    @pytest.mark.asyncio
    async def test_get_game_by_name(self, test_db, test_game):
        # Get game by name
        game = await test_db.get_game_by_name(test_game.name)
        
        # Verify game is returned
        assert game is not None
        assert game.id == test_game.id
        assert game.name == test_game.name
    
    @pytest.mark.asyncio
    async def test_get_games_by_owner_id(self, test_db, test_game):
        # Get games by owner ID
        games = await test_db.get_games_by_owner_id(test_game.owner_id)
        
        # Verify our test game is included
        assert any(game.id == test_game.id for game in games)
        assert len(games) > 0


# Message tests
class TestMessageMethods:
    @pytest.fixture
    async def test_user(self, test_db, timestamp):
        user_id = f"user_{uuid.uuid4()}"
        user = User(
            id=user_id,
            created_at=timestamp,
            messages_left=10,
            username="msguser",
            email="msguser@example.com",
            avatar_id=None,
        )
        await test_db.create_user(user)
        return user
    
    @pytest.fixture
    async def test_game(self, test_db, test_user, timestamp):
        game_id = f"game_{uuid.uuid4()}"
        game = Game(
            id=game_id,
            name="Message Test Game",
            description="Game for testing messages",
            owner_id=test_user.id,
            parent_id=None,
            created_at=timestamp,
            updated_at=timestamp,
            cover_image=None,
            version=1
        )
        await test_db.create_game(game)
        return game
    
    @pytest.fixture
    async def test_message(self, test_db, test_game, timestamp):
        message_id = f"msg_{uuid.uuid4()}"
        message = Message(
            id=message_id,
            game_id=test_game.id,
            text="Test message content",
            role="user",
            timestamp=timestamp,
            cost=None,
            status="completed",
            commit_sha=None,
            model=None
        )
        await test_db.create_message(message)
        return message
    
    @pytest.mark.asyncio
    async def test_create_message(self, test_db, test_game, timestamp):
        # Create a message
        message_id = f"msg_{uuid.uuid4()}"
        message = Message(
            id=message_id,
            game_id=test_game.id,
            text="New message content",
            role="user",
            timestamp=timestamp,
            cost=None,
            status="completed",
            commit_sha=None,
            model=None
        )
        await test_db.create_message(message)
        
        # Verify message was created
        retrieved_message = await test_db.get_message_by_id(message_id)
        assert retrieved_message is not None
        assert retrieved_message.id == message_id
        assert retrieved_message.text == "New message content"
        assert retrieved_message.game_id == test_game.id
    
    @pytest.mark.asyncio
    async def test_get_all_messages(self, test_db, test_message):
        # Get all messages
        messages = await test_db.get_all_messages()
        
        # Verify our test message is included
        assert any(message.id == test_message.id for message in messages)
        assert len(messages) > 0
    
    @pytest.mark.asyncio
    async def test_get_messages_by_game_id(self, test_db, test_message, test_game):
        # Get messages by game ID
        messages = await test_db.get_messages_by_game_id(test_game.id)
        
        # Verify our test message is included
        assert any(message.id == test_message.id for message in messages)
        assert len(messages) > 0
    
    @pytest.mark.asyncio
    async def test_get_message_by_id(self, test_db, test_message):
        # Get message by ID
        message = await test_db.get_message_by_id(test_message.id)
        
        # Verify message is returned
        assert message is not None
        assert message.id == test_message.id
        assert message.text == test_message.text
    
    @pytest.mark.asyncio
    async def test_update_message_by_id(self, test_db, test_message):
        # Update message
        await test_db.update_message_by_id(
            test_message.id,
            text="Updated message content",
            status="error",
            cost=0.05,
            model="claude-3-opus-20240229"
        )
        
        # Verify message was updated
        updated_message = await test_db.get_message_by_id(test_message.id)
        assert updated_message is not None
        assert updated_message.text == "Updated message content"
        assert updated_message.status == "error"
        assert updated_message.cost == 0.05
        assert updated_message.model == "claude-3-opus-20240229"
        # Other fields should remain unchanged
        assert updated_message.game_id == test_message.game_id
        assert updated_message.role == test_message.role
    
    @pytest.mark.asyncio
    async def test_delete_message_by_id(self, test_db, test_game, timestamp):
        # Create a message to delete
        message_id = f"msg_to_delete_{uuid.uuid4()}"
        message = Message(
            id=message_id,
            game_id=test_game.id,
            text="Message to delete",
            role="user",
            timestamp=timestamp,
            cost=None,
            status="completed",
            commit_sha=None,
            model=None
        )
        await test_db.create_message(message)
        
        # Verify message exists
        retrieved_message = await test_db.get_message_by_id(message_id)
        assert retrieved_message is not None
        
        # Delete message
        await test_db.delete_message_by_id(message_id)
        
        # Verify message was deleted
        deleted_message = await test_db.get_message_by_id(message_id)
        assert deleted_message is None


# Transaction tests
class TestTransactionMethods:
    @pytest.fixture
    async def test_user(self, test_db, timestamp):
        user_id = f"user_{uuid.uuid4()}"
        user = User(
            id=user_id,
            created_at=timestamp,
            messages_left=10,
            username="txnuser",
            email="txnuser@example.com",
            avatar_id=None,
        )
        await test_db.create_user(user)
        return user
    
    @pytest.fixture
    async def test_transaction(self, test_db, test_user, timestamp):
        txn_id = f"txn_{uuid.uuid4()}"
        session_id = f"sess_{uuid.uuid4()}"
        transaction = Transaction(
            id=txn_id,
            user_id=test_user.id,
            session_id=session_id,
            status="complete",
            created_at=timestamp,
            updated_at=timestamp,
            amount=50,
            description="Test transaction"
        )
        await test_db.create_transaction(transaction)
        return transaction
    
    @pytest.mark.asyncio
    async def test_create_transaction(self, test_db, test_user, timestamp):
        # Create a transaction
        txn_id = f"txn_{uuid.uuid4()}"
        session_id = f"sess_{uuid.uuid4()}"
        transaction = Transaction(
            id=txn_id,
            user_id=test_user.id,
            session_id=session_id,
            status="pending",
            created_at=timestamp,
            updated_at=timestamp,
            amount=25,
            description="New transaction"
        )
        await test_db.create_transaction(transaction)
        
        # Verify transaction was created
        # Note: We can't directly get a transaction by ID in the current API
        transactions = await test_db.get_all_transactions()
        created_txn = next((t for t in transactions if t.id == txn_id), None)
        assert created_txn is not None
        assert created_txn.id == txn_id
        assert created_txn.user_id == test_user.id
        assert created_txn.amount == 25
    
    @pytest.mark.asyncio
    async def test_get_all_transactions(self, test_db, test_transaction):
        # Get all transactions
        transactions = await test_db.get_all_transactions()
        
        # Verify our test transaction is included
        assert any(txn.id == test_transaction.id for txn in transactions)
        assert len(transactions) > 0
    
    @pytest.mark.asyncio
    async def test_get_transaction_by_session_id(self, test_db, test_transaction):
        # Get transaction by session ID
        transaction = await test_db.get_transaction_by_session_id(test_transaction.session_id)
        
        # Verify transaction is returned
        assert transaction is not None
        assert transaction.id == test_transaction.id
        assert transaction.session_id == test_transaction.session_id
    
    @pytest.mark.asyncio
    async def test_update_transaction_by_id(self, test_db, test_transaction):
        # Update transaction
        new_timestamp = datetime.now(timezone.utc).isoformat()
        await test_db.update_transaction_by_id(
            test_transaction.id,
            status="complete",
            updated_at=new_timestamp,
            description="Updated transaction"
        )
        
        # Verify transaction was updated
        transactions = await test_db.get_all_transactions()
        updated_txn = next((t for t in transactions if t.id == test_transaction.id), None)
        assert updated_txn is not None
        assert updated_txn.status == "complete"
        assert updated_txn.updated_at == new_timestamp
        assert updated_txn.description == "Updated transaction"
        # Other fields should remain unchanged
        assert updated_txn.user_id == test_transaction.user_id
        assert updated_txn.amount == test_transaction.amount


# PlaySession tests
class TestPlaySessionMethods:
    @pytest.fixture
    async def test_user(self, test_db, timestamp):
        user_id = f"user_{uuid.uuid4()}"
        user = User(
            id=user_id,
            created_at=timestamp,
            messages_left=10,
            username="playuser",
            email="playuser@example.com",
            avatar_id=None,
        )
        await test_db.create_user(user)
        return user
    
    @pytest.fixture
    async def test_game(self, test_db, test_user, timestamp):
        game_id = f"game_{uuid.uuid4()}"
        game = Game(
            id=game_id,
            name="Play Session Test Game",
            description="Game for testing play sessions",
            owner_id=test_user.id,
            parent_id=None,
            created_at=timestamp,
            updated_at=timestamp,
            cover_image=None,
            version=1
        )
        await test_db.create_game(game)
        return game
    
    @pytest.mark.asyncio
    async def test_create_play_session(self, test_db, test_user, test_game, timestamp):
        # Create a play session
        session_id = f"play_{uuid.uuid4()}"
        play_session = PlaySession(
            id=session_id,
            user_id=test_user.id,
            game_id=test_game.id,
            created_at=timestamp,
            seconds=120
        )
        await test_db.create_play_session(play_session)
        
        # Verify play session was created by checking game data
        game_data = await test_db.get_game_data_by_id(test_game.id)
        assert game_data is not None
        assert game_data.seconds_played == 120
