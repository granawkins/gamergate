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
echo "Checking git credentials..."
# Only set email if it's not already configured
if [ -z "$(git config --global user.email)" ]; then
    echo "Setting git user.email..."
    git config --global user.email "granthawkins88@gmail.com"
fi

# Only set name if it's not already configured
if [ -z "$(git config --global user.name)" ]; then
    echo "Setting git user.name..."
    git config --global user.name "Gamergate"
fi

# START SERVICES

pm2 delete "gamergate*" || true
pm2 start ecosystem.${ENVIRONMENT}.config.js

echo "Setup complete. Environment: ${ENVIRONMENT}"