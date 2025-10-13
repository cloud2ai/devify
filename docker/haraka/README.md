# Haraka Email Server Configuration for Devify

This directory contains Haraka mail server configuration files for the Devify project, designed to receive emails and push them to Redis queue for Django processing.

## 📁 Directory Structure

```
docker/haraka/
├── config/
│   ├── plugins.dev       # Development plugin configuration
│   ├── plugins.prod      # Production plugin configuration
│   ├── redis.ini         # Redis connection configuration
│   ├── host_list.dev     # Development domains
│   └── host_list.prod    # Production domains
├── plugins/
│   └── redis_queue.js    # Custom Redis queue plugin
└── README.md             # This documentation
```

## ⚙️ Configuration Files

### `config/plugins.dev` / `config/plugins.prod`
Environment-specific plugin configurations:

**Development (`plugins.dev`):**
- `rcpt_to.in_host_list` - Basic recipient validation
- `redis` - Official Redis plugin
- `redis_queue` - Custom Redis queue plugin

**Production (`plugins.prod`):**
- `fcrdns` - Reverse DNS lookup validation
- `helo.checks` - HELO/EHLO command validation
- `mail_from.is_resolvable` - Sender domain validation
- `spf` - SPF record validation
- `rcpt_to.in_host_list` - Recipient domain validation
- `redis` - Official Redis plugin
- `redis_queue` - Custom Redis queue plugin

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
- `devify.com` - Main production domain
- `mail.devify.com` - Mail subdomain
- `devify.local` - Alternative production domain

### `plugins/redis_queue.js`
Custom plugin functionality:
- Listens to `hook_data_post` event to capture email data
- Formats email data as JSON and pushes to `haraka:email_queue`
- Listens to `hook_queue` event to return success status

## 🔧 Environment Variables

Container automatically installs these components on startup:
- `HARAKA_INSTALL_PLUGINS=haraka-plugin-redis` - Official Redis plugin
- `APK_INSTALL_PACKAGES=openssl` - OpenSSL support for TLS

## 📊 Email Data Format

Email data format pushed to Redis:

```json
{
  "from": "sender@domain.com",
  "to": ["recipient@domain.com"],
  "subject": "Email Subject",
  "message_id": "Unique Message ID",
  "date": "2024-09-18T07:20:00Z",
  "body": "Email body content",
  "size": 1234,
  "uuid": "Transaction unique identifier"
}
```

## 🚀 Usage

### Development Environment
```bash
docker-compose -f docker-compose.dev.yml up -d haraka
```

### Production Environment
```bash
docker-compose up -d haraka
```

### Monitor Redis Queue
```bash
# Check queue length
docker-compose exec redis redis-cli LLEN "haraka:email_queue"

# View queue contents
docker-compose exec redis redis-cli LRANGE "haraka:email_queue" 0 -1

# Process emails from queue
docker-compose exec redis redis-cli RPOP "haraka:email_queue"
```

## 📝 Important Notes

1. **Single File Mounting**: Uses single file mounting instead of directory mounting to avoid overwriting container's default configuration
2. **Plugin Order**: `redis` plugin must be loaded before `redis_queue` plugin
3. **Permission Settings**: All configuration files are mounted in read-only mode (`:ro`)
4. **Log Directory**: Logs are stored in `./data/haraka/logs/` directory
5. **Queue Processing**: Django scheduled tasks should process emails from `haraka:email_queue` using `RPOP` command

## 🔍 Troubleshooting

### Check Plugin Status
```bash
docker-compose -f docker-compose.dev.yml logs haraka --tail=20
```

### Verify Redis Connection
```bash
docker-compose -f docker-compose.dev.yml exec redis redis-cli ping
```

### Test Email Processing
```bash
swaks --server <haraka-ip> --from test@localhost --to user@localhost --data "Subject: Test\n\nTest message"
```