#!/bin/bash
set -e

# Setup backend
cd backend
echo "Installing backend dependencies..."

# Check for Python and venv module
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Neither python3 nor python is available. Cannot setup environment."
    exit 1
fi

# Try to create virtual environment
echo "Checking if venv module is available..."
if $PYTHON_CMD -c "import venv" &> /dev/null; then
    echo "Creating virtual environment..."
    if $PYTHON_CMD -m venv .venv; then
        echo "Virtual environment created successfully."
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        echo "Warning: Failed to create virtual environment. Installing dependencies directly."
        $PYTHON_CMD -m pip install -r requirements.txt
    fi
else
    echo "Warning: Python venv module not available."
    echo "On Debian/Ubuntu systems, you may need to install python3-venv package:"
    echo "    apt install python3-venv"
    echo "Installing dependencies directly instead."
    $PYTHON_CMD -m pip install -r requirements.txt
fi

# Setup frontend
cd ../frontend
echo "Installing frontend dependencies..."
npm install

# Fix linting errors in frontend
echo "Fixing linting errors in frontend..."
npm run lint --fix

# Return to root directory
cd ..

echo "Setup completed successfully!"
