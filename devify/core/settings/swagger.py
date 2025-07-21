"""
Swagger Configuration

This configuration defines the behavior of Swagger documentation, including:
- Disabling session authentication (suitable for JWT-only scenarios).
- Setting up Bearer Token as the authentication method.
"""

SWAGGER_SETTINGS = {
    # Disable session authentication (JWT authentication is used instead)
    'USE_SESSION_AUTH': False,

    # Define the security scheme as Bearer Token
    # Bearer Token is passed via the Authorization request header
    # Use the format: "Bearer <JWT Token>"
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': (
                'Authentication using "Bearer <JWT Token>" format. '
                'Include the JWT token in the Authorization header.'
            ),
        },
    },
}
