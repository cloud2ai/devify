"""
Django Cache Configuration

This module provides cache configuration for the Django application.
Supports multiple cache backends including Redis, Memcached, and local memory.
"""

import os
from urllib.parse import urlparse

# ============================
# Cache Configuration
# ============================

# Cache backend selection from environment variable
CACHE_BACKEND = os.getenv('CACHE_BACKEND', 'redis')

def get_redis_cache_url():
    """
    Get Redis cache URL from environment variables.
    Uses CACHE_REDIS_URL if available, otherwise constructs from
    CELERY_BROKER_URL.
    """
    # First try to get dedicated cache Redis URL
    cache_redis_url = os.getenv('CACHE_REDIS_URL')
    if cache_redis_url:
        return cache_redis_url

    # Fallback to Celery broker URL and modify database number
    celery_broker_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
    parsed_url = urlparse(celery_broker_url)

    # Change database from 0 to 1 for cache
    if parsed_url.path and parsed_url.path != '/':
        # URL has database number, replace it
        return f"{parsed_url.scheme}://{parsed_url.netloc}/1"
    else:
        # URL doesn't have database number, add it
        return f"{parsed_url.scheme}://{parsed_url.netloc}/1"

if CACHE_BACKEND == 'redis':
    # Redis cache configuration
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': get_redis_cache_url(),
            'OPTIONS': {},
            'KEY_PREFIX': 'devify',
            'VERSION': 1,
            'TIMEOUT': 300,  # 5 minutes default timeout
        }
    }

elif CACHE_BACKEND == 'memcached':
    # Memcached cache configuration
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
            'LOCATION': os.getenv('CACHE_MEMCACHED_URL', '127.0.0.1:11211'),
            'OPTIONS': {
                'no_delay': True,
                'ignore_exc': True,
            },
            'KEY_PREFIX': 'devify',
            'VERSION': 1,
            'TIMEOUT': 300,
        }
    }

elif CACHE_BACKEND == 'database':
    # Database cache configuration
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'django_cache_table',
            'OPTIONS': {
                'MAX_ENTRIES': 10000,
                'CULL_FREQUENCY': 3,
            },
            'KEY_PREFIX': 'devify',
            'VERSION': 1,
            'TIMEOUT': 300,
        }
    }

else:
    # Fallback to local memory cache (development)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'devify-cache',
            'OPTIONS': {
                'MAX_ENTRIES': 1000,
                'CULL_FREQUENCY': 3,
            },
            'KEY_PREFIX': 'devify',
            'VERSION': 1,
            'TIMEOUT': 300,
        }
    }

# ============================
# Cache Session Configuration
# ============================

# Use cache for session storage (optional)
# Uncomment the following lines to use cache for sessions
# SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# SESSION_CACHE_ALIAS = 'default'

# ============================
# Cache Middleware Configuration
# ============================

# Cache middleware settings
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 300  # 5 minutes
CACHE_MIDDLEWARE_KEY_PREFIX = 'devify'

# ============================
# Cache Key Configuration
# ============================

# Custom cache key functions
def get_cache_key(prefix: str, *args) -> str:
    """
    Generate a consistent cache key

    Args:
        prefix: Key prefix
        *args: Additional key components

    Returns:
        Formatted cache key
    """
    return f"{prefix}:{':'.join(str(arg) for arg in args)}"

# ============================
# Cache Health Check
# ============================

def check_cache_health():
    """
    Check if cache backend is working properly

    Returns:
        bool: True if cache is working, False otherwise
    """
    try:
        from django.core.cache import cache

        # Test basic operations
        test_key = 'cache_health_check'
        test_value = 'test_value'

        # Test set
        cache.set(test_key, test_value, 60)

        # Test get
        retrieved_value = cache.get(test_key)

        # Test delete
        cache.delete(test_key)

        return retrieved_value == test_value

    except Exception as e:
        print(f"Cache health check failed: {e}")
        return False
