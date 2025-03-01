#!/bin/bash
set -e

echo "Running code quality checks..."

# Backend checks
cd backend

# Check if virtual environment exists and activate it if it does
if [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "Virtual environment not found, running checks directly..."
fi

echo "Running ruff format on backend..."
if command -v ruff &> /dev/null; then
    ruff format .
else
    echo "Warning: ruff not found. Skipping backend formatting."
fi

echo "Running ruff check --fix on backend..."
if command -v ruff &> /dev/null; then
    ruff check --fix .
else
    echo "Warning: ruff not found. Skipping backend linting."
fi

echo "Running pyright on backend..."
if command -v pyright &> /dev/null; then
    pyright .
else
    echo "Warning: pyright not found. Skipping backend type checking."
fi

# Frontend checks
cd ../frontend

echo "Running prettier on frontend..."
npm run format

echo "Running eslint on frontend..."
npm run lint

# Return to root directory
cd ..

echo "All checks completed successfully!"
