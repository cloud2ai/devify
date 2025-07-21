# Mito - Django Project Template Generator

Mito comes from the biological term "Mitosis" (cell division). Just as cells divide to create new life, Mito project template helps developers quickly create new Django applications. Each project created by Mito inherits carefully designed best practices while maintaining its own uniqueness.

> Like cell division, one perfect template can create countless excellent projects.

## Recent Updates (2025-07-20)

This update incorporates practical improvements from several production projects, focusing on developer experience and code maintainability.

### 🔧 **Major Improvements**

#### **1. Swagger Documentation Optimization**
- **Replaced legacy swagger modules** with `drf-spectacular` for better performance
- **Reduced views.py code complexity** by abstracting common swagger configurations
- **Implemented best practices** for handling large views.py files (see documentation in views.py headers)
- **Enhanced API documentation** with standardized response formats and detailed pagination structures

#### **2. Celery Development Workflow Enhancement**
- **Added custom management commands** for testing Celery tasks without starting workers
- **Implemented `show_time` command** with structured logging and debug controls
- **Improved development efficiency** by allowing synchronous task testing during development

#### **3. Docker Environment Optimization**
- **Optimized production and development Docker configurations**
- **Enhanced deployment workflows** for better development-to-production transitions
- **Improved container orchestration** for both development and production environments

#### **4. URL Structure Improvements**
- **Eliminated trailing slashes** in Django URLs for cleaner API endpoints
- **Updated auth module URLs** to follow consistent no-trailing-slash pattern
- **Improved URL consistency** across all API endpoints

### 🚀 **Developer Experience Enhancements**

- **Reduced boilerplate code** in views through swagger abstractions
- **Streamlined debugging process** with custom management commands
- **Better code organization** with improved project structure
- **Enhanced documentation** with comprehensive examples and usage patterns

### 📋 **Technical Details**

#### **Swagger Configuration (`core/swagger.py`)**
```python
# Before: Verbose inline swagger configurations
@extend_schema(
    responses={200: PostSerializer},
    parameters=[...],
    # ... many lines of configuration
)

# After: Clean, reusable configurations
@extend_schema(
    parameters=pagination_params() + [ordering_param()],
    responses={200: pagination_response(PostSerializer)}
)
```

#### **Management Commands**
```bash
# Test Celery tasks without starting workers
python manage.py show_time --debug

# Structured logging output
2025-07-20 02:56:43,737 - v1.sample.management.commands.show_time - INFO - Starting task
```

#### **URL Improvements**
```python
# Before: URLs with trailing slashes
path('api/v1/auth/login/', LoginView.as_view(), name='login'),

# After: Clean URLs without trailing slashes
path('api/v1/auth/login', LoginView.as_view(), name='login'),
```

### 🎯 **Impact on Development**

These updates significantly improve the development workflow by:
- **Reducing code complexity** in views and API documentation
- **Enabling faster debugging** of asynchronous tasks
- **Providing better deployment flexibility** with optimized Docker configurations
- **Creating cleaner API endpoints** with consistent URL patterns

## Why Choose Mito?

Mito is a foundational framework for building REST APIs and asynchronous
task execution based on Django. It is designed as a solid starting point
for developing AI applications, with Docker-based deployment optimized
for both development and production environments. The project philosophy
is "don't reinvent the wheel"—Mito integrates proven solutions wherever
possible, avoiding redundant development.

A key aspect of Mito's development is the extensive use of AI-assisted
tools such as Cursor for automated coding and testing. We encourage
developers to leverage AI in generating and maintaining their projects
with Mito, which can significantly boost productivity.

**🤖 AI-First Development Philosophy:**
- **Cursor Integration**: Optimized for AI-assisted development workflows
- **Code Generation**: Leverage AI for rapid prototyping and testing
- **Automated Testing**: AI-powered test generation and validation
- **Documentation**: AI-assisted documentation and code comments

## Design Philosophy

### Frontend-Backend Separation

- 🔄 **API-First Design**: Build standard RESTful APIs with Django REST framework
- 📚 **API Documentation**: Integrated Swagger UI for interactive API docs
- 🧹 **Code Simplification**: Abstracted common patterns to reduce boilerplate code

### Asynchronous Processing

- 🚀 **Celery Integration**: Handle time-consuming tasks and background jobs
- ⏰ **Scheduled Tasks**: Task scheduling with Celery Beat
- 📊 **Task Monitoring**: Visualize task execution status and results

### Developer Friendly

- 🛠 **Complete Toolchain**: Pre-configured development, testing and deployment tools
- 📦 **Dependency Management**: Strict dependency management with requirements.txt
- 🔧 **Environment Isolation**: Separate configs for development, testing and production

This architecture provides:

- Better scalability and maintainability
- Clear separation of concerns
- Flexible technology choices
- Powerful async processing capabilities

## Running in Production

The easiest way to get started is by using Docker Compose:

1. Clone the repository (you can rename the project to whatever you prefer, for instance, your_new_project):

   ```bash
   git clone https://github.com/xiaoquqi/django-starter-template.git your_new_project
   cd your_new_project
   ```

2. Copy the environment configuration file:

   ```bash
   cp .env.sample .env
   ```

> NOTE: How to Set CSRF_TRUSTED_ORIGINS
>
> - This setting defines the trusted domains for CSRF verification.
> - In a production environment, you must include the domain of your admin portal to ensure proper access.
>
> - Use a comma-separated list of trusted domains. For example:
>
>    ```bash
>    export CSRF_TRUSTED_ORIGINS=https://admin.example.com,https://api.example.com
>    ```

3. Start the services:

   **Scenario 1: Only API and Database Services**

   If your application only requires the API and database services without any asynchronous tasks or scheduled tasks, you can start the services as follows:

   ```bash
   docker-compose up -f docker-compose.prod.yaml -d mito-api mito-mariadb
   ```

   **Scenario 2: Full Services with Asynchronous and Scheduled Tasks**

   If your application requires all services including asynchronous tasks and scheduled tasks, you can start the services as follows:

   ```bash
   docker-compose up -f docker-compose.prod.yaml -d
   ```

4. Access the services:
   - Swagger API Documentation: http://localhost/swagger/
   - Admin Interface: http://localhost/admin/
       - Default username and password: admin/adminpassword
   - Flower(Celery Task Management): http://localhost:81/

### Containers

| Containers         | Description                                      |
|--------------------|--------------------------------------------------|
| mito-api           | The main Django application for handling requests and serving the API. |
| mito-worker        | A Celery worker for processing background tasks asynchronously. |
| mito-scheduler     | A Celery scheduler for managing periodic tasks.  |
| mito-nginx         | Nginx server for serving static files and acting as a reverse proxy. |
| mito-mariadb       | MariaDB database service for storing application data. |
| mito-redis         | Redis service for caching and message brokering. |
| mito-flower        | A web-based tool for monitoring and managing Celery tasks. |

## Developer Quick Guide

You can use this project as a foundation for developing new applications. I have created a simple starter app based on useful Django modules, and you are welcome to modify anything as you see fit. I will highlight the modifications to help you quickly set up a new project.

### Building the Development Environment

It is recommended to use an IDE with AI enhancements, such as VS Code with Copilot, Cursor, WindSurf, or any other tool you prefer. We are in the era of AI, so embrace it and become the master of AI.

1. Clone the repository (you can rename the project to anything you like, for example, your_new_project):

   ```bash
   git clone https://github.com/xiaoquqi/django-starter-template.git your_new_project
   cd your_new_project
   ```

   > NOTE: If you do not want to use the default project name `mito` and Django project name `api`, you can use the provided script in the project located at `tools/project_manager.sh` to replace them. Please refer to the documentation for more details on how to do this:[How to Change Project Name `Mito`?](#how-to-change-project-name-mito) and [How to Change Django Project Name `api`?](#how-to-change-django-project-name-api).

2. Create and activate a virtual environment:

   ```bash
   virtualenv venv
   source venv/bin/activate
   ```

3. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the database and create a superuser:

   ```bash
   export DJANGO_DEBUG=True

   python manage.py migrate

   # Create a superuser
   python manage.py createsuperuser --username admin --email admin@example.com
   # You will be prompted to enter a password
   ```

5. Start the Django Service:

When developing new APIs, you can skip starting Celery services and the database service, as Django defaults to using SQLite as its database.

   ```bash
   cd mito
   python manage.py runserver
   ```

6. (Optional) Start Celery Services:

To utilize Celery, ensure Redis is running before starting Celery. You can use the existing Docker Compose file to start Redis as follows:

   ```bash
   docker-compose -f docker-compose.dev.yaml up redis -d
   ```

Subsequently, you can start all Celery services.

   ```bash
   celery -A core worker --loglevel debug
   celery -A core beat --loglevel debug
   ```

7. Access the services:
   - Swagger API Documentation: http://localhost:18080/swagger/
   - Admin Interface: http://localhost:18080/admin/
       - Default username and password: admin/adminpassword
   - Flower(Celery Task Management): http://localhost:18081/

## Django Code Structure

All the Django code is located in the mito directory, which is generated by the django-admin startproject command. Therefore, all backend development is conducted within this directory.

### Django Project Structure

```
mito                         // The main application directory containing all project-related files.
├── accounts                 // Directory for user account management and authentication.
├── core                     // Django project directory, contains all settings.
│   ├── asgi.py              // ASGI configuration for asynchronous support.
│   ├── celery.py            // Configuration for Celery task management.
│   ├── __init__.py          // Initializes the core package.
│   ├── settings             // Directory containing various settings for the application.
│   │   ├── base.py          // Base settings for the Django project.
│   │   ├── celery.py        // Celery-specific settings.
│   │   ├── constants.py     // Global variables and constants.
│   │   ├── __init__.py      // Initializes the settings package.
│   │   ├── logging_config.py // Configuration for logging in the application.
│   │   ├── rest.py          // Settings specific to Django REST framework.
│   │   └── swagger.py       // Configuration for Swagger API documentation.
│   ├── swagger.py           // Main Swagger configuration for the application.
│   ├── urls.py              // URL routing for the core application.
│   └── wsgi.py              // WSGI configuration for serving the application.
├── docker                   // Directory for Docker-related files.
├── Dockerfile               // Instructions for building the Docker image.
├── locale                   // Directory for localization files.
├── manage.py                // Command-line utility for managing the Django project.
├── tests                    // Directory containing test cases for the application.
└── v1                       // Version 1 of the API.
    └── sample               // Sample Django application
        ├── management       // Management commands for the sample app
        │   └── commands     // Custom Django management commands
        │       └── show_time.py // Command to test Celery tasks
```

### Django Project Settings

This project is slightly different from a standard Django project. I have split the settings into several parts, allowing you to add or modify options based on your requirements.

#### How to add a new setting?

If you want to add configurations that may change depending on the environment, it is recommended to use environment variables. I have already set up automatic loading of the .env file located in the project's base directory. You can copy the .env.sample file to .env before starting development.

To add new environment variables in a Django project and configure them at startup, follow these steps:

1. Update the `.env.sample` File

First, define the new environment variable in the `.env.sample` file. For example, if you want to add a variable named `NEW_VARIABLE`, you can do it like this:

2. Load the new environment variable in base.py: Next, you need to load this new environment variable in the mito/core/settings/base.py file. You can use the os.getenv() function to retrieve the value of this variable.

``` python
# ... existing code ...

# New environment variable
NEW_VARIABLE = os.getenv("NEW_VARIABLE", "default_value")  # Set default value

# ... existing code ...
```

For settings or static variables unrelated to Django but related to the code, it is recommended to add them to the core/settings/constants.py file.

3. Use the new environment variable in the code: Now, you can use this new environment variable in other parts of the project. For example, you can use it in views, models, or other settings.

``` python
from django.http import JsonResponse
from django.conf import settings

def example_view(request):
    # Use your new environment here
    new_variable_value = settings.NEW_VARIABLE
    return JsonResponse({"new_variable": new_variable_value})
```

4. Ensure that the .env file is loaded at startup: Make sure to load the .env file when the project starts so that the new environment variables can be read correctly. You have already used load_dotenv(ENV_DIR) in base.py to load the environment variables, ensuring that the new variables are read at startup.

By following these steps, you can successfully add new environment variables and use them in your Django project.

## Authentication

### JWT

In this project, JWT (JSON Web Token) is used as the default authentication method. JWT allows you to securely transmit information between parties as a JSON object.

#### How to use JWT?

1. **Normal Authentication**: To authenticate a user, send a POST request to the `/api/v1/auth/token/` endpoint with the user's credentials (username and password). If the credentials are valid, you will receive an access token and a refresh token.

   Example request:

   ```http
   POST /api/v1/auth/token/
   Content-Type: application/json

   {
       "username": "your_username",
       "password": "your_password"
   }
   ```

   Example response:

   ```json
   {
       "access": "your_access_token",
       "refresh": "your_refresh_token"
   }
   ```

2. **Refreshing the Token**: When the access token expires, you can obtain a new access token by sending a POST request to the `/api/v1/token/refresh/` endpoint with the refresh token.

   Example request:

   ```http
   POST /api/v1/token/refresh/
   Content-Type: application/json

   {
       "refresh": "your_refresh_token"
   }
   ```

   Example response:
   ```json
   {
       "access": "your_new_access_token"
   }
   ```

By following these steps, you can effectively use JWT for authentication and token management in this project.

### About `accounts`

By default, all user authentication and authorization operations should be placed in the accounts directory. The accounts directory contains a standard Django application that implements a profile, establishing a one-to-one relationship with the default Django user module to extend user capabilities. Here is the structure of the accounts directory.

```
api
├── accounts
│   ├── admin.py
│   ├── apps.py
│   ├── __init__.py
│   ├── migrations
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
│   └── views.py
```

## API Documentation

### Swagger Configuration

This project includes a comprehensive Swagger configuration system that provides:

- **Standardized Response Format**: All API responses follow a consistent format with `code`, `message`, and `data` fields
- **Detailed Pagination Documentation**: Complete pagination structure with `total`, `page`, `pageSize`, `next`, and `previous` fields
- **Reusable Parameters**: Common parameters like pagination, ordering, and search are abstracted into reusable functions
- **Dynamic Schema Generation**: Uses dynamic class creation to avoid naming conflicts while maintaining detailed schema structure

**Usage Examples:**

```python
# Standard response
@extend_schema(responses={200: response(PostSerializer)})

# List response
@extend_schema(responses={200: list_response(TagSerializer)})

# Paginated response with parameters
@extend_schema(
    parameters=pagination_params() + [ordering_param()],
    responses={200: pagination_response(PostSerializer)}
)
```

**Available Functions:**

- `response(serializer)`: Creates standard response wrapper for single objects
- `list_response(serializer)`: Creates response wrapper for list endpoints
- `pagination_response(serializer)`: Creates detailed pagination response
- `pagination_params()`: Returns standard pagination parameters
- `ordering_param(default="created_at")`: Returns ordering parameter
- `search_param()`: Returns search parameter

### API Response Format

To make compatible with the frontend, the API response format is as follows:

```json
{
    "data": {
        "...": "..."
    },
    "code": 0
}
```

In frontend, the code is 0, which means success. If the code is not 0, it means an error occurred. You can make customization error code in the API response. A good best practice is to define different error codes for different types of errors.

So a middleware is added to the Django project to convert the response to the format above. The middleware is enabled by default, but you can disable `core.settings.middlewares.AxiosResponseMiddleware` by removing the middleware from the MIDDLEWARE list in the base.py file.

## Django Application

### Why We Have a v1 Directory

In actual development, as features continue to iterate and update, the API interfaces will also change with the increasing demands. Therefore, we have added a v1 directory in the app to accommodate the needs for future version development and iteration. This structure allows us to manage different versions of the API effectively, ensuring backward compatibility while enabling the introduction of new features and improvements in subsequent versions.

### Sample Application

In the `mito/v1/sample` directory, you will find a complete example of a Django application that implements a blogging system.

This sample application contains a simple blog data structure, including posts, tags, and categories. Posts and tags have a many-to-many relationship, while posts and categories have a one-to-many relationship. You can also create a new post with new tags and categories, and the overridden create method will function in the serializers.py file. You can use this application as a sample and develop new applications according to your requirements.

You can test the interface on the Swagger page and find more details in the code.

### Create a new App

To create a new app under the `v1` directory in your Django project, follow these steps:

1. Open your terminal and navigate to the root directory of your Django project.

2. Run the following command to create a new app (replace `your_new_app` with the desired app name):

   ```bash
   python manage.py startapp v1/your_new_app
   ```

3. After the app is created, you will need to add it to your project's settings. Open `mito/core/settings/base.py` and add the new app to the `INSTALLED_APPS` list:

   ```python
   INSTALLED_APPS = [
       ...
       'v1.your_new_app',
       ...
   ]
   ```

4. Now, you can start defining your models, views, and serializers in the newly created app directory (`v1/your_new_app`).

5. Don't forget to create migrations for your models and apply them:

   ```bash
   python manage.py makemigrations v1/your_new_app
   python manage.py migrate
   ```

6. Finally, you can start developing your API endpoints in the `views.py` file of your new app.

By following these steps, you can effectively create and set up a new app under the `v1` directory in your Django project.

## Management Commands

### Custom Management Commands

This project includes custom Django management commands to help with development and testing. These commands are located in the `v1/sample/management/commands/` directory.

#### show_time Command

The `show_time` command allows you to test Celery tasks without starting a Celery worker. This is particularly useful for development and debugging purposes.

**Usage:**

```bash
# Basic usage - show current time
python manage.py show_time

# Enable debug logging
python manage.py show_time --debug

# Enable verbose output (backward compatibility)
python manage.py show_time --verbose

# View help
python manage.py show_time --help
```

**Features:**

- **Structured Logging**: Uses Python's standard logging module with configurable levels
- **Debug Control**: `--debug` flag enables detailed logging output
- **Backward Compatibility**: `--verbose` flag maintains compatibility with older scripts
- **Error Handling**: Comprehensive error handling with clear error messages
- **Transaction Safety**: Uses database transactions for data consistency

**Example Output:**

```
2025-07-20 02:56:43,737 - v1.sample.management.commands.show_time - INFO - Info logging enabled
2025-07-20 02:56:43,737 - v1.sample.management.commands.show_time - INFO - Starting show_current_time task
2025-07-20 02:56:43,738 - v1.sample.management.commands.show_time - INFO - Running show_current_time task...
2025-07-20 02:56:43,748 v1.sample.tasks INFO     Current time: 2025-07-20 02:56:43.748130
2025-07-20 02:56:43,748 - v1.sample.management.commands.show_time - INFO - Show current time task completed successfully!
```

**Creating Custom Commands:**

To create your own management commands, follow this structure:

```
v1/your_app/management/
├── __init__.py
└── commands/
    ├── __init__.py
    └── your_command.py
```

Example command structure:

```python
from django.core.management.base import BaseCommand
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Description of your command'

    def add_arguments(self, parser):
        parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    def handle(self, *args, **options):
        logger.info('Starting your command...')
        # Your command logic here
        logger.info('Command completed successfully!')
```

## Project Customization

### How to Change Project Name `Mito`?

You can change the project name from `Mito` to a name of your choice if you prefer a different one. The only impact of changing the project name occurs after installation; the package name will be updated to your new name, and all related references will also be modified. For instance, the production Docker name will become NewName-api. If this is your intention, please follow the instructions provided.

``` bash
cd tools
./project_manager.sh --project-name myproject --dry-run
./project_manager.sh --project-name myproject
```

### How to Change Django Project Name `api`?

After installing this package, the project name will be `mito-xxx` and the package name will be `api`. You can freely change the package name since it only affects the installation path and has no impact on Django's runtime functionality. To rename the `api` package to a different name, please use the provided script.

``` bash
cd tools
./project_manager.sh --django-project-name myapi --dry-run
./project_manager.sh --django-project-name myapi
```

## Project Modules

This list contains the modules that already exist in this project.

| Module Name                        | Description                                                                                     |
|------------------------------------|-------------------------------------------------------------------------------------------------|
| Django                             | The core framework for building web applications.                                              |
| Django REST framework              | A framework for building RESTful APIs.                                                         |
| djangorestframework_simplejwt      | Extension for JWT authentication support in Django REST framework.                             |
| djangorestframework-camel-case     | Provides JSON renderers and parsers that convert between camelCase and snake_case.            |
| dj-rest-auth                       | Extension for user authentication and registration.                                            |
| drf-spectacular                    | Tool for generating OpenAPI 3.0 documentation for APIs.                                       |
| dj-rest-auth[with_social]         | DJ-REST-AUTH extension with social authentication support.                                     |
| python-dotenv                      | Library for loading environment variables from .env files.                                     |
| dj_database_url                    | Library for parsing database URLs.                                                             |
| celery                             | Framework for asynchronous task queues.                                                         |
| django-celery-beat                | Extension for scheduling periodic tasks in Django.                                             |
| flower                             | Tool for real-time monitoring of Celery tasks.                                                |
| gunicorn                           | WSGI server for running the application in production.                                         |

## Version History

### v2.0.0 (2025-07-20) - Major Refactoring

**🎯 Focus:** Developer Experience & Code Maintainability

#### **Breaking Changes**
- Replaced legacy swagger modules with `drf-spectacular`
- Updated URL patterns to remove trailing slashes
- Restructured project directory from `api/` to `mito/`

#### **New Features**
- **Custom Management Commands**: Added `show_time` command for Celery task testing
- **Enhanced Swagger Configuration**: Abstracted common patterns into reusable functions
- **Improved Logging**: Structured logging with debug controls in management commands
- **Optimized Docker**: Enhanced production and development configurations

#### **Improvements**
- **Code Reduction**: Significantly reduced boilerplate in views.py
- **Better Documentation**: Comprehensive API documentation with standardized formats
- **Development Workflow**: Streamlined debugging and testing processes
- **URL Consistency**: Cleaner API endpoints without trailing slashes

#### **Technical Enhancements**
- **Swagger Abstractions**: `response()`, `list_response()`, `pagination_response()` functions
- **Parameter Reusability**: `pagination_params()`, `ordering_param()`, `search_param()`
- **Management Commands**: Structured logging with `--debug` and `--verbose` options
- **Docker Optimization**: Improved container orchestration for both environments

### v1.0.0 (Initial Release)
- Basic Django REST API template
- JWT authentication system
- Celery integration for async tasks
- Docker containerization
- Swagger UI integration
