import sqlite3
from typing import List, Callable
import os
from pathlib import Path


class Migration:
    """Represents a single database migration"""

    def __init__(
        self,
        version: int,
        description: str,
        run_migration: Callable[[sqlite3.Connection], None],
    ):
        self.version = version
        self.description = description
        self.run_migration = run_migration


class MigrationManager:
    """Manages database migrations"""

    def __init__(self):
        self.migrations: List[Migration] = []

    def register(self, migration: Migration) -> None:
        """Register a migration with the manager"""
        self.migrations.append(migration)
        # Sort migrations by version to ensure they run in order
        self.migrations.sort(key=lambda m: m.version)

    def _ensure_migration_table_exists(self, conn: sqlite3.Connection) -> None:
        """Create the migrations tracking table if it doesn't exist"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def _get_applied_migrations(self, conn: sqlite3.Connection) -> List[int]:
        """Get list of already applied migration versions"""
        self._ensure_migration_table_exists(conn)
        cursor = conn.execute("SELECT version FROM migrations ORDER BY version")
        return [row[0] for row in cursor.fetchall()]

    def _record_migration(self, conn: sqlite3.Connection, migration: Migration) -> None:
        """Record that a migration has been applied"""
        conn.execute(
            "INSERT INTO migrations (version, description) VALUES (?, ?)",
            (migration.version, migration.description),
        )

    def run_migrations(self, db_path: Path) -> None:
        """Run all pending migrations"""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        with sqlite3.connect(db_path) as conn:
            applied_versions = self._get_applied_migrations(conn)

            for migration in self.migrations:
                if migration.version in applied_versions:
                    print(f"Migration {migration.version} already applied, skipping")
                    continue

                print(
                    f"Applying migration {migration.version}: {migration.description}"
                )
                migration.run_migration(conn)
                self._record_migration(conn, migration)
                conn.commit()
                print(f"Successfully applied migration {migration.version}")


# Create the manager instance
migration_manager = MigrationManager()


# Migration 001: Initial schema setup
def migration_001(conn: sqlite3.Connection) -> None:
    """Create initial database schema"""
    # Create users table
    conn.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            messages_left INTEGER NOT NULL,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            avatar_id TEXT
        )
    """)

    # Create messages table
    conn.execute("""
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            game_id TEXT NOT NULL,
            text TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            timestamp TEXT NOT NULL,
            cost REAL,
            status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'error')),
            commit_sha TEXT,
            model TEXT,
            FOREIGN KEY (game_id) REFERENCES games (id)
        )
    """)

    # Create games table
    conn.execute("""
        CREATE TABLE games (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            owner_id TEXT NOT NULL,
            parent_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            cover_image TEXT,
            version INTEGER NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES users (id),
            FOREIGN KEY (parent_id) REFERENCES games (id)
        )
    """)

    # Create transactions table
    conn.execute("""
        CREATE TABLE transactions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            amount INTEGER NOT NULL,
            description TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Create play_sessions table
    conn.execute("""
        CREATE TABLE play_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            seconds INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (game_id) REFERENCES games (id)
        )
    """)


# Register migrations
migration_manager.register(Migration(1, "Initial schema setup", migration_001))


# Migration 002: Add messages column to messages table
def migration_002(conn: sqlite3.Connection) -> None:
    """Add messages column to messages table"""
    conn.execute("""
        ALTER TABLE messages
        ADD COLUMN messages TEXT
    """)


# Register the new migration
migration_manager.register(
    Migration(2, "Add messages column to messages table", migration_002)
)


# Migration 003: Rename messages_left to credits in users table and multiply values by 10
def migration_003(conn: sqlite3.Connection) -> None:
    """Rename messages_left to credits in users table and multiply values by 10"""
    # SQLite doesn't support ALTER TABLE RENAME COLUMN directly, so we need to:
    # 1. Create a new table with the desired schema
    # 2. Copy data from the old table to the new table
    # 3. Drop the old table
    # 4. Rename the new table to the original name

    # Create new users table with credits instead of messages_left
    conn.execute("""
        CREATE TABLE users_new (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            credits INTEGER NOT NULL,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            avatar_id TEXT
        )
    """)

    # Copy data from old table to new table, multiplying messages_left by 10 to get credits
    conn.execute("""
        INSERT INTO users_new (id, created_at, credits, username, email, avatar_id)
        SELECT id, created_at, messages_left * 10, username, email, avatar_id FROM users
    """)

    # Drop old table
    conn.execute("DROP TABLE users")

    # Rename new table to original name
    conn.execute("ALTER TABLE users_new RENAME TO users")


# Register the migration
migration_manager.register(
    Migration(
        3,
        "Rename messages_left to credits in users table and multiply values by 10",
        migration_003,
    )
)

# Add more migrations as needed:
# migration_manager.register(Migration(4, "Alter table Y", migration_004))


def migrate(db_path: Path):
    """Run all pending migrations"""
    migration_manager.run_migrations(db_path)


# This is the single function you'll import elsewhere
__all__ = ["migrate"]
