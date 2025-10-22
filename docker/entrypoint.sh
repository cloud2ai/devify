#!/bin/bash
set -e

# -----------------------------------------------------------------------------
# Project Entrypoint Script
# -----------------------------------------------------------------------------
# This script manages database health checks, migrations, static collection,
# and process startup for Django, Celery, Gunicorn, etc.
# -----------------------------------------------------------------------------

# --- Global Variables ---
export PYTHONPATH=/opt/devify
export DJANGO_SETTINGS_MODULE=core.settings

LOG_BASE_DIR="/var/log/gunicorn"
ACCESS_LOG="${LOG_BASE_DIR}/gunicorn_access.log"
ERROR_LOG="${LOG_BASE_DIR}/gunicorn_error.log"
CELERY_LOG="/var/log/celery/celery.log"

WORKERS=${WORKERS:-1}
THREADS=${THREADS:-1}
CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-1}
REDIS_URL=${REDIS_URL:-redis://redis:6379/0}
DB_ENGINE=${DB_ENGINE:-sqlite}

# --- Ensure log directories exist ---
mkdir -p $LOG_BASE_DIR /var/log/celery
chmod -R 755 $LOG_BASE_DIR /var/log/celery

# --- Logging Helper ---
log() { echo -e "\033[1;36m[entrypoint]\033[0m $*"; }

# --- Database Health Check ---
wait_for_db() {
    log "Waiting for database engine: $DB_ENGINE"
    case "$DB_ENGINE" in
        mysql)
            HOST=${MYSQL_HOST:-localhost}
            PORT=${MYSQL_PORT:-3306}
            log "Waiting for MySQL at $HOST:$PORT..."
            until mysqladmin ping -h "$HOST" -P "$PORT" --silent; do
                sleep 2
            done
            log "MySQL is ready!"
            ;;
        postgresql|postgres)
            HOST=${POSTGRES_HOST:-localhost}
            PORT=${POSTGRES_PORT:-5432}
            log "Waiting for PostgreSQL at $HOST:$PORT..."
            until pg_isready -h "$HOST" -p "$PORT" > /dev/null 2>&1; do
                sleep 2
            done
            log "PostgreSQL is ready!"
            ;;
        *)
            log "Using SQLite (no health check required)."
            ;;
    esac
}

# --- Django Management Tasks ---
run_migrations() {
    log "Running Django migrations..."
    python manage.py migrate --noinput

    log "Ensuring superuser exists..."
    DJANGO_SUPERUSER_USERNAME=${DJANGO_SUPERUSER_USERNAME:-admin}
    DJANGO_SUPERUSER_EMAIL=${DJANGO_SUPERUSER_EMAIL:-admin@example.com}
    DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PASSWORD:-adminpassword}

    # Export environment variables for createsuperuser command
    export DJANGO_SUPERUSER_USERNAME
    export DJANGO_SUPERUSER_EMAIL
    export DJANGO_SUPERUSER_PASSWORD

    python manage.py createsuperuser \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email "$DJANGO_SUPERUSER_EMAIL" \
        --noinput \
        || log "Superuser already exists or creation failed."
}

collect_static() {
    log "Collecting static files..."
    python manage.py collectstatic --noinput
}

# --- Process Starters ---
start_gunicorn() {
    log "Starting Gunicorn..."
    exec gunicorn core.wsgi:application \
        --name devify \
        --bind 0.0.0.0:8000 \
        --workers $WORKERS \
        --threads $THREADS \
        --worker-class gthread \
        --log-level info \
        --access-logfile $ACCESS_LOG \
        --error-logfile $ERROR_LOG
}

start_celery_worker() {
    log "Starting Celery worker..."
    exec celery -A core worker \
        --loglevel=${CELERY_LOG_LEVEL:-INFO} \
        --concurrency=${CELERY_CONCURRENCY:-1} \
        --max-tasks-per-child=${CELERY_MAX_TASKS_PER_CHILD:-1000} \
        --max-memory-per-child=${CELERY_MAX_MEMORY_PER_CHILD:-256000} \
        --logfile=/var/log/celery/worker.log
}

start_celery_beat() {
    log "Starting Celery beat..."
    exec celery -A core beat \
        --loglevel=${CELERY_LOG_LEVEL:-INFO} \
        --logfile=/var/log/celery/beat.log
}

start_flower() {
    log "Starting Flower..."
    exec celery -A core flower \
        --port=${FLOWER_PORT:-5555} \
        --address=0.0.0.0 \
        --broker="$REDIS_URL" \
        --loglevel=${CELERY_LOG_LEVEL:-INFO} \
        --logfile=/var/log/celery/flower.log
}

start_development() {
    log "Starting Django development server (runserver)..."
    exec python manage.py runserver 0.0.0.0:8000
}

# --- Main Entrypoint ---
case "$1" in
    gunicorn)
        wait_for_db
        run_migrations
        collect_static
        start_gunicorn
        ;;
    celery)
        wait_for_db
        start_celery_worker
        ;;
    celery-beat)
        wait_for_db
        start_celery_beat
        ;;
    flower)
        start_flower
        ;;
    development)
        wait_for_db
        run_migrations
        start_development
        ;;
    *)
        exec "$@"
        ;;
esac
