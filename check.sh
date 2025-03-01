#!/bin/bash
set -e

echo "Activating virtual environment..."
cd backend
source .venv/bin/activate

echo "Running ruff format on backend..."
ruff format .

echo "Running ruff check --fix on backend..."
ruff check --fix .

echo "Running pyright on backend..."
pyright .

echo "Running prettier on frontend..."
cd ../frontend
npm run format

echo "Running eslint on frontend..."
npm run lint
cd ..

echo "All checks completed successfully!"
