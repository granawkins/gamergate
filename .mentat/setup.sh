#!/bin/bash
set -e

# Setup backend
cd backend
echo "Installing backend dependencies..."

# Try to create and use virtual environment, but fall back to direct install if it fails
if command -v python3 &> /dev/null; then
    # Try to create virtual environment
    if python3 -m venv .venv 2>/dev/null; then
        echo "Virtual environment created successfully."
        source .venv/bin/activate
        pip install -r requirements.txt
    else
        echo "Warning: Failed to create virtual environment. Installing dependencies directly."
        pip3 install -r requirements.txt
    fi
elif command -v python &> /dev/null; then
    # Try to create virtual environment
    if python -m venv .venv 2>/dev/null; then
        echo "Virtual environment created successfully."
        source .venv/bin/activate
        pip install -r requirements.txt
    else
        echo "Warning: Failed to create virtual environment. Installing dependencies directly."
        pip install -r requirements.txt
    fi
else
    echo "Error: Neither python3 nor python is available. Cannot setup environment."
    exit 1
fi

# Setup frontend
cd ../frontend
echo "Installing frontend dependencies..."
npm install

# Return to root directory
cd ..

echo "Setup completed successfully!"
