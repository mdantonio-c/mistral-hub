#!/bin/bash

# Manual log cleanup script
# Run this script manually or via docker exec to clean up logs immediately

echo "=== Fluentd Log Cleanup - Manual Execution ==="
echo "Running cleanup script..."

/usr/local/bin/log_cleanup.sh

echo "=== Manual cleanup completed ==="
echo ""
echo "To check current log usage:"
echo "  du -sh /var/log/fluentd"
echo ""
echo "To monitor logs continuously:"
echo "  docker exec -it mistral-fluentd-1 /usr/local/bin/manual_cleanup.sh"