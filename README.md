# About Devify

## What is Devify?

### Purpose

Devify is an **AI Agent-powered personal productivity platform** that leverages intelligent automation to enhance daily work efficiency.

**Project Evolution:**

The project was originally conceived as a toolkit for AI-driven development lifecycle management, designed to accelerate R&D workflows and address pain points in software development processes. However, through practical application and iteration, we discovered that the core AI Agent architecture we built could be more effectively applied to solve broader personal productivity challenges in everyday work scenarios.

This realization led to a strategic pivot: rather than focusing solely on development lifecycle automation, we evolved Devify into a personal productivity platform that uses AI Agents to streamline various aspects of daily work—from email processing and information organization to task creation and knowledge management. The underlying AI Agent framework remains robust and flexible, now serving a wider range of personal efficiency use cases.

### Vision

By integrating advanced AI technologies and Agent-based automation, Devify aims to:
- Automate repetitive and time-consuming tasks in daily work routines
- Reduce manual effort in information processing and organization
- Enable individuals to focus on high-value creative and strategic work
- Continuously expand AI Agent capabilities to cover more productivity scenarios

### Key Features

Below is a list of the main tools and components included in this project:

- **Threadline Core Feature:** Automatically organizes and structures chat records (including WeChat, WhatsApp, email, etc.) to streamline requirements gathering and task creation. As an extension, these organized records can be sent to JIRA issues or other platforms as needed.

#### Threadline AI Agent

Threadline AI Agent was born out of a common pain point in daily project management: many issues and solutions are discussed and resolved within WeChat groups, but this valuable knowledge is often lost because it is not systematically captured in the product knowledge base. Since WeChat does not provide a direct API to access all conversation content, and relying solely on delivery personnel to manually document these discussions is unreliable, we sought an alternative approach.

Our solution leverages the fact that WeChat allows users to forward chat records via email. By simply sending relevant chat logs to a designated internal mailbox, we can then utilize large language models and image recognition technologies to process the content.  After appropriate analysis and summarization, the processed information is automatically submitted to JIRA, enabling the initial accumulation of project knowledge with minimal manual intervention.

In fact, this approach is not limited to WeChat chat records.  It can be extended to many other scenarios as well. In the future, we will continue to broaden the boundaries of this model.

### Technical Overview

This project is a robust AI workflow and agent system, architected with Django and powered by Celery for efficient orchestration of diverse tasks. It streamlines business processes by integrating advanced AI capabilities, including large language models (LLMs), OCR, and speech technologies. All system management and configuration are currently handled through Django's built-in Admin Portal, enabling rapid development and easy maintenance. In future releases, dedicated user-facing interfaces will be introduced to further enhance accessibility and user experience, with the ultimate goal of evolving into a SaaS platform for broader adoption.

The AI workflow in this project is powered by **LangGraph**, a framework for building stateful, multi-actor applications with LLMs. The workflow architecture uses a StateGraph pattern with atomic database operations in prepare/finalize nodes, ensuring data consistency and enabling built-in checkpointing for error recovery. This approach provides better observability, maintainability, and resilience compared to traditional orchestration methods.

## Development

### Testing with Nox

This project uses [Nox](https://nox.thea.codes/) for development task automation. Nox provides a unified interface for running tests, code formatting, and other development tasks.

#### Available Nox Sessions

```bash
# Run all tests
nox -s tests

# Run EML email parsing tests
nox -s eml_tests

# Run unit tests only
nox -s unit_tests

# Run API tests only
nox -s api_tests

# Run functional tests only
nox -s functional_tests

# Generate test coverage report
nox -s coverage

# Auto format code
nox -s format

# Code quality check
nox -s lint

# Django system check
nox -s django_check

# Start development server
nox -s runserver
```

#### Installation

```bash
# Install nox
pip install nox

# Or using uv (faster)
uv pip install nox
```

## How to run Devify?

Devify supports both development and production environments using Docker. Please note the following differences:

- **Development Mode (`docker-compose.dev.yml`):**
  - Local source code is mounted into the container.
  - The application runs in Django development mode.
  - Any code changes on your host machine will automatically
    trigger a reload of the service inside the container.
  - This setup is ideal for rapid development and debugging.

- **Production Mode (`docker-compose.yml`):**
  - The application runs using Gunicorn as the WSGI server,
    providing better performance and stability.
  - Source code is not mounted; the container uses a built image.
  - This setup is recommended for deployment and production use.

### Service Architecture

Both modes include the following services:

- **devify-api**: Django API server (Django dev server in dev mode, Gunicorn in production)
- **devify-worker**: Celery worker for background task processing
- **devify-scheduler**: Celery beat scheduler for periodic tasks
- **mysql**: MariaDB database server
- **redis**: Redis cache, message broker, and LangGraph checkpoint storage
- **nginx**: Reverse proxy server (production mode only)
- **flower**: Celery monitoring dashboard (development mode only)

**Optional Services (based on email collection mode):**

- **haraka**: Open-source SMTP server for auto_assign mode (receives incoming emails and saves to file system)
  - Only required if using `auto_assign` mode in `email_config`
  - Emails are automatically assigned to users based on recipient addresses (email aliases)
  - Simplifies multi-user email collection without individual IMAP credentials

### Key Differences

**Development Mode:**
- Uses `development` command to start Django's built-in server
- Includes Flower dashboard for Celery monitoring
- Source code is mounted for live reloading
- Exposes Django admin on port 8000

**Production Mode:**
- Uses `gunicorn` command for production-grade WSGI server
- Includes Nginx reverse proxy with SSL support
- Optimized for performance and stability
- Health checks and restart policies enabled

### Environment Preparation

This step is required for both development and production environments.

```
cp env.sample .env
```

### Docker Build Configuration

Devify supports using Chinese mirrors for faster package downloads during Docker builds. This is particularly useful for users in China or regions with slow access to default package sources.

#### Mirror Configuration

The Docker build process can be configured to use Chinese mirrors through the `USE_MIRROR` environment variable:

**For Chinese users (recommended):**
```bash
# In .env file
USE_MIRROR=true
```

**For international users:**
```bash
# In .env file
USE_MIRROR=false
```

#### What the Mirror Configuration Does

When `USE_MIRROR=true`, the Dockerfile will:

1. **Debian Package Sources**: Replace default Debian sources with Tsinghua University mirrors
   - `deb.debian.org` → `mirrors.tuna.tsinghua.edu.cn`
   - `security.debian.org` → `mirrors.tuna.tsinghua.edu.cn/debian-security`

2. **Python Package Sources**: Use Tsinghua PyPI mirror for faster pip installs
   - `pypi.org` → `pypi.tuna.tsinghua.edu.cn`

3. **Build Process**: Automatically configure both system packages and Python dependencies

#### Default Behavior

- **Development Mode** (`docker-compose.dev.yml`): `USE_MIRROR=true` (default)
- **Production Mode** (`docker-compose.yml`): `USE_MIRROR=false` (default)
- **Override**: You can override the default by setting `USE_MIRROR` in your `.env` file

#### Docker Compose Differences

**Development Mode (`docker-compose.dev.yml`):**
- Uses local image name: `devify:latest`
- Default `USE_MIRROR=true` for faster development builds
- Includes Flower monitoring dashboard
- Source code mounted for live reloading

**Production Mode (`docker-compose.yml`):**
- Uses remote image: `registry.cn-beijing.aliyuncs.com/cloud2ai/devify:latest`
- Default `USE_MIRROR=false` for production builds
- Includes Nginx reverse proxy
- Optimized for production deployment

This environment values should be provided:

```
# Docker Build Configuration
USE_MIRROR=true

# Database Configuration
DB_ENGINE=mysql
MYSQL_ROOT_PASSWORD=root_password
MYSQL_PORT=3306
MYSQL_USER=devify
MYSQL_PASSWORD=devifyPass
MYSQL_DATABASE=devify

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379
CELERY_RESULT_BACKEND=redis://redis:6379
CELERY_CONCURRENCY=4
CELERY_MAX_TASKS_PER_CHILD=1000
CELERY_MAX_MEMORY_PER_CHILD=256000
CELERY_LOG_LEVEL=INFO

# Server Configuration (Production)
WORKERS=1
THREADS=1
NGINX_HTTP_PORT=10080
NGINX_HTTPS_PORT=10443

AZURE_OPENAI_API_BASE=https://your-azure-openai-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_DEPLOYMENT=your-azure-openai-deployment
AZURE_OPENAI_API_VERSION=your-azure-openai-api-version

# OCR
AZURE_DOCUMENT_INTELLIGENCE_KEY="your-azure-document-intelligence-key"
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://your-azure-document-intelligence-endpoint.cognitiveservices.azure.com/"

# Email Collection (Haraka auto_assign mode)
AUTO_ASSIGN_EMAIL_DOMAIN=devify.local
HARAKA_EMAIL_BASE_DIR=/opt/haraka/emails
```

### Run in Development Mode

```
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up -d
```

**Note:** Development mode uses `USE_MIRROR=true` by default for faster builds in China. You can override this by setting `USE_MIRROR=false` in your `.env` file.

Django API services is running in http://your_host:8000

Check output:

```
docker logs -f devify-api
```

### Run in Production Mode

```
docker-compose -f docker-compose.yml build
docker-compose -f docker-compose.yml up -d
```

**Note:** Production mode uses `USE_MIRROR=false` by default. For faster builds in China, you can set `USE_MIRROR=true` in your `.env` file.

### Service Access

**Development Mode:**
- Django API: http://localhost:8000
- Django Admin: http://localhost:8000/admin/
- Flower Dashboard: http://localhost:5555

**Production Mode:**
- Nginx HTTP: http://localhost:10080
- Nginx HTTPS: https://localhost:10443
- Health Check: http://localhost:10080/health

### Container Management

**View logs:**
```bash
# API service
docker logs -f devify-api

# Worker service
docker logs -f devify-worker

# Scheduler service
docker logs -f devify-scheduler
```

**Execute commands:**
```bash
# Enter API container
docker exec -it devify-api bash

# Run Django management commands
docker exec -it devify-api python manage.py migrate
docker exec -it devify-api python manage.py collectstatic
```

## Threadline Settings

Before using Threadline features, you should initialize the required settings for all users. This can be done via a management command inside the API container. The command will automatically create default records for all necessary THREADLINE settings (`email_config`, `issue_config`, `prompt_config`, `webhook_config`) for each user if they do not already exist.

To simplify configuration, all required settings should be added here. Below are the key-value pairs you need to set before using the system. The table describes the key design, and the values should be saved in JSON format.

| Key                  | Description                                                      | Required | Example Key Fields/Notes                |
|----------------------|------------------------------------------------------------------|----------|-----------------------------------------|
| email_config         | Email collection mode and configuration (auto_assign or custom_imap) | Yes      | See below - supports Haraka auto-assign and IMAP modes |
| issue_config         | Issue creation engine configuration (JIRA, email, Slack, etc.)   | Yes      | See below                              |
| prompt_config        | AI prompt templates for email/attachment/summary processing       | Yes      | See below                              |
| webhook_config       | Webhook configuration for external notifications                  | No       | See below                              |

> **Note:**
> All values must be valid JSON.
> If you add new fields to the models or settings, update this table accordingly.

**How to initialize THREADLINE settings:**

1. **Enter the API container:**

   ```bash
   docker exec -it devify-api python manager.py init_threadline_settings --user admin
   ```

**Note:**
- The initialization command is idempotent and safe to run multiple times.
- All values are stored in JSON format and should be customized according to your actual email, JIRA, and AI integration requirements.

2. **Edit the settings in Django Admin:**

   After initialization, log in to the Django Admin panel and navigate to the **Settings** section. You can then edit the values for each key (`email_config`, `issue_config`, `prompt_config`, `webhook_config`) as needed for your environment.

   > **Tip:**
   > You can also update these settings directly in the database if required.

3. **Log in to Django Admin**
   - Visit [http://localhost:8000/admin](http://localhost:8000/admin) in your browser.
   - Log in with your admin credentials.
   - Username: admin
   - Password: adminpassword

4. **Navigate to the Settings Model**
   - In the sidebar, find and click on **Settings** under THREADLINE

### Email Configuration (email_config)

The email configuration supports two distinct modes for email collection, providing flexibility for different deployment scenarios.

#### Email Collection Modes

Threadline supports two email collection modes:

| Mode | Description | Use Case | Email Source |
|------|-------------|----------|--------------|
| **auto_assign** | Haraka-based automatic email assignment | Multi-user shared email server, no IMAP credentials needed | File system |
| **custom_imap** | User-specific IMAP server configuration | Personal email accounts, custom IMAP servers | IMAP server |

**Default Mode**: `auto_assign` (recommended for team collaboration scenarios)

#### Mode Selection Guide

Choose the appropriate mode based on your deployment scenario:

| Scenario | Recommended Mode | Reason |
|----------|------------------|--------|
| Team collaboration with shared email domain | `auto_assign` | No need to manage individual IMAP credentials |
| Multiple users need different email aliases | `auto_assign` | Flexible alias management, one user can have multiple aliases |
| Enterprise deployment with many users | `auto_assign` | Simplified onboarding, just create an alias |
| Personal use or single user | `custom_imap` | Direct access to personal email account |
| Users have different email providers | `custom_imap` | Each user connects to their own email server |
| Need real-time email processing | `auto_assign` | Haraka provides instant email availability |
| Existing IMAP infrastructure | `custom_imap` | Leverage existing email servers |

#### Mode 1: Auto-Assign (Haraka-based) - Recommended

In this mode, emails are received by **Haraka** (an open-source SMTP server) and automatically assigned to users based on recipient email addresses. This eliminates the need for individual IMAP configurations and simplifies multi-user deployments.

**Why Haraka?**

Haraka was introduced to solve several key challenges in multi-user email processing:

1. **Simplified User Management**: No need to collect and manage individual IMAP credentials for each user
2. **Centralized Email Collection**: Single SMTP server handles emails for all users
3. **Flexible Email Routing**: Users can have multiple email aliases for different purposes (e.g., projects, teams)
4. **Security**: No storage of user email passwords in the system
5. **Scalability**: Easily add new users without configuring email servers
6. **Real-time Processing**: Haraka saves emails to file system immediately upon receipt

**How it works:**
1. Haraka receives incoming emails and saves them to the file system (`HARAKA_EMAIL_BASE_DIR/inbox/`)
2. The `haraka_email_fetch` task periodically scans the inbox directory
3. For each email, the system matches the recipient address to user email aliases
4. The email is automatically assigned to the matching user
5. If no user is found, the email is logged and moved to the failed directory
6. Processed emails are moved to `processed/` directory for archival

**Email Alias System:**

Each user automatically gets a default email alias based on their username:
- Default format: `{username}@{AUTO_ASSIGN_EMAIL_DOMAIN}`
- Example: User `admin` → `admin@devify.local`

Users can create additional custom aliases for different purposes:
- Project-specific: `project-alpha@devify.local`
- Team-specific: `devops-team@devify.local`
- Role-specific: `support@devify.local`

**Configuration:**
```json
{
  "mode": "auto_assign"
}
```

**Global Settings (Environment Variables):**
- `AUTO_ASSIGN_EMAIL_DOMAIN`: The email domain for all users (default: `devify.local`)
- `HARAKA_EMAIL_BASE_DIR`: Haraka email storage directory (default: `/opt/haraka/emails`)

**Directory Structure:**
```
/opt/haraka/emails/
├── inbox/           # Incoming emails waiting to be processed
├── processed/       # Successfully processed emails (archived)
└── failed/          # Emails that failed processing (for debugging)
```

**Advantages:**
- ✅ No IMAP credentials needed per user
- ✅ Instant email availability (no polling delay)
- ✅ Multiple aliases per user
- ✅ Centralized email management
- ✅ Easy to add new users (just create an alias)
- ✅ Better security (no password storage)

**Managing Email Aliases:**

In Django Admin, navigate to **THREADLINE** → **Email Aliases** to manage user aliases:

1. **View all aliases**: See all configured email aliases and their associated users
2. **Create new alias**: Click "Add Email Alias" and enter:
   - User: Select the user who will receive emails sent to this alias
   - Alias: Enter the alias name (without domain, e.g., `project-alpha`)
   - Is Active: Check to enable the alias
3. **Full email address**: The system automatically combines your alias with the configured domain (e.g., `project-alpha@devify.local`)
4. **Uniqueness check**: The system ensures each alias is unique across all users

**Haraka Setup (for auto_assign mode):**

If you plan to use auto_assign mode, you need to deploy Haraka SMTP server:

1. **Install Haraka**: Follow [Haraka documentation](https://haraka.github.io/)
2. **Configure email storage**: Set Haraka to save emails to `HARAKA_EMAIL_BASE_DIR`
3. **DNS/MX Records**: Point your domain's MX record to your Haraka server
4. **Directory permissions**: Ensure the Django application can read from Haraka directories

Haraka configuration is beyond the scope of this README. Please refer to Haraka's official documentation for deployment details.

#### Mode 2: Custom IMAP

In this mode, each user configures their own IMAP server credentials for fetching emails from personal or corporate email accounts.

**Configuration Structure:**

| Key | Type | Description | Required |
|-----|------|-------------|----------|
| mode | string | Must be "custom_imap" | Yes |
| imap_config | object | IMAP server configuration | Yes |
| filter_config | object | Email filtering rules (optional) | No |

**IMAP Config Fields:**

| Key               | Type     | Description                                 | Example                        |
|-------------------|----------|---------------------------------------------|--------------------------------|
| imap_host         | string   | IMAP server hostname                        | "imap.feishu.cn"               |
| smtp_ssl_port     | integer  | SMTP SSL port (default: 465)                | 465                            |
| smtp_starttls_port| integer  | SMTP StartTLS port (default: 587)           | 587                            |
| imap_ssl_port     | integer  | IMAP SSL port (default: 993)                | 993                            |
| username          | string   | Email username                              | "user@example.com"             |
| password          | string   | Email password or app-specific password     | "your-password"                |
| use_ssl           | boolean  | Enable SSL connection                       | true                           |
| use_starttls      | boolean  | Enable StartTLS                             | false                          |
| delete_after_fetch| boolean  | Delete emails from server after fetching (default: false) | false              |

**Filter Config Fields (Optional):**

| Key              | Type     | Description                                                        | Example                |
|------------------|----------|--------------------------------------------------------------------|------------------------|
| filters          | array    | List of IMAP search criteria to apply when fetching emails         | ["UNSEEN", "SINCE \"24-Jul-2025\""] |
| exclude_patterns | array    | Patterns to exclude emails, e.g., subjects containing keywords     | ["spam", "newsletter"] |
| max_age_days     | integer  | Maximum age of emails to process, in days                          | 7                      |

**Complete Example (Custom IMAP Mode):**
```json
{
  "mode": "custom_imap",
  "imap_config": {
    "imap_host": "imap.gmail.com",
    "smtp_ssl_port": 465,
    "smtp_starttls_port": 587,
    "imap_ssl_port": 993,
    "username": "your-email@gmail.com",
    "password": "your-app-specific-password",
    "use_ssl": true,
    "use_starttls": false,
    "delete_after_fetch": false
  },
  "filter_config": {
    "filters": ["UNSEEN"],
    "exclude_patterns": ["spam", "newsletter"],
    "max_age_days": 7
  }
}
```

**Note on `delete_after_fetch`:**
- `false` (default, recommended): Emails remain on the IMAP server after fetching. Duplicate emails are automatically prevented by the system's `unique_together` constraint on `(user, message_id)`.
- `true`: Emails are permanently deleted from the IMAP server after successful fetch. Use this to save server storage space, but be aware that emails cannot be re-fetched.

**Simple Example (Auto-Assign Mode):**
```json
{
  "mode": "auto_assign"
}
```

#### IMAP Filter Configuration (custom_imap mode only)

When using `custom_imap` mode, you can optionally configure filters in the `filter_config` section of `email_config` to control which emails are fetched.

**Available IMAP Search Criteria:**

| Category         | Criteria                    | Description                                    | Example                                    |
|------------------|-----------------------------|------------------------------------------------|--------------------------------------------|
| **Time-based**   | `SINCE`                     | Emails received after specified date          | `"SINCE \"24-Jul-2025\""`                  |
|                  | `BEFORE`                    | Emails received before specified date         | `"BEFORE \"25-Jul-2025\""`                 |
|                  | `ON`                        | Emails received on specified date             | `"ON \"24-Jul-2025\""`                     |
| **Status**       | `UNSEEN`                    | Unread emails                                 | `"UNSEEN"`                                 |
|                  | `SEEN`                      | Read emails                                   | `"SEEN"`                                   |
|                  | `FLAGGED`                   | Flagged emails                                | `"FLAGGED"`                                |
|                  | `UNFLAGGED`                 | Unflagged emails                              | `"UNFLAGGED"`                              |
| **Sender/Recipient** | `FROM`                  | Emails from specific sender                   | `"FROM \"sender@example.com\""`            |
|                  | `TO`                        | Emails to specific recipient                  | `"TO \"recipient@example.com\""`           |
|                  | `CC`                        | Emails CC'd to specific address               | `"CC \"cc@example.com\""`                  |
| **Content**      | `SUBJECT`                   | Emails with subject containing keyword        | `"SUBJECT \"important\""`                  |
|                  | `BODY`                      | Emails with body containing keyword           | `"BODY \"urgent\""`                        |
|                  | `TEXT`                      | Emails with subject or body containing keyword | `"TEXT \"meeting\""`                       |

**Note:**
- The `filters` array can contain multiple IMAP search criteria (combined with AND logic)
- Date format should be "DD-MMM-YYYY" (e.g., "24-Jul-2025")
- The system automatically adds time-based filtering using `last_email_fetch_time` for incremental fetching
- Filter configuration is **not applicable** to auto_assign mode (Haraka processes all incoming emails)

### Issue Config(issue_config)

The issue configuration supports multiple engines (JIRA, email, Slack, etc.) with engine-specific settings.

| Key                | Type     | Description                                      | Example                      |
|--------------------|----------|--------------------------------------------------|------------------------------|
| enable             | boolean  | Whether issue creation is enabled                | true                         |
| engine             | string   | Issue creation engine type                       | "jira"                       |
| jira               | object   | JIRA-specific configuration (when engine="jira") | See JIRA config below        |

#### JIRA Configuration (when engine="jira")

| Key                | Type     | Description                                      | Example                      |
|--------------------|----------|--------------------------------------------------|------------------------------|
| url                | string   | JIRA server URL                                  | "https://jira.example.com"   |
| username           | string   | JIRA account username                            | "jira-user"                  |
| api_token          | string   | JIRA API token or password                       | "your-api-token"             |
| summary_prefix     | string   | Prefix for issue summary                         | "[AI]"                       |
| summary_timestamp  | boolean  | Add timestamp to summary                         | true                         |
| project_key        | string   | Default JIRA project key                         | "PRJ"                        |
| allow_project_keys | array    | Allowed project keys for validation              | ["PRJ", "REQ"]               |
| project_prompt     | string   | LLM prompt for project key selection (empty = use default) | "" or "The project key is: ..." |
| default_issue_type | string   | Default issue type for new issues                | "Task"                       |
| default_priority   | string   | Default priority for new issues                  | "High"                       |
| epic_link          | string   | Epic link key (optional)                         | "PRJ-1234"                   |
| assignee           | string   | Default assignee username (optional)             | "jira-assignee"              |
| allow_assignees    | array    | Allowed assignees for validation                 | ["assignee1", "assignee2"]   |
| assignee_prompt    | string   | LLM prompt for assignee selection (empty = use default) | "" or "Assign the issue to..." |
| description_prompt | string   | LLM prompt for description formatting (empty = use default) | "" or "Convert the provided..." |

**Example configuration:**

```json
{
  "enable": false,
  "engine": "jira",
  "jira": {
    "url": "your-jira-url",
    "username": "your-jira-username",
    "api_token": "your-api-token-or-password",
    "summary_prefix": "[AI]",
    "summary_timestamp": true,
    "project_key": "your-default-project-key",
    "allow_project_keys": ["PRJ", "REQ"],
    "project_prompt": "",
    "default_issue_type": "your-default-issue-type",
    "default_priority": "your-default-priority",
    "epic_link": "your-epic-link-key",
    "assignee": "your-default-assignee-username",
    "allow_assignees": ["assignee1", "assignee2"],
    "description_prompt": "",
    "assignee_prompt": ""
  }
}
```

**Note about prompts:**
- If `project_prompt`, `assignee_prompt`, or `description_prompt` are empty strings (`""`), the system will use the default values directly without calling LLM
- This is the recommended approach for simple setups where you want to use fixed project keys, assignees, and standard description formatting
- If you want LLM-based dynamic selection, provide custom prompts for these fields

### Prompt Config (prompt_config)

| Config Key              | Description                                                                                   | Required |
|------------------------|-----------------------------------------------------------------------------------------------|----------|
| `output_language`      | Default output language for LLM responses                                                     | Yes      |
| `email_content_prompt` | Organizes email/chat content for LLM processing.                                              | Yes      |
| `ocr_prompt`           | Processes OCR text from images for LLM summarization.                                         | Yes      |
| `summary_prompt`       | Summarizes email and attachment content for JIRA issue creation.                              | Yes      |
| `summary_title_prompt` | Generates a structured and concise JIRA issue title.                                          | Yes      |

**Example:**
```json
{
  "output_language": "zh-hans",
  "email_content_prompt": "Organize the provided email content (which may include chat records or message bodies) in chronological order into a conversation text with minimal polishing (clearly mark any assumptions), without altering any original meaning and retaining all information. Output format: [Date Time] Speaker: Content (on a single line, or wrapped across multiple lines if necessary), with image placeholders [IMAGE: filename.png] placed on separate lines in their original positions. Date and time: if the date is unknown, display only the time; if known, display both date and time. Conversation text must be plain text (excluding emojis, special characters, etc.) with clear structure. Always preserve the original language of the conversation; if the specified output language differs from the original language, include the original text on top and the translated text below. No explanations or additional content should be provided.",
  "ocr_prompt": "Organize the provided OCR results into plain text output, using Markdown formatting when necessary for code or quoted content (e.g., ``` for code blocks, > for quotes). Describe all explanatory or interpretive content in the specified output language, while keeping all actual OCR text in the original language from the image. Fully retain and describe all content without omission. Clearly highlight any normal, abnormal, or valuable information. Attempt to correct and standardize incomplete, unclear, or potentially erroneous OCR content without altering its original meaning, and mark any uncertain parts as [unclear]. Produce only structured text with necessary Markdown formatting, without any additional explanations, summaries, or unrelated content.",
  "summary_prompt": "Based on the provided content (including chronological chat records and OCR-recognized content from images), organize the chat records in chronological order, preserving the original speaker and language for each entry, fully retaining all information, and using Markdown formatting when necessary for code or quoted content. The output should include four sections: 1) **Main Content**: list the key points of the current conversation; 2) **Process Description**: provide a detailed description of the problem and its reproduction steps, marking any uncertain information as \"unknown\"; 3) **Solution** (if unresolved, indicate attempted measures): if the issue is resolved, list the solution; if unresolved, list measures already taken and their results, optionally including possible causes clearly marked as (speculation); 4) **Resolution Status**: indicate whether the issue has been resolved (Yes/No). Output must be well-structured, hierarchically clear plain text, without any additional explanations, summaries, or extra content, while highlighting any normal, abnormal, or valuable information for quick reference.",
  "summary_title_prompt": "Based on the chat records, extract a single structured title in the format: [Issue Category][Participant]Title Content; the title should use a verb-object structure, be concise, and accurately express the core problem or requirement, avoiding vague terms, with a maximum length of 300 characters; if the information is unclear, add [To Be Confirmed]; if multiple issues exist, extract only the most critical and central one, generating a single structured title."
}
```

### Webhook Config (webhook_config)

Threadline supports webhook notifications to keep you informed about email processing status. Configure webhook settings in Django Admin under **Settings**.

| Key                | Type     | Description                                      | Example                      | Required |
|--------------------|----------|--------------------------------------------------|------------------------------|----------|
| `url`              | string   | Webhook endpoint URL                             | `"https://open.feishu.cn/open-apis/bot/v2/hook/xxx"` | Yes |
| `events`           | array    | List of events to notify                         | `["issue_success", "ocr_failed", "llm_summary_failed"]` | No |
| `timeout`          | integer  | Request timeout in seconds                       | `10`                         | No |
| `retries`          | integer  | Number of retry attempts                         | `3`                          | No |
| `headers`          | object   | Custom headers for webhook requests              | `{"Authorization": "Bearer xxx"}` | No |
| `language`         | string   | Notification message language                    | `"zh-hans"` or `"en"`        | No |
| `provider`         | string   | Webhook provider type                            | `"feishu"`                   | No |

> **Note:** Whether the webhook is enabled is controlled by the `is_active` field of the `webhook_config` setting in Django Admin. There is no need for an `enabled` field inside the JSON config.

#### Supported Providers

Currently, the following webhook providers are supported:

- **`feishu`** (default): Feishu/Lark interactive card messages with Markdown format

#### Supported Events

Email processing status events from the simplified state machine can be configured for notifications:

**Simplified State Machine Events (4 States):**
- **`fetched`**: Email has been fetched and is ready for processing
- **`processing`**: Email is being processed through the LangGraph workflow (OCR → LLM → Issue creation)
- **`success`**: All processing completed successfully (terminal state)
- **`failed`**: Processing failed, can be retried

**Note:** The workflow now uses a simplified 4-state model. Detailed step-by-step progress (OCR, LLM, Issue creation) is managed internally by the LangGraph workflow and is not reflected as separate database states. For detailed progress tracking, check the workflow logs or LangGraph checkpoints.

#### Example Webhook Configuration

**Basic Configuration (simplified state model):**
```json
{
  "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
  "events": ["success", "failed"],
  "timeout": 10,
  "retries": 3,
  "headers": {},
  "language": "zh-hans",
  "provider": "feishu"
}
```

**Complete Configuration (all state transitions):**
```json
{
  "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
  "events": ["fetched", "processing", "success", "failed"],
  "timeout": 10,
  "retries": 3,
  "headers": {},
  "language": "zh-hans",
  "provider": "feishu"
}
```

**Minimal Configuration (only completion events):**
```json
{
  "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
  "events": ["success"],
  "timeout": 10,
  "retries": 3,
  "headers": {},
  "language": "zh-hans",
  "provider": "feishu"
}
```
#### Feishu Card Message Format

When using the `feishu` provider, notifications are sent as interactive cards with:

- **Color-coded headers**: Green (success), Red (failure), Blue (processing), Grey (other)
- **Markdown content**: Formatted with time, subject, sender, stage, and details
- **JIRA integration**: Includes issue key and URL when available
- **Internationalization**: Supports Chinese and English message content

#### Testing Webhook Configuration

Use the management command to test your webhook configuration:

```bash
# Test with default parameters
python manage.py test_webhook --user your_username

# Test with specific email and status
python manage.py test_webhook --user your_username --email-id 123 --old-status fetched --new-status jira_success

# Test with status transition only
python manage.py test_webhook --user your_username --old-status processing --new-status jira_success
```
### How to Configure the Scheduler in Django Admin

To enable automated email processing and JIRA issue creation, you need to configure the scheduler in Django Admin. Follow these steps:

3. **Configure the Scheduler Task**
   - In Django Admin, go to the **Periodic Tasks** section (provided by `django-celery-beat`).
   - Click **Add** to create a new periodic task.
   - In the **Task** field, select the task you want to schedule (for example, your email/JIRA processing task).
   - Set the **Interval** or **Crontab** schedule as needed (e.g., every 5 minutes).
   - Fill in any required arguments or keyword arguments for your task.
   - Optionally, add a description for clarity.
   - Ensure the **Enabled** checkbox is selected.

4. **Save the Task**
   - Click **Save** to activate the periodic task.

5. **Verify**
   - The periodic task will now run automatically according to your schedule (e.g., scanning emails, triggering LLM, submitting to JIRA).
   - You can edit, disable, or delete the task at any time in the **Periodic Tasks** section.

> **Tip:**
> Managing periodic tasks directly in the **Periodic Tasks** section is recommended for most use cases. No need to configure scheduler settings separately if you use `django-celery-beat`.

> **Important:**
> You must configure the following two periodic tasks in Django Admin (Periodic Tasks section):
>
> 1. **schedule_email_fetch**
>    - This is the main scheduler task. It periodically fetches emails from IMAP and Haraka sources and triggers the appropriate processing tasks (such as OCR, LLM summarization, and JIRA submission) based on the current state machine.
>
> 2. **reset_stuck_processing_emails**
>    - This task is responsible for detecting and resetting any email/message tasks that have been stuck in a pending or processing state for too long (timeout recovery). It helps ensure the system can recover from unexpected failures or timeouts.
>
> Both tasks are essential for robust, automated email-to-JIRA processing. Make sure both are scheduled to run at appropriate intervals (e.g., every 5 minutes for the main scheduler, every 10-30 minutes for the stuck task reset).

## Required Periodic Tasks

You **must** configure the following periodic tasks in Django Admin (**Periodic Tasks** section, provided by `django-celery-beat`):

1. **schedule_email_fetch**
   - Main scheduler task. Periodically fetches emails from IMAP and Haraka sources and triggers the LangGraph workflow for each email.
   - Automatically processes emails through the complete workflow (OCR → LLM → Issue creation).
   - **Recommended interval:** every 5 minutes.

2. **schedule_reset_stuck_processing_emails**
   - Detects and resets emails stuck in `PROCESSING` state for longer than the specified timeout.
   - Automatically marks stuck emails as `FAILED` with error message indicating manual intervention is required.
   - This prevents infinite retry loops and ensures system stability.
   - **Recommended interval:** every 10–30 minutes.
   - **Default timeout:** 30 minutes (configurable via `timeout_minutes` parameter)

3. **schedule_haraka_cleanup** (Optional)
   - Cleans up old Haraka email files from the file system to free up disk space.
   - **Recommended interval:** daily or weekly, depending on email volume.

4. **schedule_email_task_cleanup** (Optional)
   - Cleans up old EmailTask records from the database to prevent database bloat.
   - **Recommended interval:** daily or weekly.

> **Note:** Email fetching automatically triggers the LangGraph workflow for each new email, eliminating the need for separate processing tasks.

> **Tip:**
> You can edit, disable, or delete these tasks at any time in the **Periodic Tasks** section.

## EmailMessage State Machine & Exception Handling

The `EmailMessage` model uses a comprehensive state machine to track the processing stage with proper error handling and retry mechanisms.

### State Machine Flow (Simplified 4-State Model)

```mermaid
stateDiagram-v2
    [*] --> FETCHED
    FETCHED --> PROCESSING
    PROCESSING --> SUCCESS
    PROCESSING --> FAILED
    FAILED --> PROCESSING : Retry
    SUCCESS --> [*]
```

### State Descriptions

| Status | Description | Next Possible States |
|--------|-------------|---------------------|
| `FETCHED` | Email has been fetched and ready for processing | `PROCESSING` |
| `PROCESSING` | Email is being processed through the workflow (OCR → LLM → Issue creation) | `SUCCESS`, `FAILED` |
| `FAILED` | Processing failed, can be retried | `PROCESSING` |
| `SUCCESS` | All processing completed successfully (terminal state) | None (terminal) |

**Note**: Detailed step-by-step progress (OCR, LLM, Issue creation) is managed internally by the LangGraph workflow and is not reflected in the database status. The database status shows only the overall processing stage.

### Key Features

- **Simplified State Model**: Uses a 4-state model (FETCHED → PROCESSING → SUCCESS/FAILED) for easier monitoring and debugging
- **LangGraph Workflow**: Powered by LangGraph StateGraph for robust, stateful workflow execution with built-in checkpointing
- **Atomic Operations**: Prepare and Finalize nodes ensure atomic database operations for data consistency
- **Automatic Transitions**: Processing automatically transitions to SUCCESS or FAILED upon workflow completion
- **Error Message Cleanup**: When transitioning to SUCCESS, error messages are automatically cleared to ensure clean state
- **Retry Mechanism**: Failed emails can be retried using `retry_failed_email_workflow` task with force mode
- **Stuck Task Recovery**: The `schedule_reset_stuck_processing_emails` task automatically detects and marks stuck emails as FAILED
- **Force Mode**: Available for reprocessing emails regardless of current status (useful for debugging and manual reprocessing)
- **Internal Workflow State**: Detailed step-by-step progress is managed by LangGraph internal state with Redis checkpointing, not stored in the database
- **Error Tracking**: Node-level error tracking allows granular debugging and recovery strategies

### Error Handling

- **Node-level Error Tracking**: Each node in the workflow tracks its own errors in the state's `node_errors` field
- **Graceful Degradation**: Workflow continues even if non-critical nodes fail, with errors logged for later review
- **Automatic Recovery**: Redis checkpointing allows workflow resumption from the last successful checkpoint
- **Timeout Protection**: Stuck emails are automatically marked as FAILED after configurable timeout (default: 30 minutes)
- **Status Validation**: Each state transition is validated against the state machine rules to prevent invalid states
- **Force Processing**: Bypass status checks and reprocess emails using `retry_failed_email_workflow` task
- **Detailed Logging**: Comprehensive logging at each workflow node for debugging and monitoring

> **Best Practice:**
> Always keep your prompt templates, periodic task names, and state machine logic in sync with the codebase. If you add new settings or change the structure of any config, update the README accordingly.

## Reference
The foundational framework of this project is based on the
[django-starter-template](https://github.com/xiaoquqi/django-starter-template)
project, which provides a robust and modular Django REST API structure.

Core features of this project leverage components from the
[devtoolbox](https://github.com/cloud2ai/devtoolbox) project, including:

- **LLM Service**: For AI-powered content summarization and processing.
- **OCR Service**: For document and image text extraction.
- **JIRA Clients**: For seamless integration and automation with JIRA.

For more details on the architecture and advanced usage, please refer to the
above repositories.

## LangGraph Workflow Architecture

The email processing workflow is built on **LangGraph**, using a StateGraph pattern with 7 specialized nodes:

### Workflow Nodes

```
START → WorkflowPrepare → OCR → LLMAttachment → LLMEmail → Summary → Issue → WorkflowFinalize → END
```

| Node | Responsibility | Database Access |
|------|----------------|-----------------|
| **WorkflowPrepareNode** | Load email data, attachments, and user configurations into State | Read-only |
| **OCRNode** | Process image attachments and extract text using Azure Document Intelligence | No database access |
| **LLMAttachmentNode** | Process OCR content with LLM to organize and structure text | No database access |
| **LLMEmailNode** | Process email content with LLM, merge with attachment OCR content | No database access |
| **SummaryNode** | Generate comprehensive summary and title for issue creation | No database access |
| **IssueNode** | Create issue in external systems (JIRA) via API | No database access |
| **WorkflowFinalizeNode** | Atomically sync all results to database and update status | Write-only |

### Key Architecture Principles

1. **Prepare/Finalize Pattern**: Only the first and last nodes access the database
   - **Prepare**: Loads all necessary data into State (single read transaction)
   - **Finalize**: Saves all results to database (single write transaction)
   - **Middle nodes**: Pure business logic, operate only on State

2. **State-Driven Design**: All data flows through the `EmailState` TypedDict
   - Type-safe state structure
   - Immutable state updates (functional programming style)
   - Node-level error tracking in `node_errors` field

3. **Error Resilience**:
   - Each node tracks its own errors without stopping the workflow
   - Graceful degradation: non-critical failures don't block the entire process
   - Redis checkpointing enables workflow resumption from any point

4. **Atomic Database Operations**:
   - All database writes happen in a single transaction in WorkflowFinalizeNode
   - Either all changes are saved or none (ACID compliance)
   - Prevents partial updates and data inconsistency

### File Structure

```
threadline/
├── agents/
│   ├── workflow.py                 # LangGraph workflow definition
│   ├── email_state.py              # State structure and helper functions
│   ├── checkpoint_manager.py       # Redis checkpoint management
│   └── nodes/
│       ├── base_node.py            # Base class for all nodes
│       ├── workflow_prepare.py     # Data loading node
│       ├── workflow_finalize.py    # Data persistence node
│       ├── ocr_node.py             # OCR processing
│       ├── llm_attachment_node.py  # LLM for attachments
│       ├── llm_email_node.py       # LLM for email content
│       ├── summary_node.py         # Summary generation
│       └── issue_node.py           # Issue creation
└── tasks/
    ├── email_workflow.py           # Celery task wrapper for workflow
    ├── email_fetch.py              # Email fetching tasks
    ├── cleanup.py                  # Cleanup tasks
    └── scheduler.py                # Periodic task schedulers
```

## Threadline Processing Flow

```mermaid
flowchart TD
    A[Input Sources] --> B[Email Collection]
    B --> C[Email Processing]
    C --> D{Has Attachments?}

    D -->|Yes| E[Extract Images]
    D -->|No| F[Process Text Content]

    E --> G[OCR Processing]
    G --> H[OCR Content Extraction]

    F --> I[Text Content Organization]
    H --> I

    I --> J[LLM Email Processing]
    J --> K[LLM Summary Processing]
    K --> L[Content Summarization & Title Generation]

    L --> M{Issue Creation Enabled?}
    M -->|Yes| N[JIRA Issue Creation]
    M -->|No| O[Mark as Completed]

    N --> P[Upload Attachments to JIRA]
    P --> Q[JIRA Issue Complete]
    Q --> R[Mark as Completed]

    style A fill:#e1f5fe
    style R fill:#c8e6c9
    style G fill:#fff3e0
    style J fill:#f3e5f5
    style K fill:#e8f5e8
```

### Process Description

1. **Input Sources**: Various communication tools (WeChat, Slack, Teams, etc.) or direct emails
2. **Email Collection**: System fetches emails from configured mailboxes (IMAP/Haraka)
3. **Workflow Trigger**: Each email triggers a LangGraph workflow execution
4. **Data Preparation**: WorkflowPrepareNode loads email data, attachments, and user configs into State
5. **OCR Processing**: OCRNode extracts text from image attachments using Azure Document Intelligence
6. **LLM Attachment Processing**: LLMAttachmentNode processes OCR content with LLM for structure and clarity
7. **LLM Email Processing**: LLMEmailNode processes email text, merges with attachment OCR content
8. **Summary Generation**: SummaryNode generates comprehensive summary and title for issue creation
9. **Issue Creation**: IssueNode creates JIRA issue with organized content (if enabled)
10. **Data Persistence**: WorkflowFinalizeNode atomically saves all results to database
11. **Status Update**: Email status automatically set to SUCCESS or FAILED based on workflow result

### Key Features

- **Multi-source Input**: Supports various communication platforms via email forwarding
- **Image Processing**: Automatic OCR extraction from screenshots and documents
- **Three-stage LLM Processing**:
  - Stage 1: Organize attachment OCR content
  - Stage 2: Process and structure email content
  - Stage 3: Generate comprehensive summary and title
- **Automated Issue Creation**: Direct integration with JIRA and other issue tracking systems
- **Attachment Handling**: Preserves and uploads original files to JIRA issues
- **Stateful Workflow**: LangGraph manages internal state with Redis checkpointing for recovery
- **Atomic Database Operations**: All database writes happen in a single transaction for data consistency
- **Error Resilience**: Node-level error tracking allows the workflow to continue despite non-critical failures
- **Force Mode**: Reprocess emails regardless of current status for debugging and manual intervention
