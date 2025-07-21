#!/bin/bash

# Recommended: For 2-core 2GB server, set WORKERS=1 and THREADS=1 to avoid resource contention.
# Exit immediately if a command exits with a non-zero status
set -e

# Set environment variables
export PYTHONPATH=/opt/mito
export DJANGO_SETTINGS_MODULE=core.settings

# Log file paths
LOG_BASE_DIR="/var/log/gunicorn"
ACCESS_LOG="${LOG_BASE_DIR}/gunicorn_access.log"
ERROR_LOG="${LOG_BASE_DIR}/gunicorn_error.log"
CELERY_LOG="/var/log/celery/celery.log"

# Ensure the log directory exists and is writable
mkdir -p $LOG_BASE_DIR /var/log/celery
chmod -R 755 $LOG_BASE_DIR /var/log/celery

# Use environment variables or defaults
WORKERS=${WORKERS:-1}
THREADS=${THREADS:-1}
CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-1}

# Flower Configurations
REDIS_URL=${REDIS_URL:-redis://redis:6379/0}  # Use environment variable for Redis URL
FLOWER_PORT=5555

echo "Using $WORKERS workers and $THREADS threads. (Default: 1 worker, 1 thread)"
echo "Celery auto-reload: $CELERY_AUTORELOAD"

# Function to wait for database
wait_for_db() {
    echo "Waiting for database..."
    # Begin to check database connection
    DB_TYPE=$(echo "$DATABASE_URL" | awk -F: '{print $1}')
    HOST=$(echo "$DATABASE_URL" | sed -E 's#^[^:]+://[^@]+@([^:/]+).*#\1#')
    PORT=$(echo "$DATABASE_URL" | sed -E 's#.*:([0-9]+).*#\1#')

    echo "Detected DB_TYPE: $DB_TYPE, HOST: $HOST, PORT: ${PORT:-default}"

    while true; do
        case "$DB_TYPE" in
            mysql)
                if mysqladmin ping -h "$HOST" --silent; then
                    echo "MySQL is ready!"
                    break
                fi
                ;;
            postgres)
                if pg_isready -h "$HOST" -p "${PORT:-5432}" > /dev/null 2>&1; then
                    echo "PostgreSQL is ready!"
                    break
                fi
                ;;
            *)
                echo "Use SQLite by default and SQLite does not require a health check."
                break
                ;;
        esac
        echo "Waiting for $DB_TYPE at $HOST:$PORT..."
        sleep 2
    done
}

# Function to run migrations
run_migrations() {
    echo "Running migrations..."
    python manage.py migrate --noinput

    # Check if a superuser exists, create one if not
    echo "Checking if superuser exists..."
    DJANGO_SUPERUSER_USERNAME=${DJANGO_SUPERUSER_USERNAME:-admin} \
    DJANGO_SUPERUSER_EMAIL=${DJANGO_SUPERUSER_EMAIL:-admin@example.com} \
    DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PASSWORD:-adminpassword} \
    python manage.py createsuperuser --noinput || echo "Superuser already exists."
}

# Function to collect static files
collect_static() {
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
}

# Function to start gunicorn
start_gunicorn() {
    echo "Starting Gunicorn..."
    exec gunicorn core.wsgi:application \
        --name liangyi \
        --bind 0.0.0.0:8000 \
        --workers $WORKERS \
        --threads $THREADS \
        --worker-class gthread \
        --log-level info \
        --access-logfile $ACCESS_LOG \
        --error-logfile $ERROR_LOG
}

# Function to start celery worker
start_celery_worker() {
        echo "Starting Celery worker..."

    # Note: Auto-reload functionality has been removed in Celery 5.x
    # For development, consider using watchfiles or similar tools
    echo "Starting Celery worker (auto-reload not available in Celery 5.x)"
    exec celery -A core worker \
        --loglevel=${CELERY_LOG_LEVEL:-INFO} \
        --concurrency=${CELERY_CONCURRENCY} \
        --max-tasks-per-child=1 \
        --max-memory-per-child=256000 \
        --logfile=/var/log/celery/worker.log
}

# Function to start celery beat
start_celery_beat() {
        echo "Starting Celery beat..."

    # Note: Auto-reload functionality has been removed in Celery 5.x
    # For development, consider using watchfiles or similar tools
    echo "Starting Celery beat (auto-reload not available in Celery 5.x)"
    exec celery -A core beat \
        --loglevel=${CELERY_LOG_LEVEL:-INFO} \
        --logfile=/var/log/celery/beat.log
}

# Function to start flower
start_flower() {
    echo "Starting Flower..."
    exec celery -A core flower \
        --port=$FLOWER_PORT \
        --address=0.0.0.0 \
        --broker="$REDIS_URL" \
        --loglevel=${CELERY_LOG_LEVEL:-INFO} \
        --logfile=/var/log/celery/flower.log
}

# Function to start Django development server (runserver)
start_development() {
    echo "Starting Django development server (runserver)..."
    exec python manage.py runserver 0.0.0.0:8000
}

# Main execution
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
        collect_static
        start_development
        ;;
    *)
        exec "$@"
        ;;
esac
