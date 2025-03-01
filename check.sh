#!/bin/bash
set -e

echo "Running ruff format on backend..."
ruff format backend/

echo "Running ruff check --fix on backend..."
ruff check --fix backend/

echo "Running pyright on backend..."
pyright backend/

echo "Running prettier on frontend..."
cd frontend
npm run format

echo "Running eslint on frontend..."
npm run lint
cd ..

echo "All checks completed successfully!"
