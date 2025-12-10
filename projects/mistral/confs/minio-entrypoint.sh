#!/bin/sh
set -e

mkdir -p /root/.minio/certs
echo "Copying certificates for domain: ${DOMAIN}"

cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem /root/.minio/certs/public.crt
cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem /root/.minio/certs/private.key

echo "Certificates copied. Starting MinIO with HTTPS..."
exec minio server --console-address ":9001" /data --address ":9000"