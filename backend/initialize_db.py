#!/usr/bin/env python
"""
Database initialization script for Gamergate.

This script initializes the SQLite database by:
1. Creating the database if it doesn't exist
2. Running any pending Alembic migrations
3. Importing data from the old JSON database if needed

Usage:
    python initialize_db.py
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path

# Make sure we're in the backend directory
os.chdir(Path(__file__).parent)

# Run Alembic migrations
print("Running database migrations...")
try:
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    print("Migrations completed successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error running migrations: {e}")
    sys.exit(1)

# Initialize the database with data from the JSON file
print("Initializing database with data...")


async def init_db():
    # Import here to avoid circular imports
    from db_sqlalchemy import db_sqlalchemy

    try:
        await db_sqlalchemy.initialize()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)
    finally:
        # Close the database connection
        await db_sqlalchemy.close()


if __name__ == "__main__":
    asyncio.run(init_db())
    print("Database setup complete!")
