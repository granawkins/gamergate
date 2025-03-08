"""
One-time migration script to transfer data from the old JSON database to the new SQLite database.
This script will:
1. Read data from the old db.json file
2. Convert it to the new SQLite format
3. Insert it into the SQLite database

Run this script once after setting up the new database schema.
"""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

# Import the new database module
from db import db, DB_PATH
from db.models import User, Game, Message, Transaction, PlaySession

# Path to the old database file
OLD_DB_PATH = Path(__file__).parent / "db.json"


async def migrate_data():
    """Migrate data from the old JSON database to the new SQLite database"""
    # Check if old database exists
    if not OLD_DB_PATH.exists():
        print(f"Old database file not found at {OLD_DB_PATH}")
        return

    # Check if new database already has data
    await db.connect()
    users = await db.get_all_users()
    if len(users) > 0:
        print("SQLite database already has data. Are you sure you want to continue?")
        response = input("Type 'yes' to continue: ")
        if response.lower() != "yes":
            print("Migration aborted.")
            await db.close()
            return

    # Load the old database
    print(f"Reading old database from {OLD_DB_PATH}")
    with open(OLD_DB_PATH, "r") as f:
        old_db = json.load(f)

    # Migrate users
    print(f"Migrating {len(old_db.get('users', {}))} users...")
    for user_id, user_data in old_db.get("users", {}).items():
        user = User(
            id=user_data["id"],
            created_at=user_data["created_at"],
            messages_left=user_data.get("messages_left", 0),
            username=user_data.get("username"),
            email=user_data.get("email"),
            avatar_id=user_data.get("avatar_id"),
        )
        try:
            await db.create_user(user)
            print(f"Migrated user: {user.id} ({user.username or 'unnamed'})")
        except Exception as e:
            print(f"Error migrating user {user.id}: {str(e)}")

    # Migrate games and their messages
    print(f"Migrating {len(old_db.get('games', {}))} games...")
    for game_id, game_data in old_db.get("games", {}).items():
        # Create the game first
        game = Game(
            id=game_data["id"],
            name=game_data["name"],
            description=game_data.get("description", ""),
            owner_id=game_data["owner_id"],
            parent_id=game_data.get("parent_id"),
            created_at=game_data["created_at"],
            updated_at=game_data["updated_at"],
            cover_image=game_data.get("cover_image", ""),
            version=game_data.get("version", 1),
        )
        try:
            await db.create_game(game)
            print(f"Migrated game: {game.id} ({game.name})")

            # Then migrate all messages for this game
            message_count = 0
            for msg_data in game_data.get("messages", []):
                message = Message(
                    id=msg_data["id"],
                    game_id=game.id,
                    text=msg_data.get("text", ""),
                    role=msg_data["role"],
                    timestamp=msg_data["timestamp"],
                    cost=msg_data.get("cost"),
                    status=msg_data.get("status", "completed"),
                    commit_sha=msg_data.get("commit_sha"),
                    model=msg_data.get("model"),
                )
                try:
                    await db.create_message(message)
                    message_count += 1
                except Exception as e:
                    print(f"Error migrating message {message.id}: {str(e)}")

            print(f"  Migrated {message_count} messages for game {game.id}")
        except Exception as e:
            print(f"Error migrating game {game.id}: {str(e)}")

    # Migrate transactions
    print(f"Migrating {len(old_db.get('transactions', {}))} transactions...")
    for txn_id, txn_data in old_db.get("transactions", {}).items():
        transaction = Transaction(
            id=txn_data["id"],
            user_id=txn_data["user_id"],
            session_id=txn_data.get("session_id", ""),
            status=txn_data.get("status", "complete"),
            created_at=txn_data["created_at"],
            updated_at=txn_data["updated_at"],
            amount=txn_data.get("amount", 0),
            description=txn_data.get("description", ""),
        )
        try:
            await db.create_transaction(transaction)
            print(f"Migrated transaction: {transaction.id}")
        except Exception as e:
            print(f"Error migrating transaction {transaction.id}: {str(e)}")

    # Migrate play sessions
    print(f"Migrating {len(old_db.get('play_sessions', []))} play sessions...")
    for session_data in old_db.get("play_sessions", []):
        play_session = PlaySession(
            id=session_data.get("id", str(uuid4())),  # Generate ID if missing
            user_id=session_data["user_id"],
            game_id=session_data["game_id"],
            created_at=session_data["created_at"],
            seconds=session_data["seconds"],
        )
        try:
            await db.create_play_session(play_session)
            print(f"Migrated play session: {play_session.id}")
        except Exception as e:
            print(f"Error migrating play session {play_session.id}: {str(e)}")

    print("Migration complete!")
    print(f"Data has been migrated to {DB_PATH}")
    await db.close()


if __name__ == "__main__":
    # Run the migration
    asyncio.run(migrate_data())
