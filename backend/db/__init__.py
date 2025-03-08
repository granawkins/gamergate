import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from db.models import User, Message, Game, Transaction, PlaySession  # noqa: F401
from db.migrations import migrate
from db.database import Database

DB_PATH = Path(__file__).parent / "db.sqlite"
GAME_VERSION = 1
GAMES_PATH = Path(__file__).parent.parent / "games"
ADMIN_EMAIL = "granthawkins88@gmail.com"

# Make sure games directory exists
GAMES_PATH.mkdir(exist_ok=True)

# Run migrations to set up the database schema
migrate(DB_PATH)

# Create database instance
db = Database(DB_PATH)


async def initialize_admin_and_templates():
    """
    Initialize the admin user and template games if they don't exist.
    This is run when the module is first imported.
    """

    # Check if admin user exists, create if not
    admin_user = await db.get_user_by_email(ADMIN_EMAIL)
    if admin_user is None:
        admin_id = str(uuid4())
        admin_user = User(
            id=admin_id,
            username="admin",
            email=ADMIN_EMAIL,
            created_at=datetime.now().isoformat(),
            avatar_id=None,
            messages_left=10,
        )
        await db.create_user(admin_user)

    # Initialize template games from games directory
    for dir in GAMES_PATH.iterdir():
        if not dir.is_dir() or dir.name.startswith("."):
            continue

        # Check if this template already exists
        existing_game = await db.get_game_by_name(dir.name)
        if existing_game is None:
            # Create new template game
            game_id = str(uuid4())
            now = datetime.now().isoformat()
            template_game = Game(
                id=game_id,
                name=dir.name,
                description="",
                owner_id="",  # Empty owner_id means it's a template
                parent_id=None,
                created_at=now,
                updated_at=now,
                cover_image="",
                version=GAME_VERSION,
            )
            await db.create_game(template_game)

            # Create a new directory with the game_id and copy the contents
            game_dir = GAMES_PATH / game_id
            if not game_dir.exists():
                shutil.copytree(dir, game_dir)

                # Initialize a git repo for the game
                subprocess.run(["git", "init"], cwd=game_dir)
                subprocess.run(["git", "add", "."], cwd=game_dir)
                subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=game_dir)
