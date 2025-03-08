# SQLite Database Migration

This PR transitions the Gamergate application from using a JSON file-based database to a SQLite database using SQLAlchemy and Pydantic, providing a more robust, scalable database solution while maintaining type safety.

## Overview

### Files Added

- **db_sqlalchemy.py**: Core SQLAlchemy implementation with Pydantic models
- **db_new.py**: Compatibility wrapper providing the same interface as the old db.py
- **alembic.ini**: Alembic configuration for migrations
- **migrations/**: Directory containing database migration scripts
- **initialize_db.py**: Script to initialize the database
- **tests/test_db_sqlalchemy.py**: Tests for the new database implementation

### How to Switch to SQLite

1. Install the new requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Initialize the database:
   ```bash
   cd backend
   python initialize_db.py
   ```

3. Update your imports to use the new database module:
   ```python
   from db_new import db, User, Game, Message, Transaction, PlaySession, GAME_VERSION, GAMES_PATH, ADMIN_EMAIL
   ```

### Type-Safe Data Models

The implementation uses Pydantic models for data validation and SQLAlchemy for database access:

```python
class User(BasePydanticModel):
    id: str
    created_at: str
    messages_left: int
    username: Optional[str] = None
    email: Optional[str] = None
    avatar_id: Optional[str] = None
```

### Future Schema Changes

For future schema changes:

1. Modify the SQLAlchemy models in `db_sqlalchemy.py`
2. Generate a migration:
   ```bash
   cd backend
   alembic revision --autogenerate -m "Description of changes"
   ```
3. Apply the migration:
   ```bash
   alembic upgrade head
   ```

See `migrations/README.md` for more details on migrations.

## Benefits

1. **Data Integrity**: SQLite enforces schema constraints and foreign keys
2. **Performance**: SQL databases optimize queries for larger datasets
3. **Scalability**: Easier path to PostgreSQL or other databases in the future
4. **Migrations**: Structured approach to schema changes
5. **Type Safety**: Still fully compatible with your pyright setup

## Compatibility

The migration maintains backward compatibility with your existing codebase:
- Same `db.get()` and `db.set()` methods
- Same data structures returned to your application
- Same type definitions

## Additional Methods

The new implementation adds several new methods that you can start using for more efficient database operations:

```python
await db.get_user(user_id)
await db.get_game(game_id)
await db.get_game_by_name(game_name)
await db.add_message(game_id, message)
```

## Testing

Run the tests with:

```bash
cd backend
pytest tests/test_db_sqlalchemy.py
```
