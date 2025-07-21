"""
REST Framework Settings

This module configures Django REST Framework (DRF) and related JWT settings.

JWT Authentication:
- Uses access tokens in the "Authorization" header ("Bearer <token>").
- Suitable for stateless API communication without cookies.
- Requires clients to store and include tokens in the header per request.

JWTCookieAuthentication:
- Uses cookies to store JWT tokens (access and refresh).
- Tokens are automatically sent by browsers via cookies.
- Ideal for web apps; simplifies frontend as browsers handle cookies.

Below, JWTAuthentication is used, requiring tokens in the request header.

DRF Parameters:
- DEFAULT_RENDERER_CLASSES: Renders API responses in standardized format.
  - CustomJSONRenderer: Ensures consistent response structure with code, message
    and data.
  - BrowsableAPIRenderer: Provides a browsable API interface.
- DEFAULT_PARSER_CLASSES: Parses incoming camelCase request data to snake_case.
  - CamelCaseJSONParser: Handles JSON with camelCase keys for internal
    processing.
"""

from datetime import timedelta

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'core.settings.renders.CustomJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # Schema generation for API documentation
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    # Pagination Settings
    # -----------------
    # DEFAULT_PAGINATION_CLASS options:
    # - PageNumberPagination: Classic page-based style (?page=2)
    # - LimitOffsetPagination: Limit/skip style (?limit=10&offset=20)
    # - CursorPagination: Cursor-based for large datasets, prevents skipping
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',

    # PAGE_SIZE: Number of items per page
    # Can be overridden per view using:
    # - pagination_class attribute
    # - page_size attribute
    'PAGE_SIZE': 10,

    # Additional pagination settings (optional):
    # ---------------------------------------
    # 'PAGINATE_BY_PARAM': 'page_size',  # Allow client to override page size
    # 'MAX_PAGE_SIZE': 100,              # Maximum limit for page size
    # 'PAGE_QUERY_PARAM': 'p',           # Custom page parameter (default: page)
    # 'PAGE_SIZE_QUERY_PARAM': 'size',   # Allow client to set page size

    # --- Sorting Configuration ---
    # DEFAULT_FILTER_BACKENDS: Enable ordering filter backend
    # Using OrderingFilter allows clients to sort results via ?ordering=field_name
    # Example: ?ordering=-created_date for descending sort
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.OrderingFilter',
    ),

    # Optional sorting parameters:
    # -----------------------------------------------------------------
    # ORDERING_PARAM: Custom query parameter name (default: 'ordering')
    # 'ORDERING_PARAM': 'sort_by',

    # ORDERING_FIELDS: Explicitly declare allowed sorting fields in views
    # Note: Must be defined per view using ordering_fields attribute
    # 'ORDERING_FIELDS': ['created_date', 'updated_date'],

    # DEFAULT_ORDERING: Default sorting when no parameter is provided
    # Example: '-created_date' for default descending sort by creation date
    # 'DEFAULT_ORDERING': '-created_date',
}

# SimpleJWT Settings:
#
# - ACCESS_TOKEN_LIFETIME: Duration for which the access token is valid.
# - REFRESH_TOKEN_LIFETIME: Duration for which the refresh token is valid.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

# REST Authentication Settings:
#
# - USE_JWT: Enables JWT for authentication.
# - JWT_AUTH_HTTPONLY: Determines if refresh tokens should be HTTP-only.
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_HTTPONLY": False,
}
