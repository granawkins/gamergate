# Database Migrations with Alembic

This directory contains database migrations for Gamergate using Alembic and SQLAlchemy.

## Setup

Alembic is already set up for this project. The main configuration is in `alembic.ini` and the migration scripts
are stored in the `versions` directory.

## Creating a New Migration

When you need to make schema changes:

1. Make changes to the SQLAlchemy models in `db_sqlalchemy.py`
2. Generate a new migration script:

```bash
cd backend
alembic revision --autogenerate -m "Description of your changes"
```

3. Review the generated migration script in `migrations/versions/`
4. Apply the migration:

```bash
alembic upgrade head
```

## Migration Commands

* `alembic current` - Show current revision
* `alembic history` - Show migration history
* `alembic upgrade head` - Apply all migrations
* `alembic downgrade -1` - Rollback one migration
* `alembic downgrade base` - Rollback all migrations

## Manual Migrations

If you need to make complex changes that can't be auto-detected:

1. Create a new revision:

```bash
alembic revision -m "Complex changes description"
```

2. Edit the generated file to implement your changes in the `upgrade()` and `downgrade()` functions
3. Apply the migration with `alembic upgrade head`

## Initial Migration

The initial migration creates the database schema from scratch. If you're starting with a new database, simply run:

```bash
alembic upgrade head
```

This will create all tables and relationships needed for the application.
