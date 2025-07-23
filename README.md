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

Before using this project to enhance your development with AI, you need to pre-configure certain settings at the database level. You can complete these configurations through the Django Admin page.

1. **Log in to Django Admin**
   - Visit [http://localhost:8000/admin](http://localhost:8000/admin) in your browser.
   - Log in with your admin credentials.
   - Username: admin
   - Password: adminpassword

2. **Navigate to the Settings Model**
   - In the sidebar, find and click on **Settings** under JIRABOT

To simplify configuration, all required settings should be added here. Below are the key-value pairs you need to set before using the system. The table describes the key design, and the values should be saved in JSON format.

| Key                  | Description                                                      |
|----------------------|------------------------------------------------------------------|
| email_config         | Email server connection and authentication settings               |
| email_filter_config  | Email filtering and processing rules                              |
| jira_config          | JIRA integration and default issue creation settings              |
| prompt_config        | AI prompt templates for email/attachment/summary processing       |

Please refer to the detailed sections below for the required fields and example values for each setting.

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
| filters          | array    | List of filter rules to apply when fetching emails                 | []                     |
| exclude_patterns | array    | Patterns to exclude emails, e.g., subjects containing keywords     | ["spam", "newsletter"] |
| max_age_days     | integer  | Maximum age of emails to process, in days                          | 7                      |

```

{
  "filters": [],
  "exclude_patterns": [
    "spam",
    "newsletter"
  ],
  "max_age_days": 7
}
```

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
  "username": "your-jira-username",
  "api_token": "your-api-token-or-password",
  "project_key": "your-project-key",
  "default_issue_type": "your-default-issue-type",
  "default_priority": "your-default-priority",
  "epic_link": "your-epic-link-key",
  "assignee": "your-assignee-username"
}
```

#### Prompt Config(prompt_config)

| Config Key              | Description                                                                                   |
|------------------------|-----------------------------------------------------------------------------------------------|
| `email_content_prompt` | Organizes email content (such as chat logs) in chronological order and formats messages and images for further processing. |
| `ocr_prompt`           | Processes OCR text from images, extracts key information, and summarizes relevant context and issues. |
| `summary_prompt`       | Summarizes email content for JIRA, including main issues, analysis, and action items, with attention to OCR content if present. |
| `summary_title_prompt` | Generates a structured and concise JIRA issue title following the required format, highlighting the core issue or requirement. |

Below are the English versions of the prompts:

```
{
  "email_content_prompt": "Sort the chat logs in chronological order (oldest to newest). Format each message as: [Time] [Sender]: Message Content. Place each image on a separate line using JIRA markup (e.g., !image-filename.png!). Preserve the original time, nickname, and content. Supplement semantics if necessary, but do not alter the original meaning.",
  "ocr_prompt": "Extract key information from the raw OCR text, remove irrelevant or redundant content, supplement semantics, and organize it into a concise and complete description. Highlight operational context, abnormal phenomena, and error messages to facilitate issue localization and documentation.",
  "summary_prompt": "You are a professional product manager for HyperBDR (Disaster Recovery) and HyperMotion (Migration). Based on the chat logs, background information, user feedback, and screenshots, clarify task ownership (migration or disaster recovery), identify source and target platforms, determine where the issue occurred (client, control, or target), and perform issue classification and analysis. Output three parts: (1) phenomenon description and preliminary cause analysis (including environment info, issue phenomenon, and reproduction process, referencing screenshots and chat for completeness; mark any assumptions clearly), (2) TODO list of core issues and potential requirements (mark assumptions), (3) if the input contains '--- ATTACHMENT OCR CONTENT ---', be sure to analyze the OCR content, as it may contain key error messages or configuration info. If information is unclear, mark as 'To be confirmed' and strictly summarize based on the provided content.",
  "summary_title_prompt": "Based on the following chat logs and background information, extract a structured and concise JIRA issue title. Strictly follow this format and keep the structure consistent, with each field enclosed in square brackets [] in the following order: [Project Name][Source/Target][Scenario Type][Issue Category] Title Content. Field explanations: - [Project Name]: Identify from chat or group name, usually at the beginning; - [Source/Target]: Format as 'Source Platform/Target Platform', e.g., 'VMware/Huawei Cloud', extract from background or user description; - [Scenario Type]: Determine if 'Migration' or 'Disaster Recovery', if unclear, use 'Scenario Unclear'; - [Issue Category]: Determine if the issue is mainly on 'Source', 'Target', or 'Control', if unclear, mark as 'To be confirmed'; - Title Content: Use a concise verb-object structure to state the core issue or requirement, e.g., 'Restore Failed', 'Validation Stuck', 'Task Unresponsive', 'Need to Support Log Download', avoid vague expressions. Requirements: 1. All fields must be present and structured (if unclear, keep the field and fill with 'To be confirmed'); 2. Title content must be concise and use a clear verb-object structure; 3. No more than 200 characters for easy creation, identification, and retrieval in JIRA; 4. Accurately reflect the core issue or requirement, avoid generic terms like 'Experience Optimization' or 'Feedback'."
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
>    - This is the main scheduler task. It periodically polls the email/message status and triggers the appropriate processing tasks (such as OCR, LLM summarization, and JIRA submission) based on the current state.
>
> 2. **reset_stuck_processing_email**
>    - This task is responsible for detecting and resetting any email/message tasks that have been stuck in a pending or processing state for too long (timeout recovery). It helps ensure the system can recover from unexpected failures or timeouts.
>
> Both tasks are essential for robust, automated email-to-JIRA processing. Make sure both are scheduled to run at appropriate intervals (e.g., every 5 minutes for the main scheduler, every 10-30 minutes for the stuck task reset).

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
