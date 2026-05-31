# Haraka Email Server Configuration for Devify

This directory contains Haraka mail server configuration files for the Devify
project. Haraka receives inbound SMTP mail, saves raw email files to the shared
mail directory, and Devify workers process those files into the normal email
workflow.

## 📁 Directory Structure

```
docker/haraka/
├── config/
│   ├── plugins.dev       # Development plugin configuration
│   ├── plugins.prod      # Production plugin configuration
│   ├── redis.ini         # Redis connection configuration
│   ├── host_list.dev     # Development domains
│   ├── host_list.prod    # Production domains
│   └── tls.ini           # TLS/SSL configuration
├── plugins/
│   └── raw_email_saver.js    # Custom email storage plugin
└── README.md             # This documentation
```

## ⚙️ Configuration Files

### `config/tls.ini`
TLS/SSL encryption configuration:

**Production Environment:**
- `enableTLS=true` - Enable TLS and STARTTLS support
- Certificate path: `/etc/haraka/certs/cert.pem`
- Private key path: `/etc/haraka/certs/key.pem`
- STARTTLS available on port 25 (optional encryption)

**Development Environment:**
- `enableTLS=false` - TLS disabled for simplified testing
- No certificates required

### `config/smtp.ini`
SMTP server configuration:
- Port 25 (standard SMTP) - Used for both receiving and sending emails
- No port 587 (submission) - Not needed for this use case
- Connection limits and timeouts configured

### `config/plugins.dev` / `config/plugins.prod`
Environment-specific plugin configurations:

**Development (`plugins.dev`):**
- `rcpt_to.in_host_list` - Basic recipient validation
- `raw_email_saver` - Raw email storage for testing

**Production (`plugins.prod`):**
- `tls` - TLS/SSL encryption support
- `fcrdns` - Reverse DNS lookup validation
- `helo.checks` - HELO/EHLO command validation
- `mail_from.is_resolvable` - Sender domain validation
- `spf` - SPF record validation
- `rcpt_to.in_host_list` - Recipient domain validation
- `auth/flat_file` - SMTP authentication
- `raw_email_saver` - Raw email storage for processing

### `config/redis.ini`
Redis connection configuration:
- Server: `redis:6379`
- Database: `0`
- Supports pub/sub functionality

### `config/host_list.dev` / `config/host_list.prod`
Environment-specific domain configurations:

**Development (`host_list.dev`):**
- `localhost` - Local testing
- `devify.local` - Development environment domain
- `example.com` - Example domain

**Production (`host_list.prod`):**
- `aimychats.com` - default hosted production domain
- Add every domain used by `AUTO_ASSIGN_EMAIL_DOMAIN`

`host_list.prod` and `AUTO_ASSIGN_EMAIL_DOMAIN` must agree. For example, if
users receive mail at `alice@example.com`, then:

```bash
AUTO_ASSIGN_EMAIL_DOMAIN=example.com
```

and `config/host_list.prod` must contain:

```text
example.com
```

### `plugins/raw_email_saver.js`
Custom plugin functionality:
- Listens to `hook_data` event to capture raw email data chunks
- Saves complete email files to inbox directory for processing
- Returns success status after successful email storage
- Supports configurable inbox directory via EMAIL_INBOX_DIR environment variable

## 🔧 Environment Variables

Container automatically installs these components on startup:
- `HARAKA_INSTALL_PLUGINS=haraka-plugin-redis` - Official Redis plugin
- `APK_INSTALL_PACKAGES=openssl` - OpenSSL support for TLS

## DNS Setup

For production inbound mail, point the public mail domain to the server running
the Haraka container.

Example for `AUTO_ASSIGN_EMAIL_DOMAIN=example.com`:

```text
example.com.        MX   10 mail.example.com.
mail.example.com.   A    <server-public-ip>
example.com.        TXT  "v=spf1 mx -all"
_dmarc.example.com. TXT  "v=DMARC1; p=quarantine; rua=mailto:admin@example.com"
```

Notes:

1. `MX` tells other mail servers to deliver `@example.com` mail to
   `mail.example.com`.
2. The `A` record must resolve to the public IP of the host exposing
   `HARAKA_SMTP_PORT`, normally port 25.
3. `SPF` and `DMARC` are not required for receiving mail, but help with domain
   hygiene and future outbound mail behavior.
4. If your cloud provider blocks port 25, inbound SMTP will not work until that
   block is removed or traffic is routed through an SMTP relay.

Optional DKIM helper:

```bash
./docker/haraka/generate_dkim.sh
```

The helper prints the TXT record that should be added at
`default._domainkey.<domain>`.

## 🚀 Usage

### Development Environment
```bash
docker compose -f docker-compose.dev.yml up -d haraka
```

### Production Environment
```bash
docker compose up -d haraka
```

### Inspect Saved Email Files
```bash
find data/haraka/emails -type f | head
```

## 📝 Important Notes

1. **Single File Mounting**: Uses single file mounting instead of directory mounting to avoid overwriting container's default configuration
2. **Domain Matching**: `AUTO_ASSIGN_EMAIL_DOMAIN` and `host_list.prod` must
   include the same inbound mail domain
3. **Permission Settings**: All configuration files are mounted in read-only mode (`:ro`)
4. **Log Directory**: Logs are stored in `./data/haraka/logs/` directory
5. **File Processing**: Django scheduled tasks process raw email files saved by
   Haraka from the shared mail directory

## 🔍 Troubleshooting

### Check Plugin Status
```bash
docker compose -f docker-compose.dev.yml logs haraka --tail=20
```

### Verify Redis Connection
```bash
docker compose -f docker-compose.dev.yml exec redis redis-cli ping
```

### Test Email Processing
```bash
swaks --server <haraka-ip> --from test@localhost --to user@localhost --data "Subject: Test\n\nTest message"
```

## 🔐 TLS/SSL Certificate Management

### Environment Differences

| Feature | Production | Development |
|---------|-----------|------------|
| Port 25 | ✅ STARTTLS Enabled | ✅ No Encryption |
| Port 587 | ❌ Not Used | ❌ Not Used |
| TLS | ✅ Required | ❌ Disabled |
| Certificates | Let's Encrypt | Not Required |

### Certificate Setup (Production)

The project includes a certificate management script at `scripts/manage-haraka-certs.sh`.

**First-time certificate application:**
```bash
# Set your domain and email
export HARAKA_DOMAIN=mail.your-domain.com
export HARAKA_CERT_EMAIL=admin@your-domain.com

# Apply for certificate
sudo ./scripts/manage-haraka-certs.sh apply
```

**Manual certificate renewal:**
```bash
sudo ./scripts/manage-haraka-certs.sh renew
```

**Install automatic renewal (cron job):**
```bash
sudo ./scripts/manage-haraka-certs.sh install-cron
```

**Check certificate status:**
```bash
sudo ./scripts/manage-haraka-certs.sh status
```

### Certificate Paths

- **Host machine**: `./data/certs/haraka/cert.pem` and `./data/certs/haraka/key.pem`
- **Haraka container**: `/etc/haraka/certs/cert.pem` and `/etc/haraka/certs/key.pem`

The host directory is mounted as read-only in the container.

### Verify TLS Configuration

```bash
# Test STARTTLS connection
openssl s_client -connect mail.your-domain.com:25 -starttls smtp

# Expected output should show certificate details and "Verify return code: 0 (ok)"
```

## 📧 Mail Client Configuration

### Production Environment
- **Purpose**: Receive emails from other mail servers
- **Port**: 25
- **Encryption**: STARTTLS (optional)
- **Authentication**: Not required for incoming mail

### Development/Testing Environment

**Apple Mail Client Configuration Example:**
```
Outgoing Mail Server (SMTP):
  Server: localhost (or 127.0.0.1)
  Port: 25
  Authentication: None
  Encryption: None
  Username: (leave empty)
  Password: (leave empty)
```

**Test sending from command line:**
```bash
# Using swaks
swaks --server localhost:25 \
  --from test@devify.local \
  --to user@devify.local \
  --header "Subject: Test Email" \
  --body "This is a test message"

# Using telnet
telnet localhost 25
EHLO localhost
MAIL FROM: <test@devify.local>
RCPT TO: <user@devify.local>
DATA
Subject: Test Email

This is a test message.
.
QUIT
```

## 🔄 Deployment & Restart

### After Certificate Updates
```bash
# Restart Haraka container to load new certificates
docker compose restart haraka

# Or if using development environment
docker compose -f docker-compose.dev.yml restart haraka
```

### Complete Restart
```bash
# Production
docker compose down
docker compose up -d haraka

# Development
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d haraka
```
