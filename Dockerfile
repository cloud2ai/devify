# Use official Python 3.12 on Ubuntu 24.04 LTS
FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]

ARG DEV_MODE=0
ARG APT_MIRROR_URL=http://archive.ubuntu.com/ubuntu
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_TRUSTED_HOST=pypi.org

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    DEV_MODE=${DEV_MODE} \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}

# Install ca-certificates first to avoid SSL certificate issues
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates

# Setup mirrors before installing the rest of the packages
RUN set -eux; \
    echo "Using Ubuntu mirror: ${APT_MIRROR_URL}"; \
    printf '%s\n' \
        "deb ${APT_MIRROR_URL} noble main restricted universe multiverse" \
        "deb ${APT_MIRROR_URL} noble-updates main restricted universe multiverse" \
        "deb ${APT_MIRROR_URL} noble-backports main restricted universe multiverse" \
        "deb ${APT_MIRROR_URL} noble-security main restricted universe multiverse" \
        > /etc/apt/sources.list; \
    apt-get update

# Install Python 3.12, pip and system dependencies in one step
# libmagic is for python-magic which is a library for file type detection
# gettext is for Django i18n (makemessages, compilemessages)
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    gettext \
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

# Set working directory
WORKDIR /opt/devify

# Copy project files
COPY devify /opt/devify
COPY pyproject.toml /opt/devify/
COPY LICENSE /opt/devify/
COPY README.md /opt/devify/

# Install uv and project dependencies using the preselected index settings.
RUN set -eux; \
    export PATH="/root/.local/bin:$PATH"; \
    echo "Installing uv from ${PIP_INDEX_URL}"; \
    pip install --index-url "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST" uv; \
    echo 'export PATH="/root/.local/bin:$PATH"' >> /root/.bashrc; \
    export PATH="/root/.local/bin:$PATH"; \
    echo "Using Python index: ${PIP_INDEX_URL}"; \
    uv pip compile pyproject.toml -o requirements.txt --index-url "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST"; \
    uv pip install --system -r requirements.txt --index-url "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST"; \
    if [ "$DEV_MODE" = "1" ]; then \
        echo "Development mode enabled: installing development and test dependencies"; \
        uv pip install --system ".[dev]" --index-url "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST"; \
        for d in /opt/devify/agentcore/*/; do \
            if [ -f "${d}pyproject.toml" ]; then \
                echo "Dev mode: installing ${d}"; \
                (cd "$d" && uv pip install --system -e . --index-url "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST"); \
            fi; \
        done; \
    fi

# Create necessary directories
RUN mkdir -p /var/log/gunicorn /var/log/celery /var/cache/devify

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set default command
ENTRYPOINT ["/entrypoint.sh"]
