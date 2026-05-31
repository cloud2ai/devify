#!/bin/bash

# Script to generate DKIM keys for Haraka
# Domain: aimychats.com
# Selector: default

echo "==================================="
echo "Generating DKIM keys for aimychats.com"
echo "==================================="

# Create directory for DKIM keys if it doesn't exist
mkdir -p /etc/haraka/dkim

# Install opendkim-tools if not present
if ! command -v opendkim-genkey &> /dev/null; then
    echo "Installing opendkim-tools..."
    apt-get update && apt-get install -y opendkim-tools
fi

# Generate DKIM key pair
echo "Generating DKIM key pair..."
opendkim-genkey -D /etc/haraka/dkim -d aimychats.com -s default

# Set correct permissions
chmod 600 /etc/haraka/dkim/default.private
chmod 644 /etc/haraka/dkim/default.txt

echo ""
echo "==================================="
echo "DKIM Keys Generated Successfully!"
echo "==================================="
echo ""
echo "Private key location: /etc/haraka/dkim/default.private"
echo "Public key (for DNS): /etc/haraka/dkim/default.txt"
echo ""
echo "==================================="
echo "DNS Record Configuration:"
echo "==================================="
echo ""
echo "Record Type: TXT"
echo "Host: default._domainkey"
echo "Value: (see below)"
echo ""
cat /etc/haraka/dkim/default.txt
echo ""
echo "==================================="
echo "Next Steps:"
echo "1. Copy the public key value above"
echo "2. Add TXT record to DNS: default._domainkey.aimychats.com"
echo "3. Configure Haraka to use the private key"
echo "==================================="
