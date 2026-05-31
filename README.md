# About Devify

## What is Devify?

Devify is an **enterprise-grade AI-powered conversation intelligence and data application platform**.

Its core value is straightforward:

1. Collect fragmented communication content from enterprise work scenarios
2. Understand both text and image content with AI
3. Transform raw conversations into structured summaries and reusable data
4. Feed that data into downstream systems such as JIRA, knowledge bases, and workflow automation

What matters most is not only collection or summarization, but the abstraction behind the system:

- **Data Layer**: unify scattered raw inputs
- **Data Processing Layer**: convert raw content into structured understanding
- **Data Application Layer**: build reusable business applications on top of that data

This layered design is the real long-term value of the project, because it makes horizontal expansion much easier as new sources and new applications are added.

## Why We Built It

Devify did not start from an abstract product idea. It grew out of real enterprise collaboration problems.

In many teams, important information is scattered across:

- WeChat groups
- email threads
- screenshots
- temporary chat messages
- cross-functional coordination channels
- personal notes and informal records

Decisions get made, requirements get clarified, and issues get solved, but the result often never becomes structured knowledge.

This creates recurring enterprise pain points:

- important context is scattered across multiple channels
- enterprise and personal information are separated and difficult to unify
- key decisions are easy to miss or lose
- manual knowledge consolidation is expensive and unreliable
- downstream systems receive incomplete information
- valuable business data remains trapped inside unstructured conversations

Devify exists to solve that gap.

## Purpose and Scenarios

At the current stage, the clearest and most practical workflow is:

- collect chat records and related materials through email
- analyze both text and image content
- generate structured summaries
- output reusable data for project delivery and business workflows

The core purpose is to bring fragmented enterprise and personal information into one unified system, so it can be continuously organized, understood, and reused.

Today, email is the first stable entry point.

In the future, Devify can expand to unify more inputs such as:

- voice content
- meeting notes and transcripts
- forwarded records from more platforms
- other multimodal work artifacts

## How Devify Works

```text
Enterprise / Personal Information

  WeChat groups
  Email threads
  Screenshots
  Temporary chat messages
  Personal notes
  Meeting records

            |
            v

  +-------------------+
  |    Data Layer     |
  |-------------------|
  | Unified raw input |
  | collection layer  |
  +-------------------+

            |
            v

  +-----------------------------+
  |  Data Processing Layer      |
  |-----------------------------|
  | LLM understanding           |
  | Multimodal intent detection |
  | Image understanding         |
  | Summary + metadata extract  |
  +-----------------------------+

            |
            v

  +-----------------------------+
  |   Data Application Layer    |
  |-----------------------------|
  | JIRA                        |
  | Knowledge base              |
  | Reports                     |
  | Workflow automation         |
  | Future app center features  |
  +-----------------------------+
```

```text
Current practical path

  Chat records / screenshots / related materials
                    |
                    v
           Forward by email
                    |
                    v
        AI understanding and extraction
                    |
                    v
        Structured summary and data
                    |
                    v
   JIRA / Knowledge Base / Workflow Data
```

## Threadline Core Feature

Threadline is the current flagship workflow inside Devify.

It was born from a practical enterprise pain point: many issues are discussed and even resolved inside chat tools, but the resulting knowledge never enters the formal delivery system.

Threadline focuses on:

- collecting conversation content
- understanding images and text with AI
- generating structured summaries
- delivering the result to downstream systems such as JIRA

This approach is not limited to WeChat chat records. It can be extended to many communication scenarios while keeping the output structured and reusable.

More importantly, Threadline is not just a single feature. It is an example of how the platform turns fragmented communication into reusable data products through the three-layer model.

## Management Console

Runtime configuration is no longer limited to Django Admin.

Many core settings can now be configured in the management UI:

- `/management/llm/config`
  Configure provider credentials, models, defaults, and connection testing
- `/management/app-settings`
  Configure global app settings, Threadline model bindings, notification channels, and Relay smart-channel model bindings
- `/management/threadline/config`
  Configure Threadline workflow model settings
- `/management/threadline/periodic-tasks`
  Configure scheduled tasks
- `/management/notifier/channels`
  Configure webhook and notification channels
- `/management/notifier/settings`
  Configure notification-related settings
- `/management/billing/settings`
  Configure billing-related runtime settings

Django Admin is still available for low-level inspection and legacy operations, but it is no longer the only day-to-day configuration path.

## Supported LLM Platforms

Devify is not tied to a single LLM vendor.

The current built-in provider catalog in the management console includes:

- OpenAI
- OpenAI-compatible endpoints
- Azure OpenAI
- Google Gemini
- Anthropic
- Mistral
- DashScope (Qwen)
- DeepSeek
- xAI
- MiniMax
- Moonshot
- ZAI
- Volcengine
- Meta Llama
- Amazon Nova
- NVIDIA NIM
- OpenRouter

This allows you to bind different models for different jobs, such as:

- one multimodal model for image understanding and intent detection
- one text model for summarization and metadata extraction
- one dedicated model for smart delivery channels

## Quick Start

### Development

```bash
cp env.sample .env
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up -d
```

Default local access:

- API and Django Admin: `http://localhost:8000`
- Flower: `http://localhost:5555`

### Production

```bash
cp env.sample .env
docker compose build
docker compose up -d
```

The production compose file includes the full application stack: API, worker,
scheduler, UI, MySQL, Redis, Nginx, and Haraka.

### Haraka Inbound Email

Devify includes Haraka for auto-assigned inbound email addresses. When enabled,
users can receive mail at addresses such as:

```text
{username}@{AUTO_ASSIGN_EMAIL_DOMAIN}
```

Haraka receives SMTP traffic on port 25, stores raw email files under
`data/haraka/emails`, and the worker/scheduler processes those files into the
normal email workflow.

For production, the mail domain must be configured in three places:

- `.env`: `AUTO_ASSIGN_EMAIL_DOMAIN=example.com`
- `docker/haraka/config/host_list.prod`: add `example.com`
- DNS: add an MX record for `example.com` pointing to the host that runs Haraka

Recommended DNS records:

```text
example.com.        MX   10 mail.example.com.
mail.example.com.   A    <server-public-ip>
example.com.        TXT  "v=spf1 mx -all"
_dmarc.example.com. TXT  "v=DMARC1; p=quarantine; rua=mailto:admin@example.com"
```

Port 25 must be open from the public internet. If STARTTLS is required, create
Haraka certificates with:

```bash
HARAKA_DOMAIN=mail.example.com HARAKA_CERT_EMAIL=admin@example.com \
  ./scripts/manage-haraka-certs.sh apply
```

More details are documented in `docker/haraka/README.md`.

## Required Configuration

Before first run, review at least these settings in `.env`:

### Basic Runtime

- `USE_MIRROR`
- `SITE_DOMAIN`
- `FRONTEND_URL`
- `VITE_API_BASE_URL`
- `AUTO_ASSIGN_EMAIL_DOMAIN`

### Email / Notifications

- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`

### Optional OAuth

- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`

### AI Models and Providers

AI services are now configured primarily through the management console, not through a single fixed set of `.env` variables.

Recommended path after startup:

1. Open `/management/llm/config`
2. Add one or more `LLMConfig` entries
3. Configure provider-specific fields such as:
   - `api_key`
   - `api_base`
   - `model`
   - `deployment` for Azure OpenAI
   - optional parameters such as `max_tokens`, `temperature`, `top_p`, and request timeout
4. Bind the appropriate models in `/management/app-settings` and `/management/threadline/config`

In other words, `.env` is mainly for base runtime setup, while actual model provider configuration is managed in the application.

## Self-Hosting Requirements

Minimum recommendation:

- 2 CPU cores
- 4GB RAM
- 20GB storage
- Docker and Docker Compose

External services:

- at least one supported LLM provider account and API credentials
- multimodal model capability for image understanding and intent detection
- SMTP server for notifications

For HTTPS, use a reverse proxy such as Nginx Proxy Manager, Traefik, or Caddy.

## Open Source & Commercial Editions

This repository contains the **self-hosted Devify platform** with an Apache-2.0 open core and a separately licensed billing module.

Commercial SaaS version: [aimychats.com](https://aimychats.com)

Core difference at a glance:

- self-hosted platform: open core, self-managed deployment, IMAP-based email collection
- commercial SaaS edition: managed hosting, dedicated email, real-time SMTP, and additional operational features

## Licensing

Devify uses a mixed licensing structure:

- core platform: `Apache License 2.0`
- billing module: separate `Devify Billing Commercial License`

Billing follows one simple rule:

- internal company use is allowed
- external operation is prohibited without separate authorization

See `LICENSE`, `LICENSES.md`, `TRADEMARKS.md`, and `devify/billing/COMMERCIAL-LICENSE.md`.
