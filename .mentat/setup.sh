#!/bin/bash

# Setup backend
cd backend
# Install Python dependencies directly without virtual environment
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt
else
    echo "Error: Neither pip3 nor pip is available. Cannot install Python dependencies."
    exit 1
fi

# Setup frontend
cd ../frontend
npm install

# Return to root directory
cd ..
