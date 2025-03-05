#!/bin/bash

ENVIRONMENT=dev
if [ "$1" == "--prod" ]; then
    ENVIRONMENT=prod
fi

# SETUP DEPENDENCIES

cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
if [ "$ENVIRONMENT" != "dev" ]; then
    npm run build
fi

# START SERVICES

cd ..
pm2 delete "gamergate*" || true
pm2 start ecosystem.${ENVIRONMENT}.config.js

echo "Setup complete. Environment: ${ENVIRONMENT}"