#!/bin/bash
set -e

# Backend checks
cd backend

# Format and fix backend code
if command -v ruff &> /dev/null; then
    ruff format .
    ruff check --fix .
else
    echo "Warning: ruff not found. Skipping backend formatting and linting."
fi

# Type check backend code
if command -v pyright &> /dev/null; then
    pyright .
else
    echo "Warning: pyright not found. Skipping backend type checking."
fi

# Frontend checks
cd ../frontend

# Format frontend code
npm run format

# Lint frontend code
npm run lint

# Return to root directory
cd ..

echo "All checks completed successfully!"
