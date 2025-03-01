#!/bin/bash

# SETUP DEPENDENCIES

cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install

# START SERVICES

cd ..
pm2 delete "gamergate*" || true
pm2 start ecosystem.dev.config.js