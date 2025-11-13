#!/bin/bash
# Generate self-signed SSL certificate for development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERT_DIR="$PROJECT_ROOT/docker/nginx/certs"

# Default values
DOMAIN="${1:-aimychats.com}"
DAYS="${2:-365}"

echo "==================================================================="
echo "Generating self-signed SSL certificate for: $DOMAIN"
echo "Valid for: $DAYS days"
echo "Output directory: $CERT_DIR"
echo "==================================================================="

# Create certs directory if not exists
mkdir -p "$CERT_DIR"

# Generate self-signed certificate
openssl req -x509 -nodes -days "$DAYS" -newkey rsa:2048 \
  -keyout "$CERT_DIR/nginx-selfsigned.key" \
  -out "$CERT_DIR/nginx-selfsigned.crt" \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=Devify/CN=$DOMAIN"

# Set proper permissions
chmod 600 "$CERT_DIR/nginx-selfsigned.key"
chmod 644 "$CERT_DIR/nginx-selfsigned.crt"

echo ""
echo "==================================================================="
echo "✅ Certificate generated successfully!"
echo ""
echo "Certificate: $CERT_DIR/nginx-selfsigned.crt"
echo "Private Key: $CERT_DIR/nginx-selfsigned.key"
echo ""
echo "⚠️  This is a SELF-SIGNED certificate for DEVELOPMENT only."
echo "   For production, use certificates from Let's Encrypt or a trusted CA."
echo ""
echo "Certificate details:"
openssl x509 -in "$CERT_DIR/nginx-selfsigned.crt" -noout -subject -dates
echo "==================================================================="
