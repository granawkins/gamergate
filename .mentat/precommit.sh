#!/bin/bash
set -e

# Backend checks
cd backend
source .venv/bin/activate

# Format and fix backend code
ruff format .
ruff check --fix .

# Type check backend code
pyright .

# Frontend checks
cd ../frontend

# Format frontend code
npm run format

# Lint frontend code
npm run lint

# Return to root directory
cd ..

echo "All checks completed successfully!"
