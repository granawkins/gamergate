#!/bin/bash

# Reset script for gamergate application
# This script:
# 1. Stops all PM2 processes
# 2. Deletes UUID folders in backend/games
# 3. Deletes the database file if it exists
# 4. Calls setup.sh to reinitialize the application

echo "Starting reset process..."

# 1. Stop all PM2 processes
echo "Stopping all PM2 processes..."
pm2 delete all || echo "No PM2 processes to delete"

# 2. Delete UUID folders in backend/games
echo "Deleting game folders..."
for dir in backend/games/*/; do
  # Skip the driver directory
  if [ "$(basename "$dir")" != "driver" ]; then
    # Check if directory name matches UUID pattern (8-4-4-4-12 hexadecimal characters)
    if [[ $(basename "$dir") =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
      echo "Removing $dir"
      rm -rf "$dir"
    fi
  fi
done

# 3. Delete the database file if it exists
echo "Deleting database file..."
if [ -f backend/db.json ]; then
  rm backend/db.json
  echo "Database file deleted"
else
  echo "No database file found"
fi

# 4. Call setup.sh to reinitialize the application
echo "Running setup script..."
chmod +x ./setup.sh
./setup.sh

echo "Reset complete!"
