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

# CONFIGURE GIT CREDENTIALS
# This ensures git operations don't fail due to missing user identity

cd ..
echo "Configuring git credentials..."
git config --global user.email "granthawkins88@gmail.com"
git config --global user.name "Gamergate"

# START SERVICES

pm2 delete "gamergate*" || true
pm2 start ecosystem.${ENVIRONMENT}.config.js

echo "Setup complete. Environment: ${ENVIRONMENT}"