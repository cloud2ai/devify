# Use official Python 3.12 on Ubuntu 24.04 LTS
FROM ubuntu:24.04

# Build argument to control mirror usage
ARG USE_MIRROR=false

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install ca-certificates first to avoid SSL certificate issues
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates

# Setup mirrors based on build argument (before installing packages)
RUN set -eux; \
    if [ "$USE_MIRROR" = "true" ]; then \
        echo "Setting up Chinese mirrors for Ubuntu 24.04 LTS..."; \
        # Backup original sources
        cp /etc/apt/sources.list /etc/apt/sources.list.backup; \
        # Replace with Chinese mirrors
        echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble main restricted universe multiverse" > /etc/apt/sources.list; \
        echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-updates main restricted universe multiverse" >> /etc/apt/sources.list; \
        echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-backports main restricted universe multiverse" >> /etc/apt/sources.list; \
        echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-security main restricted universe multiverse" >> /etc/apt/sources.list; \
        echo "✓ Chinese mirrors configured for Ubuntu 24.04 LTS (Noble Numbat)"; \
        echo "Current sources.list content:"; \
        cat /etc/apt/sources.list; \
    else \
        echo "Using default Ubuntu sources"; \
    fi; \
    apt-get update

# Install Python 3.12, pip and system dependencies in one step
# libmagic is for python-magic which is a library for file type detection
RUN apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-dev \
    python3-pip \
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
    libmagic1 \
    libmagic-dev \
    procps \
    htop \
    net-tools \
    iputils-ping \
    dnsutils \
    mariadb-client \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Disable externally-managed-environment restriction for container environment
RUN rm -f /usr/lib/python3.12/EXTERNALLY-MANAGED

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
    export PATH="/root/.local/bin:$PATH"; \
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