#!/bin/bash

# Setup backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Setup frontend
cd ../frontend
npm install

# Return to root directory
cd ..
