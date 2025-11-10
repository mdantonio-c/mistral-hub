#!/bin/sh

echo 'Installing Python...'
apt-get update && apt-get install -y python3 python3-requests
echo 'Python installed, starting log import loop...'

while true; do
  for f in /data/logs/nginx*.log; do
    [ -f "$f" ] || continue
    case "$f" in
      *nginx.log) continue ;;  # skip actively-written file
    esac
    if [ ! -e "$f.imported" ]; then
      echo "Starting import of $f at $(date)..."
      echo "File size: $(du -h "$f" | cut -f1)"
      if python3 /var/www/html/misc/log-analytics/import_logs.py \
        --url=http://matomo:80 \
        --idsite=1 \
        --recorders=4 \
        --enable-http-errors \
        --enable-http-redirects \
        --enable-bots \
        --show-progress \
        "$f"; then
        # touch "$f.imported"
        rm "$f"
        echo "SUCCESS: $f imported at $(date)"
      else
        echo "ERROR: Failed to import $f at $(date)"
      fi
    else
      echo "SKIPPING: $f already imported"
    fi
  done
  echo "Waiting 30 seconds before next check..."
  sleep 30
done