"""
Swagger Schema Configuration

A simplified approach to API documentation using drf-spectacular.

This module provides a clean abstraction layer for generating OpenAPI 3.0
schemas with consistent response formats. It addresses common challenges
in API documentation:

1. **Response Format Standardization**: All API responses follow a
   consistent format with code, message, and data fields.

2. **Pagination Documentation**: Provides detailed pagination structure
   documentation with total, page, pageSize, next, and previous fields.

3. **Parameter Reusability**: Common parameters like pagination,
   ordering, and search are abstracted into reusable functions.

4. **Dynamic Schema Generation**: Uses dynamic class creation to avoid
   naming conflicts while maintaining detailed schema structure.

5. **Simplified API**: Provides simple function calls that generate
   complex schemas automatically.

Usage Examples:
    # Standard response
    @extend_schema(responses={200: response(PostSerializer)})

    # List response
    @extend_schema(responses={200: list_response(TagSerializer)})

    # Paginated response
    @extend_schema(
        parameters=pagination_params() + [ordering_param()],
        responses={200: pagination_response(PostSerializer)}
    )
"""

from drf_spectacular.openapi import OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.views import (SpectacularAPIView,
                                   SpectacularSwaggerView,
                                   SpectacularRedocView)
from rest_framework.permissions import AllowAny
from rest_framework import serializers


# Schema view instances
schema_view = SpectacularAPIView.as_view(
    permission_classes=(AllowAny,),
    authentication_classes=(),
)

swagger_view = SpectacularSwaggerView.as_view(
    permission_classes=(AllowAny,),
    authentication_classes=(),
)

redoc_view = SpectacularRedocView.as_view(
    permission_classes=(AllowAny,),
    authentication_classes=(),
)


# Parameter generators
def pagination_params():
    """
    Get pagination parameters for API documentation.

    Returns a list of OpenAPI parameters for standard pagination
    functionality. These parameters are commonly used in list endpoints
    that support pagination.

    Returns:
        list: List of OpenApiParameter objects for page and page_size

    Usage:
        @extend_schema(
            parameters=pagination_params(),
            responses={200: pagination_response(PostSerializer)}
        )

    Generated Parameters:
        - page (int): Page number, starts from 1
        - page_size (int): Number of items per page, max 100
    """
    return [
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Page number (starts from 1)",
            default=1
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Number of items per page (max 100)",
            default=10
        )
    ]


def ordering_param(default="created_at"):
    """
    Get ordering parameter for API documentation.

    Returns an OpenAPI parameter for sorting functionality. This is
    commonly used in list endpoints where users can specify the order
    of results.

    Args:
        default (str): Default ordering field name.
                      Defaults to "created_at".

    Returns:
        OpenApiParameter: Parameter object for ordering functionality

    Usage:
        @extend_schema(
            parameters=[ordering_param("title")],
            responses={200: list_response(PostSerializer)}
        )

    Generated Parameter:
        - ordering (string): Order field, prefix with '-' for descending
    """
    return OpenApiParameter(
        name='ordering',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description=(
            "Order field, prefix with '-' for descending "
            f"(default: {default})"
        ),
        required=False,
        default=default
    )


def search_param():
    """
    Get search parameter for API documentation.

    Returns an OpenAPI parameter for search functionality. This is
    commonly used in list endpoints where users can search through
    the results.

    Returns:
        OpenApiParameter: Parameter object for search functionality

    Usage:
        @extend_schema(
            parameters=[search_param()],
            responses={200: list_response(PostSerializer)}
        )

    Generated Parameter:
        - search (string): Search term to filter results
    """
    return OpenApiParameter(
        name='search',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Search term to filter results",
        required=False
    )


class BaseResponseWrapper(serializers.Serializer):
    """
    Base response wrapper for standardized API responses.

    This class defines the standard structure for all API responses
    in the system. It ensures consistency across all endpoints by
    providing a common format with code, message, and data fields.

    This wrapper is used as the base class for all response
    serializers to maintain consistent API documentation and
    response structure.

    Fields:
        code (IntegerField): Response status code indicating
                           success/failure
        message (CharField): Human-readable response message
        data (Field): The actual response data (varies by endpoint)

    Usage:
        This class is not used directly. Instead, use the response()
        functions which create subclasses of this wrapper.
    """
    code = serializers.IntegerField(help_text="Response status code")
    message = serializers.CharField(help_text="Response message")
    data = serializers.Field(help_text="Response data")


def response(serializer_class):
    """
    Create standard response wrapper for single object endpoints.

    This function generates a response serializer that wraps a single
    object in the standard response format. It's used for endpoints
    that return a single resource (GET /posts/{id}/, POST /posts/,
    etc.).

    The generated serializer includes the standard response structure
    with the provided serializer_class as the data field.

    Args:
        serializer_class: The serializer class for the response data

    Returns:
        type: A dynamically created serializer class that wraps the data

    Usage:
        @extend_schema(responses={200: response(PostSerializer)})

    Generated Response Format:
        {
            "code": integer,
            "message": "string",
            "data": {PostSerializer fields}
        }

    Use Cases:
        - GET /posts/{id}/ - Return single post
        - POST /posts/ - Return created post
        - PUT /posts/{id}/ - Return updated post
        - DELETE /posts/{id}/ - Return success message
    """
    class_name = f"SingleResponse_{serializer_class.__name__}"
    wrapper_class = type(class_name, (BaseResponseWrapper,), {
        'data': serializer_class(help_text="Response data"),
        '__module__': 'core.swagger'
    })
    return wrapper_class


def list_response(serializer_class):
    """
    Create list response wrapper for collection endpoints.

    This function generates a response serializer that wraps a list
    of objects in the standard response format. It's used for
    endpoints that return multiple resources without pagination
    (GET /tags/, GET /categories/, etc.).

    The generated serializer includes the standard response structure
    with a list of the provided serializer_class as the data field.

    Args:
        serializer_class: The serializer class for each item in the list

    Returns:
        type: A dynamically created serializer class that wraps the list

    Usage:
        @extend_schema(responses={200: list_response(TagSerializer)})

    Generated Response Format:
        {
            "code": integer,
            "message": "string",
            "data": [{TagSerializer fields}, ...]
        }

    Use Cases:
        - GET /tags/ - Return all tags
        - GET /categories/ - Return all categories
        - Any endpoint returning a simple list without pagination
    """
    class_name = f"ArrayResponse_{serializer_class.__name__}"
    wrapper_class = type(class_name, (BaseResponseWrapper,), {
        'data': serializers.ListField(
            child=serializer_class(),
            help_text="List of items"
        ),
        '__module__': 'core.swagger'
    })
    return wrapper_class


def pagination_response(serializer_class):
    """
    Create pagination response wrapper for paginated list endpoints.

    This function generates a response serializer that wraps a
    paginated list in the standard response format. It's used for
    endpoints that return multiple resources with pagination support
    (GET /posts/, etc.).

    The generated serializer includes the standard response structure
    with a list of objects and detailed pagination information.

    Args:
        serializer_class: The serializer class for each item in the list

    Returns:
        type: A dynamically created serializer class that wraps the
              paginated data

    Usage:
        @extend_schema(
            parameters=pagination_params() + [ordering_param()],
            responses={200: pagination_response(PostSerializer)}
        )

    Generated Response Format:
        {
            "code": integer,
            "message": "string",
            "data": {
                "list": [{PostSerializer fields}, ...],
                "pagination": {
                    "total": integer,
                    "page": integer,
                    "pageSize": integer,
                    "next": "string (uri)",
                    "previous": "string (uri)"
                }
            }
        }

    Use Cases:
        - GET /posts/ - Return paginated posts with ordering
        - GET /users/ - Return paginated users
        - Any endpoint returning large datasets that need pagination

    Pagination Fields:
        - total: Total number of items across all pages
        - page: Current page number
        - pageSize: Number of items per page
        - next: URL to next page (null if no next page)
        - previous: URL to previous page (null if no previous page)
    """
    # Create pagination info serializer
    pagination_info_name = (
        f"PaginationInfo_{serializer_class.__name__}"
    )
    pagination_info_class = type(
        pagination_info_name,
        (serializers.Serializer,),
        {
            'total': serializers.IntegerField(
                help_text="Total number of items"
            ),
            'page': serializers.IntegerField(
                help_text="Current page number"
            ),
            'pageSize': serializers.IntegerField(
                help_text="Number of items per page"
            ),
            'next': serializers.URLField(
                allow_null=True,
                help_text="URL to next page"
            ),
            'previous': serializers.URLField(
                allow_null=True,
                help_text="URL to previous page"
            ),
            '__module__': 'core.swagger'
        }
    )

    # Create paginated data serializer
    paginated_data_name = (
        f"PaginatedData_{serializer_class.__name__}"
    )
    paginated_data_class = type(
        paginated_data_name,
        (serializers.Serializer,),
        {
            'list': serializers.ListField(
                child=serializer_class(),
                help_text="List of items for current page"
            ),
            'pagination': pagination_info_class(
                help_text="Pagination information"
            ),
            '__module__': 'core.swagger'
        }
    )

    # Create response wrapper
    wrapper_name = (
        f"PaginatedResponse_{serializer_class.__name__}"
    )
    wrapper_class = type(
        wrapper_name,
        (BaseResponseWrapper,),
        {
            'data': paginated_data_class(
                help_text="Paginated data"
            ),
            '__module__': 'core.swagger'
        }
    )
    return wrapper_class
