from django.urls import path
"""
URL configuration for the sample app in the v1 API.

This module defines URL patterns for the sample app, including paths for
creating, listing, updating and deleting posts, tags, and categories.

Routes:
- 'posts/': Provides a list of posts and allows for creating new posts.
- 'posts/<int:pk>/': Allows updating and deleting specific posts.
- 'tags/': Provides a list of tags and allows for creating new tags.
- 'tags/<int:pk>/': Allows updating and deleting specific tags.
- 'categories/': Provides a list of categories and allows for creating new
    categories.
- 'categories/<int:pk>/': Allows updating and deleting specific categories.

Each route is associated with a corresponding view that handles the request.

Views:
- PostListCreateAPIView: Handles listing, creating, updating and deleting posts.
- TagListCreateAPIView: Handles listing, creating, updating and deleting tags.
- CategoryListCreateAPIView: Handles listing, creating, updating and deleting
    categories.
"""
from .views import (
    PostListCreateView, PostDetailView,
    TagListCreateView, TagDetailView,
    CategoryListCreateView, CategoryDetailView
)

urlpatterns = [
    # Post URLs
    path('api/v1/posts', PostListCreateView.as_view(), name='post-list'),
    path('api/v1/posts/<int:pk>', PostDetailView.as_view(), name='post-detail'),

    # Tag URLs
    path('api/v1/tags', TagListCreateView.as_view(), name='tag-list'),
    path('api/v1/tags/<int:pk>', TagDetailView.as_view(), name='tag-detail'),

    # Category URLs
    path('api/v1/categories', CategoryListCreateView.as_view(), name='category-list'),
    path('api/v1/categories/<int:pk>', CategoryDetailView.as_view(),
         name='category-detail'),
]