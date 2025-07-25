"""
Database configuration module for Django project.

This module dynamically constructs the DATABASE_URL from environment variables.

Rationale:
    - Environment variables (.env, docker-compose) do not support variable
      interpolation or string concatenation for complex database URLs.
    - Manually composing the DATABASE_URL in Django config ensures:
        1. All DB parameters can be set as simple env variables.
        2. No need for awkward string concatenation in docker-compose.
        3. The logic is centralized, explicit, and easy to maintain.
        4. Supports switching DB engines (mysql, postgresql, sqlite) elegantly.
"""
import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Read environment variables for database configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    db_engine = os.getenv('DB_ENGINE', 'sqlite')

    if db_engine == 'mysql':
        db_user = os.getenv('MYSQL_USER', 'root')
        db_password = os.getenv('MYSQL_PASSWORD', '')
        db_host = os.getenv('MYSQL_HOST', 'localhost')
        db_port = os.getenv('MYSQL_PORT', '3306')
        db_name = os.getenv('MYSQL_DATABASE', 'app')
        # Compose MySQL DATABASE_URL with line breaks for readability
        DATABASE_URL = (
            f"mysql://{db_user}:{db_password}@"
            f"{db_host}:{db_port}/"
            f"{db_name}?charset=utf8mb4"
        )
    elif db_engine == 'postgresql':
        db_user = os.getenv('POSTGRES_USER', 'postgres')
        db_password = os.getenv('POSTGRES_PASSWORD', '')
        db_host = os.getenv('POSTGRES_HOST', 'localhost')
        db_port = os.getenv('POSTGRES_PORT', '5432')
        db_name = os.getenv('POSTGRES_DB', 'app')
        # Compose PostgreSQL DATABASE_URL with line breaks for readability
        DATABASE_URL = (
            f"postgresql://{db_user}:{db_password}@"
            f"{db_host}:{db_port}/"
            f"{db_name}"
        )
    else:
        sqlite_path = os.getenv('SQLITE_PATH', 'db.sqlite3')
        DATABASE_URL = f"sqlite:///{BASE_DIR / sqlite_path}"

# Use DATABASE_URL for unified database configuration
DATABASES = {
    'default': dj_database_url.config(default=DATABASE_URL)
}