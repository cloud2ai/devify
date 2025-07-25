# About Devify

## What is Devify?

### Purpose

Devify is an **AI-driven development platform** created to accelerate R&D workflows and address pain points that traditionally require significant manual effort. The project was initiated to meet internal demands for smarter, more efficient development processes.

### Vision

By integrating advanced AI technologies, Devify aims to:
- Automate repetitive and time-consuming tasks in the development lifecycle
- Reduce manual workload for engineering teams
- Enable faster and more reliable delivery of features and fixes

### Key Features

- **Jirabot Core Feature:** Automatically converts WeChat chat records into JIRA issues, streamlining the process of requirements collection and task creation for development teams.

#### Jirabot AI Agent

Jirabot AI Agent was born out of a common pain point in daily project
management: many issues and solutions are discussed and resolved
within WeChat groups, but this valuable knowledge is often lost
because it is not systematically captured in the product knowledge
base. Since WeChat does not provide a direct API to access all
conversation content, and relying solely on delivery personnel to
manually document these discussions is unreliable, we sought an
alternative approach.

Our solution leverages the fact that WeChat allows users to forward
chat records via email. By simply sending relevant chat logs to a
designated internal mailbox, we can then utilize large language
models and image recognition technologies to process the content.
After appropriate analysis and summarization, the processed
information is automatically submitted to JIRA, enabling the
initial accumulation of project knowledge with minimal manual
intervention.

In fact, this approach is not limited to WeChat chat records.
It can be extended to many other scenarios as well. In the future,
we will continue to broaden the boundaries of this model.

### Technical Overview

This project is built on standard Django and Celery asynchronous
task frameworks, leveraging AI capabilities such as Azure OpenAI
and OCR services. All essential configuration can be managed
directly through the Django Admin Portal; currently, no additional
user-facing UI is provided. Future releases will gradually introduce
more user interfaces and enhanced configuration options.

## How to run Devify?

Devify supports both development and production environments using
Docker. Please note the following differences:

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

### Environment Preparation

This step is required for both development and production environments.

```
cp env.sample .env
```

This environment values should be provided:

```
# Common Settings for MySQL Database
MYSQL_ROOT_PASSWORD=root_password
MYSQL_PORT=3306
MYSQL_USER=devify
MYSQL_PASSWORD=devifyPass
MYSQL_DATABASE=devify

# Celery
CELERY_BROKER_URL=redis://redis:6379
CELERY_RESULT_BACKEND=redis://redis:6379

AZURE_OPENAI_API_BASE=https://your-azure-openai-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_DEPLOYMENT=your-azure-openai-deployment
AZURE_OPENAI_API_VERSION=your-azure-openai-api-version

# OCR
AZURE_DOCUMENT_INTELLIGENCE_KEY="your-azure-document-intelligence-key"
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://your-azure-document-intelligence-endpoint.cognitiveservices.azure.com/"
```

### Run in Development Mode

```
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up -d
```

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

### Settings

Before using Jirabot features, you should initialize the required settings for all users. This can be done via a management command inside the API container. The command will automatically create default records for all necessary JIRABOT settings (`email_config`, `email_filter_config`, `jira_config`, `prompt_config`) for each user if they do not already exist.

To simplify configuration, all required settings should be added here. Below are the key-value pairs you need to set before using the system. The table describes the key design, and the values should be saved in JSON format.

| Key                  | Description                                                      | Required | Example Key Fields/Notes                |
|----------------------|------------------------------------------------------------------|----------|-----------------------------------------|
| email_config         | Email server connection and authentication settings               | Yes      | See below                              |
| email_filter_config  | Email filtering and processing rules                              | Yes      | See below                              |
| jira_config          | JIRA integration and default issue creation settings              | Yes      | See below                              |
| prompt_config        | AI prompt templates for email/attachment/summary processing       | Yes      | See below                              |

> **Note:**
> All values must be valid JSON.
> If you add new fields to the models or settings, update this table accordingly.

**How to initialize JIRABOT settings:**

1. **Enter the API container:**

   ```bash
   docker exec -it devify-api python manager.py init_jirabot_settings --user admin
   ```

**Note:**
- The initialization command is idempotent and safe to run multiple times.
- All values are stored in JSON format and should be customized according to your actual email, JIRA, and AI integration requirements.

2. **Edit the settings in Django Admin:**

   After initialization, log in to the Django Admin panel and navigate to the **Settings** section. You can then edit the values for each key (`email_config`, `email_filter_config`, `jira_config`, `prompt_config`) as needed for your environment.

   > **Tip:**
   > You can also update these settings directly in the database if required.

3. **Log in to Django Admin**
   - Visit [http://localhost:8000/admin](http://localhost:8000/admin) in your browser.
   - Log in with your admin credentials.
   - Username: admin
   - Password: adminpassword

4. **Navigate to the Settings Model**
   - In the sidebar, find and click on **Settings** under JIRABOT

#### Email Configuration(email_config)

| Key               | Type     | Description                                 | Example                        |
|-------------------|----------|---------------------------------------------|--------------------------------|
| host              | string   | SMTP server hostname                        | "smtp.feishu.cn"               |
| imap_host         | string   | IMAP server hostname                        | "imap.feishu.cn"               |
| smtp_ssl_port     | integer  | SMTP SSL port (default: 465)                | 465                            |
| smtp_starttls_port| integer  | SMTP StartTLS port (default: 587)           | 587                            |
| imap_ssl_port     | integer  | IMAP SSL port (default: 993)                | 993                            |
| username          | string   | Email username                              | "your-email@domain.com"        |
| password          | string   | Email password                              | "your-email-password"          |
| use_ssl           | boolean  | Enable SSL                                  | true                           |
| use_starttls      | boolean  | Enable StartTLS                             | false                          |

```
{
  "imap_host": "your-imap-server-hostname",
  "smtp_ssl_port": 465,
  "smtp_starttls_port": 587,
  "imap_ssl_port": 993,
  "username": "your-email-username",
  "password": "your-email-password",
  "use_ssl": true,
  "use_starttls": false
}
```

#### Email Filter Config(email_filter_config)

| Key              | Type     | Description                                                        | Example                |
|------------------|----------|--------------------------------------------------------------------|------------------------|
| folder           | string   | The email folder to fetch messages from, usually "INBOX"           | "INBOX"                |
| filters          | array    | List of IMAP search criteria to apply when fetching emails         | ["UNSEEN", "SINCE \"24-Jul-2025\""] |
| exclude_patterns | array    | Patterns to exclude emails, e.g., subjects containing keywords     | ["spam", "newsletter"] |
| max_age_days     | integer  | Maximum age of emails to process, in days                          | 7                      |

**Available IMAP Search Criteria for `filters` array:**

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

**Example configuration:**

```json
{
  "folder": "INBOX",
  "filters": [
    "UNSEEN",
    "SINCE \"24-Jul-2025\"",
    "FROM \"admin@example.com\""
  ],
  "exclude_patterns": [
    "spam",
    "newsletter"
  ],
  "max_age_days": 7
}
```

**Note:**
- The `filters` array can contain multiple IMAP search criteria (combined with AND logic)
- Date format should be "DD-MMM-YYYY" (e.g., "24-Jul-2025")
- The system automatically adds time-based filtering using `last_email_fetch_time` for incremental fetching

### JIRA Config(jira_config)

| Key                | Type     | Description                                      | Example                      |
|--------------------|----------|--------------------------------------------------|------------------------------|
| url                | string   | JIRA server URL                                  | "https://jira.example.com"   |
| username           | string   | JIRA account username                            | "jira-user"                  |
| api_token          | string   | JIRA API token or password                       | "your-api-token"             |
| project_key        | string   | JIRA project key                                 | "PRJ"                        |
| default_issue_type | string   | Default issue type for new issues                | "Task"                       |
| default_priority   | string   | Default priority for new issues                  | "High"                       |
| epic_link          | string   | Epic link key (optional)                         | "PRJ-1234"                   |
| assignee           | string   | Default assignee username (optional)             | "jira-assignee"              |

```
{
  "url": "your-jira-url",
  "username": "your-jira-username",
  "api_token": "your-api-token-or-password",
  "project_key": "your-project-key",
  "default_issue_type": "your-default-issue-type",
  "default_priority": "your-default-priority",
  "epic_link": "your-epic-link-key",
  "assignee": "your-assignee-username"
}
```

## Prompt Config (prompt_config)

| Config Key              | Description                                                                                   | Required |
|------------------------|-----------------------------------------------------------------------------------------------|----------|
| `email_content_prompt` | Organizes email/chat content for LLM processing.                                              | Yes      |
| `ocr_prompt`           | Processes OCR text from images for LLM summarization.                                         | Yes      |
| `summary_prompt`       | Summarizes email and attachment content for JIRA issue creation.                              | Yes      |
| `summary_title_prompt` | Generates a structured and concise JIRA issue title.                                          | Yes      |

**Example:**
```json
{
  "email_content_prompt": "Sort chat logs in chronological order (oldest to newest). Format each message as: [Time] [Sender]: Message Content. Place each image on a separate line using markup (e.g., !image-filename.png!). Keep the original time, sender, and content. Supplement semantics if necessary, but do not change the original meaning.",
  "ocr_prompt": "Extract key information from raw OCR text, remove irrelevant or redundant content, supplement semantics, and organize it into a concise and complete description. Highlight operational context, abnormal phenomena, and error messages to help locate and document issues.",
  "summary_prompt": "Based on chat logs, background information, user feedback, and screenshots, clarify task responsibilities, determine where the issue occurred, and perform issue classification and analysis. Output three parts: (1) phenomenon description and preliminary cause analysis (including environment information, issue phenomenon, and reproduction process; reference screenshots and chat for completeness; clearly mark any assumptions), (2) TODO list of core issues and potential requirements (mark assumptions), (3) if the input contains '--- ATTACHMENT OCR CONTENT ---', analyze the OCR content, as it may contain key error messages or configuration information. If information is unclear, mark as 'To be confirmed' and strictly summarize based on the provided content.",
  "summary_title_prompt": "Summarize a clear and specific issue title based on the provided chat logs and background information. The title should directly reflect the main problem to be solved or the key requirement, using a concise verb-object structure. Avoid vague or generic terms. Focus on what needs to be addressed or resolved. Limit the title to 200 characters for clarity and easy identification."
}
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
> 1. **schedule_email_processing_tasks**
>    - This is the main scheduler task. It periodically polls the email/message status and triggers the appropriate processing tasks (such as OCR, LLM summarization, and JIRA submission) based on the current state machine.
>
> 2. **reset_stuck_processing_emails**
>    - This task is responsible for detecting and resetting any email/message tasks that have been stuck in a pending or processing state for too long (timeout recovery). It helps ensure the system can recover from unexpected failures or timeouts.
>
> Both tasks are essential for robust, automated email-to-JIRA processing. Make sure both are scheduled to run at appropriate intervals (e.g., every 5 minutes for the main scheduler, every 10-30 minutes for the stuck task reset).

## Required Periodic Tasks

You **must** configure the following periodic tasks in Django Admin (**Periodic Tasks** section, provided by `django-celery-beat`):

1. **schedule_scan_all_users_emails**
   - Periodically fetches new emails for all users with active email_config.
   - Triggers the scan and storage of new emails into the system, enabling downstream processing (OCR, LLM, JIRA, etc.).
   - **Recommended interval:** every 5 minutes.

2. **schedule_email_processing_tasks**
   - Main scheduler task. Periodically polls the status of all emails and triggers the appropriate processing tasks (OCR, LLM summarization, JIRA submission) based on the current state machine.
   - **Recommended interval:** every 5 minutes.

3. **reset_stuck_processing_emails**
   - Detects and resets any email/message tasks that have been stuck in a pending or processing state for too long (timeout recovery).
   - **Recommended interval:** every 10–30 minutes.

> **Tip:**
> You can edit, disable, or delete these tasks at any time in the **Periodic Tasks** section.

## EmailMessage State Machine & Exception Handling

- The `EmailMessage` model uses a single state field to track the processing stage:
  - `FETCHED`, `OCR_PROCESSING`, `OCR_SUCCESS`, `OCR_FAILED`, `SUMMARY_PROCESSING`, `SUMMARY_SUCCESS`, `SUMMARY_FAILED`, `JIRA_PROCESSING`, `JIRA_SUCCESS`, `JIRA_FAILED`
- Each processing task (OCR, LLM, JIRA) will only execute if the previous stage is successful.
- If any required content is missing (e.g., OCR result, LLM content), the task will raise an exception and set the status to `*_FAILED`.
- The scheduler will retry or reset failed/stuck tasks as needed.

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
