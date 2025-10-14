#!/bin/bash
# Haraka SSL/TLS Certificate Management Script
# Manages Let's Encrypt certificates for Haraka mail server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CERT_DIR="$PROJECT_ROOT/data/certs/haraka"
LETSENCRYPT_LIVE="/etc/letsencrypt/live"

DOMAIN="${HARAKA_DOMAIN:-mail.example.com}"
EMAIL="${HARAKA_CERT_EMAIL:-admin@example.com}"

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_usage() {
    echo "Usage: $0 {apply|renew|status|install-cron|help} [options]"
    echo ""
    echo "Commands:"
    echo "  apply          - Apply for a new Let's Encrypt certificate"
    echo "  renew          - Renew existing certificate"
    echo "  status         - Check certificate status and expiration"
    echo "  install-cron   - Install automatic renewal cron job"
    echo "  help           - Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  HARAKA_DOMAIN       - Domain for certificate (default: mail.example.com)"
    echo "  HARAKA_CERT_EMAIL   - Email for Let's Encrypt (default: admin@example.com)"
    echo ""
    echo "Examples:"
    echo "  HARAKA_DOMAIN=mail.devify.com HARAKA_CERT_EMAIL=admin@devify.com $0 apply"
    echo "  $0 renew"
    echo "  $0 status"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
        exit 1
    fi
}

check_certbot() {
    if ! command -v certbot &> /dev/null; then
        echo -e "${YELLOW}certbot not found. Installing...${NC}"
        apt-get update
        apt-get install -y certbot
    fi
}

apply_certificate() {
    check_root
    check_certbot
    
    echo -e "${BOLD}Applying for SSL certificate for ${DOMAIN}...${NC}"
    echo -e "${YELLOW}Email: ${EMAIL}${NC}"
    echo ""
    
    read -p "Is this correct? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 1
    fi
    
    echo -e "${GREEN}Starting certificate application...${NC}"
    
    certbot certonly --standalone \
        -d "$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --non-interactive \
        --preferred-challenges http
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Certificate obtained successfully!${NC}"
        copy_certificates
        restart_haraka
    else
        echo -e "${RED}Failed to obtain certificate${NC}"
        exit 1
    fi
}

copy_certificates() {
    echo -e "${GREEN}Copying certificates to Haraka directory...${NC}"
    
    if [ ! -d "$LETSENCRYPT_LIVE/$DOMAIN" ]; then
        echo -e "${RED}Error: Certificate directory not found${NC}"
        exit 1
    fi
    
    mkdir -p "$CERT_DIR"
    
    cp "$LETSENCRYPT_LIVE/$DOMAIN/fullchain.pem" "$CERT_DIR/cert.pem"
    cp "$LETSENCRYPT_LIVE/$DOMAIN/privkey.pem" "$CERT_DIR/key.pem"
    
    chmod 644 "$CERT_DIR/cert.pem"
    chmod 600 "$CERT_DIR/key.pem"
    
    echo -e "${GREEN}Certificates copied successfully${NC}"
    echo "  - $CERT_DIR/cert.pem"
    echo "  - $CERT_DIR/key.pem"
}

renew_certificate() {
    check_root
    check_certbot
    
    echo -e "${BOLD}Renewing SSL certificate...${NC}"
    
    certbot renew --quiet
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Certificate renewed successfully${NC}"
        copy_certificates
        restart_haraka
    else
        echo -e "${YELLOW}No renewal needed or renewal failed${NC}"
    fi
}

restart_haraka() {
    echo -e "${GREEN}Restarting Haraka container...${NC}"
    
    cd "$PROJECT_ROOT"
    
    if [ -f "docker-compose.yml" ]; then
        docker-compose restart haraka
        echo -e "${GREEN}Haraka restarted successfully${NC}"
    else
        echo -e "${YELLOW}Warning: docker-compose.yml not found, skipping restart${NC}"
    fi
}

check_status() {
    echo -e "${BOLD}Certificate Status${NC}"
    echo "================================"
    
    if [ -f "$CERT_DIR/cert.pem" ]; then
        echo -e "${GREEN}Certificate found:${NC} $CERT_DIR/cert.pem"
        
        EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_DIR/cert.pem" | cut -d= -f2)
        EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
        NOW_EPOCH=$(date +%s)
        DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))
        
        echo -e "${BOLD}Expires:${NC} $EXPIRY"
        
        if [ $DAYS_LEFT -lt 30 ]; then
            echo -e "${RED}Days remaining: $DAYS_LEFT${NC} (renewal recommended)"
        else
            echo -e "${GREEN}Days remaining: $DAYS_LEFT${NC}"
        fi
        
        echo ""
        echo -e "${BOLD}Certificate details:${NC}"
        openssl x509 -in "$CERT_DIR/cert.pem" -noout -subject -issuer
    else
        echo -e "${RED}No certificate found${NC}"
        echo "Run: sudo $0 apply"
    fi
    
    echo ""
    echo -e "${BOLD}Let's Encrypt certificates:${NC}"
    if [ -d "$LETSENCRYPT_LIVE" ]; then
        ls -la "$LETSENCRYPT_LIVE/" | grep -v "^total" | grep -v "^d.*\.$"
    else
        echo "No Let's Encrypt certificates found"
    fi
}

install_cron() {
    check_root
    
    CRON_SCRIPT="$SCRIPT_DIR/manage-haraka-certs.sh"
    CRON_JOB="0 2 1 * * $CRON_SCRIPT renew >> /var/log/haraka-cert-renewal.log 2>&1"
    
    echo -e "${BOLD}Installing automatic renewal cron job...${NC}"
    
    (crontab -l 2>/dev/null | grep -v "$CRON_SCRIPT"; echo "$CRON_JOB") | crontab -
    
    echo -e "${GREEN}Cron job installed successfully${NC}"
    echo "Schedule: Every 1st of month at 2:00 AM"
    echo "Log file: /var/log/haraka-cert-renewal.log"
    echo ""
    echo "Current crontab:"
    crontab -l | grep haraka
}

case "$1" in
    apply)
        apply_certificate
        ;;
    renew)
        renew_certificate
        ;;
    status)
        check_status
        ;;
    install-cron)
        install_cron
        ;;
    help|--help|-h)
        print_usage
        ;;
    *)
        echo -e "${RED}Error: Invalid command${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac
