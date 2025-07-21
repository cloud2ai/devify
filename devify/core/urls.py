from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include

from .swagger import schema_view, swagger_view, redoc_view
from accounts.views import WeChatAppLoginView

# Define project URL routing configuration
urlpatterns = [
    # Health check endpoint
    # Used by Docker/Kubernetes for container health monitoring
    # Returns a simple 'OK' response to indicate the application is running
    path('health', lambda _: JsonResponse({'health': 'OK'}, status=200)),

    # API Schema endpoint
    # Provides the OpenAPI schema in JSON format
    path('api/schema', schema_view, name='schema'),

    # Swagger UI documentation route
    # Displays the API documentation using Swagger UI.
    path('swagger', swagger_view, name='swagger-ui'),

    # ReDoc documentation route
    # Displays the API documentation using ReDoc.
    path('redoc', redoc_view, name='redoc'),

    # Django admin site route
    # Provides access to the Django Admin interface for managing models and
    # data.
    path('admin', admin.site.urls),

    # Authentication routes
    # Includes authentication endpoints provided by custom
    # v1.auth.urls (no trailing slash)
    path('', include('v1.auth.urls')),

    # API routes for the cloud_platform application
    # Includes the URLs for APIs under the 'v1/sample' app.
    path('', include('v1.sample.urls')),

    # FIXME(Ray): Implement this method according to real project
    # Simulates WeChat mini-program login functionality
    # Endpoint for WeChat authentication
    # path('api/v1/auth/wechat/login',
    #      WeChatAppLoginView.as_view(),
    #      name='wechat_auth'),
]
