"""
Sample app views

If the codebase becomes too large, you can split the views into multiple files
and organize them under a dedicated 'views' directory. For example, create
views/post.py, views/tag.py, and views/category.py for each resource type.
Then, import and register these views in urls.py as needed.

Reference directory structure:

sample/
├── __init__.py
├── models.py
├── serializers.py
├── urls.py
├── views/
│   ├── __init__.py
│   ├── post.py
│   ├── tag.py
│   └── category.py
"""

"""
All imports are grouped and sorted according to the custom rules:
1. Standard library imports
2. Third-party library imports
3. Local application imports
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.paginations import APIPagination
from core.swagger import (
    list_response,
    ordering_param,
    pagination_params,
    pagination_response,
    response,
)
from utils.constrants import SUCCESS_CODE

from .models import Category, Post, Tag
from .serializers import (
    CategorySerializer,
    PostSerializer,
    PostUpdateSerializer,
    TagSerializer,
)


class PostListCreateView(APIView):
    """
    API endpoint for listing and creating posts.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Get a list of all posts with pagination and sorting",
        parameters=pagination_params() + [
            ordering_param("created_at"),
        ],
        responses={200: pagination_response(PostSerializer)}
    )
    def get(self, request):
        """
        Returns a list of all posts.
        """
        try:
            # Get ordering param from query params
            # Default to 'created_at' if not provided
            # Example: ?ordering=title or ?ordering=-title
            ordering = request.query_params.get('ordering', '-created_at')
            if not ordering:
                ordering = '-created_at'

            ordering_fields = ordering.split(',')
            logging.info(f"Ordering fields: {ordering_fields}")

            # Query all posts and apply the ordering
            # The '-reverse' suffix determines sort direction in database
            posts = Post.objects.all().order_by(*ordering_fields)
            logging.info(f"Posts: {posts}")

            # Pagination Notes:
            #
            # APIView requires manual pagination handling in get() method.
            #
            # GenericAPIView provides automatic pagination by setting the
            # pagination_class attribute.
            #
            # Example:
            #   class PostListCreateView(GenericAPIView):
            #       pagination_class = APIPagination
            #
            paginator = APIPagination()
            paginated_posts = paginator.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_posts, many=True)

            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logging.error(f"Error fetching posts: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Create a new post",
        request=PostSerializer,
        responses={201: response(PostSerializer)}
    )
    def post(self, request):
        """Creates a new post and triggers sample task"""
        try:
            serializer = PostSerializer(
                data=request.data,
                context={"user": request.user}
            )
            if serializer.is_valid():
                # Save the post
                post = serializer.save()

                # Return both post data and task id
                return Response({
                    "code": SUCCESS_CODE,
                    "message": "Post created successfully",
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)

            return Response({
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "Invalid data",
                "data": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(f"Error creating post: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PostDetailView(APIView):
    """
    API endpoint for retrieving, updating and deleting posts.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return None
        except Exception as e:
            logging.error(f"Error fetching post {pk}: {str(e)}")
            raise

    @extend_schema(
        description="Get a specific post",
        responses={200: response(PostSerializer)}
    )
    def get(self, request, pk):
        """Returns a specific post"""
        try:
            post = self.get_object(pk)
            if not post:
                return Response({
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": "Post not found",
                    "data": {"error": "Post not found"}
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = PostSerializer(post)
            return Response({
                "code": SUCCESS_CODE,
                "message": "Post retrieved successfully",
                "data": serializer.data
            })
        except Exception as e:
            logging.error(f"Error retrieving post {pk}: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Update a specific post",
        request=PostUpdateSerializer,
        responses={200: response(PostUpdateSerializer)}
    )
    def put(self, request, pk):
        """Updates a specific post"""
        try:
            post = self.get_object(pk)
            if not post:
                return Response({
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": "Post not found",
                    "data": {"error": "Post not found"}
                }, status=status.HTTP_404_NOT_FOUND)
            serializer = PostUpdateSerializer(post, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "code": SUCCESS_CODE,
                    "message": "Post updated successfully",
                    "data": serializer.data
                })
            return Response({
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "Invalid data",
                "data": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(f"Error updating post {pk}: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Delete a specific post",
        responses={204: None}
    )
    def delete(self, request, pk):
        """Deletes a specific post"""
        try:
            post = self.get_object(pk)
            if not post:
                return Response({
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": "Post not found",
                    "data": {"error": "Post not found"}
                }, status=status.HTTP_404_NOT_FOUND)
            post.delete()
            return Response({
                "code": SUCCESS_CODE,
                "message": "Post deleted successfully",
                "data": {}
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logging.error(f"Error deleting post {pk}: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Tag views
class TagListCreateView(APIView):
    """
    API endpoint for listing and creating tags.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Get a list of all tags",
        responses={200: list_response(TagSerializer)}
    )
    def get(self, request):
        """Returns a list of all tags"""
        try:
            tags = Tag.objects.all()
            serializer = TagSerializer(tags, many=True)
            return Response({
                "code": SUCCESS_CODE,
                "message": "Tags retrieved successfully",
                "data": serializer.data
            })
        except Exception as e:
            logging.error(f"Error fetching tags: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Create a new tag",
        request=TagSerializer,
        responses={201: response(TagSerializer)}
    )
    def post(self, request):
        """Creates a new tag"""
        try:
            serializer = TagSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "code": SUCCESS_CODE,
                    "message": "Tag created successfully",
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response({
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "Invalid data",
                "data": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(f"Error creating tag: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TagDetailView(APIView):
    """
    API endpoint for retrieving, updating and deleting tags.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Tag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            return None
        except Exception as e:
            logging.error(f"Error fetching tag {pk}: {str(e)}")
            raise

    @extend_schema(
        description="Get a specific tag",
        responses={200: response(TagSerializer)}
    )
    def get(self, request, pk):
        """Returns a specific tag"""
        try:
            tag = self.get_object(pk)
            if not tag:
                return Response({
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": "Tag not found",
                    "data": {"error": "Tag not found"}
                }, status=status.HTTP_404_NOT_FOUND)
            serializer = TagSerializer(tag)
            return Response({
                "code": SUCCESS_CODE,
                "message": "Tag retrieved successfully",
                "data": serializer.data
            })
        except Exception as e:
            logging.error(f"Error retrieving tag {pk}: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Update a specific tag",
        request=TagSerializer,
        responses={200: response(TagSerializer)}
    )
    def put(self, request, pk):
        """Updates a specific tag"""
        try:
            tag = self.get_object(pk)
            if not tag:
                return Response({
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": "Tag not found",
                    "data": {"error": "Tag not found"}
                }, status=status.HTTP_404_NOT_FOUND)
            serializer = TagSerializer(tag, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "code": SUCCESS_CODE,
                    "message": "Tag updated successfully",
                    "data": serializer.data
                })
            return Response({
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "Invalid data",
                "data": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(f"Error updating tag {pk}: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Delete a specific tag",
        responses={204: None}
    )
    def delete(self, request, pk):
        """Deletes a specific tag"""
        try:
            tag = self.get_object(pk)
            if not tag:
                return Response({
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": "Tag not found",
                    "data": {"error": "Tag not found"}
                }, status=status.HTTP_404_NOT_FOUND)
            tag.delete()
            return Response({
                "code": SUCCESS_CODE,
                "message": "Tag deleted successfully",
                "data": {}
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logging.error(f"Error deleting tag {pk}: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Category views
class CategoryListCreateView(APIView):
    """
    API endpoint for listing and creating categories.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Get a list of all categories",
        responses={200: list_response(CategorySerializer)}
    )
    def get(self, request):
        """Returns a list of all categories"""
        try:
            categories = Category.objects.all()
            serializer = CategorySerializer(categories, many=True)
            return Response({
                "code": SUCCESS_CODE,
                "message": "Categories retrieved successfully",
                "data": serializer.data
            })
        except Exception as e:
            logging.error(f"Error fetching categories: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Create a new category",
        request=CategorySerializer,
        responses={201: response(CategorySerializer)}
    )
    def post(self, request):
        """Creates a new category"""
        try:
            serializer = CategorySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "code": SUCCESS_CODE,
                    "message": "Category created successfully",
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response({
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "Invalid data",
                "data": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(f"Error creating category: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CategoryDetailView(APIView):
    """
    API endpoint for retrieving, updating and deleting categories.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return None
        except Exception as e:
            logging.error(f"Error fetching category {pk}: {str(e)}")
            raise

    @extend_schema(
        description="Get a specific category",
        responses={200: response(CategorySerializer)}
    )
    def get(self, request, pk):
        """Returns a specific category"""
        try:
            category = self.get_object(pk)
            if not category:
                return Response({
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": "Category not found",
                    "data": {"error": "Category not found"}
                }, status=status.HTTP_404_NOT_FOUND)
            serializer = CategorySerializer(category)
            return Response({
                "code": SUCCESS_CODE,
                "message": "Category retrieved successfully",
                "data": serializer.data
            })
        except Exception as e:
            logging.error(f"Error retrieving category {pk}: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Update a specific category",
        request=CategorySerializer,
        responses={200: response(CategorySerializer)}
    )
    def put(self, request, pk):
        """Updates a specific category"""
        try:
            category = self.get_object(pk)
            if not category:
                return Response({
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": "Category not found",
                    "data": {"error": "Category not found"}
                }, status=status.HTTP_404_NOT_FOUND)
            serializer = CategorySerializer(category, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "code": SUCCESS_CODE,
                    "message": "Category updated successfully",
                    "data": serializer.data
                })
            return Response({
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "Invalid data",
                "data": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(f"Error updating category {pk}: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Delete a specific category",
        responses={204: None}
    )
    def delete(self, request, pk):
        """Deletes a specific category"""
        try:
            category = self.get_object(pk)
            if not category:
                return Response({
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": "Category not found",
                    "data": {"error": "Category not found"}
                }, status=status.HTTP_404_NOT_FOUND)
            category.delete()
            return Response({
                "code": SUCCESS_CODE,
                "message": "Category deleted successfully",
                "data": {}
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logging.error(f"Error deleting category {pk}: {str(e)}")
            return Response({
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": "Internal server error"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)