#!/bin/bash

# Setup backend
cd backend
# Try python3 first, fall back to python if python3 is not available
if command -v python3 &> /dev/null; then
    python3 -m venv .venv
else
    python -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt

# Setup frontend
cd ../frontend
npm install

# Return to root directory
cd ..
