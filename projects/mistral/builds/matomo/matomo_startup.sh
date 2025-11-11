#!/bin/bash

# Start the original Matomo entrypoint in the background
echo "Starting Matomo..."
/entrypoint.sh apache2-foreground &

# Wait a bit for Matomo to start up
# sleep 30

# Run the site initialization script
# echo "Running site initialization..."
# /init_sites.sh

# Keep the container running
wait