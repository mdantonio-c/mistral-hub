#!/bin/bash

# Alternative entrypoint using background daemon instead of cron

# Log the startup
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Fluentd with log cleanup daemon"

# Ensure log directories exist with proper permissions
mkdir -p /var/log/fluentd /var/log/fluentd/buffer

# Start log cleanup daemon in background
/usr/local/bin/log_cleanup.sh --daemon &

# Start fluentd (use the correct path from the base image)
exec fluentd -c /fluentd/etc/fluent.conf -v