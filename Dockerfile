# Use official Python 3.12 slim image
FROM python:3.12-slim

# Build argument to control mirror usage
ARG USE_MIRROR=false

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Setup mirrors based on build argument
RUN set -eux; \
    if [ "$USE_MIRROR" = "true" ]; then \
        echo "Setting up Chinese mirrors..."; \
        # Replace URLs in debian.sources file
        if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
            echo "Updating debian.sources with Chinese mirrors..."; \
            # Replace main Debian sources
            sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list.d/debian.sources; \
            # Replace security sources
            sed -i 's|http://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
            echo "✓ Chinese mirrors configured in debian.sources"; \
            echo "Current debian.sources content:"; \
            cat /etc/apt/sources.list.d/debian.sources; \
        else \
            echo "debian.sources file not found, using default sources"; \
        fi; \
    else \
        echo "Using default Debian sources"; \
    fi; \
    apt-get update

# Install system dependencies
RUN apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    default-libmysqlclient-dev \
    pkg-config \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    procps \
    htop \
    net-tools \
    iputils-ping \
    dnsutils \
    mariadb-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv using pip with mirror selection
RUN set -eux; \
    if [ "$USE_MIRROR" = "true" ]; then \
        echo "Installing uv with Chinese PyPI mirror"; \
        pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn uv; \
    else \
        echo "Installing uv with default PyPI"; \
        pip install uv; \
    fi; \
    echo 'export PATH="/root/.local/bin:$PATH"' >> /root/.bashrc; \
    export PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /opt/devify

# Copy project files
COPY devify /opt/devify
COPY pyproject.toml /opt/devify/

# Install project dependencies with mirror selection
RUN set -eux; \
    . /root/.bashrc; \
    if [ "$USE_MIRROR" = "true" ]; then \
        echo "Using Chinese PyPI mirror for dependencies"; \
        uv pip compile pyproject.toml -o requirements.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple; \
        uv pip install --system -r requirements.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple; \
    else \
        echo "Using default PyPI for dependencies"; \
        uv pip compile pyproject.toml -o requirements.txt; \
        uv pip install --system -r requirements.txt; \
    fi

# Create necessary directories
RUN mkdir -p /var/log/gunicorn /var/log/celery /var/cache/devify

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set default command
ENTRYPOINT ["/entrypoint.sh"]