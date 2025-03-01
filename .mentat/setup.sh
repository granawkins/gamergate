#!/bin/bash

# Run the existing setup.sh script but skip the service startup part
# Extract the setup portion from the original script

# Setup backend
cd backend
if command -v python3 &> /dev/null; then
    python3 -m venv .venv || {
        echo "Warning: Failed to create virtual environment. Installing dependencies directly."
        pip3 install -r requirements.txt
    }
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        pip install -r requirements.txt
    fi
elif command -v python &> /dev/null; then
    python -m venv .venv || {
        echo "Warning: Failed to create virtual environment. Installing dependencies directly."
        pip install -r requirements.txt
    }
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        pip install -r requirements.txt
    fi
else
    echo "Error: Neither python3 nor python is available. Cannot setup environment."
    exit 1
fi

# Setup frontend
cd ../frontend
npm install

# Return to root directory
cd ..

echo "Setup completed successfully!"
