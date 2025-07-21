"""
This module provides custom renderers for standardizing API response formats.
It includes a CustomJSONRenderer that ensures all API responses follow a
consistent structure with code, message and data fields.
"""

from rest_framework.renderers import JSONRenderer
from rest_framework import status
from utils.constrants import SUCCESS_MESSAGE, FAILED_MESSAGE, SUCCESS_CODE


class CustomJSONRenderer(JSONRenderer):
    """
    A custom JSON renderer that standardizes API response format.

    This renderer is primarily used for JWT authentication-related responses
    (login, refresh token, etc.) since custom views already handle the
    response format internally.

    The standardized format is:
    {
        "code": int,      # 0 for success, HTTP status code for errors
        "message": str,   # "success" or "failed"
        "data": dict      # Original response data
    }

    The renderer handles three cases:
    1. Response already has correct format (code, message, data)
    2. Response has code/message but no data (will restructure other fields)
    3. Response has none of the required fields (will create standard format)

    Example success response:
    {
        "code": 0,
        "message": "success",
        "data": {
            "access": "jwt_token_here",
            "refresh": "refresh_token_here"
        }
    }

    Example error response:
    {
        "code": 401,
        "message": "failed",
        "data": {
            "detail": "Invalid credentials"
        }
    }
    """
    def render(
        self,
        data,
        accepted_media_type=None,
        renderer_context=None
    ):
        if renderer_context is None:
            return super().render(data, accepted_media_type,
                                  renderer_context)

        response = renderer_context.get('response')
        is_success = (status.HTTP_200_OK <= response.status_code < 
                     status.HTTP_300_MULTIPLE_CHOICES)

        # Ensure data is a dictionary
        if not isinstance(data, dict):
            data = {'data': data}

        # Extract code and message from the response
        code = data.get('code', SUCCESS_CODE if is_success else
                        response.status_code)
        message = data.get('message',
                           SUCCESS_MESSAGE if is_success else
                           FAILED_MESSAGE)

        formatted_data = {
            'code': code,
            'message': message,
            'data': data.get('data', data)
        }

        return super().render(formatted_data,
                              accepted_media_type,
                              renderer_context)