from pathlib import Path

from db.models import User, Message, Game, Transaction, PlaySession  # noqa: F401
from db.migrations import migrate
from db.database import Database

DB_PATH = Path(__file__).parent / "db.sqlite"

migrate(DB_PATH)

db = Database(DB_PATH)
