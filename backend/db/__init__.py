from pathlib import Path

from db.models import User, Message, Game, Transaction, PlaySession  # noqa: F401
from db.migrations import migrate
from db.database import Database

DB_PATH = Path(__file__).parent / "db.sqlite"
GAME_VERSION = 1
GAMES_PATH = Path(__file__).parent / "games"
ADMIN_EMAIL = "granthawkins88@gmail.com"

migrate(DB_PATH)

db = Database(DB_PATH)

# TODO: Add initialize games and users
