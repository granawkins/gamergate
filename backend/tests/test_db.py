import asyncio
import pytest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from db import Database
from db.models import User
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


# Async test for Database class methods
@pytest.mark.asyncio
async def test_database_user_methods(temp_db_path):
    # First run migrations to set up the schema
    migrate(temp_db_path)

    # Create a Database instance
    db = Database(db_path=temp_db_path)
    await db.connect()

    try:
        # Initially, the user shouldn't exist
        test_user_id = "test123"
        user = await db.get_user(test_user_id)
        assert user is None

        # Create a user and upsert it
        now = datetime.now(timezone.utc).isoformat()
        new_user = User(
            id=test_user_id,
            created_at=now,
            messages_left=10,
            username="testuser",
            email="test@example.com",
            avatar_id=None,
        )

        await db.upsert_user(new_user)

        # Check if user was saved
        user = await db.get_user(test_user_id)
        assert user is not None
        assert user.id == test_user_id
        assert user.username == "testuser"
        assert user.messages_left == 10

        # Test update functionality
        updated_user = User(
            id=test_user_id,
            created_at=now,
            messages_left=5,  # Changed
            username="updateduser",  # Changed
            email="test@example.com",
            avatar_id="avatar1",  # Changed
        )

        await db.upsert_user(updated_user)

        # Check if user was updated
        user = await db.get_user(test_user_id)
        assert user is not None
        assert user.username == "updateduser"
        assert user.messages_left == 5
        assert user.avatar_id == "avatar1"

    finally:
        # Clean up
        await db.close()


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
            await db.upsert_user(user)
            return user

        # Launch tasks concurrently
        tasks = [create_user(str(i)) for i in range(5)]
        users = await asyncio.gather(*tasks)

        # Verify all users were created
        for user in users:
            retrieved_user = await db.get_user(user.id)
            assert retrieved_user is not None
            assert retrieved_user.id == user.id
            assert retrieved_user.username == user.username

        # Launch multiple updates concurrently
        async def update_messages(user_id: str, new_count: int):
            user = await db.get_user(user_id)
            assert user is not None
            user.messages_left = new_count
            await db.upsert_user(user)

        # Update all users concurrently
        update_tasks = [update_messages(f"user_{i}", i * 5) for i in range(5)]
        await asyncio.gather(*update_tasks)

        # Verify updates
        for i in range(5):
            user = await db.get_user(f"user_{i}")
            assert user is not None
            assert user.messages_left == i * 5

    finally:
        # Clean up
        await db.close()
