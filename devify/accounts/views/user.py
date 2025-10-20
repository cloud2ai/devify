"""
User-related views.

Handles user details retrieval and updates.
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import RetrieveUpdateAPIView

from ..serializers import UserDetailsSerializer


class CustomUserDetailsView(RetrieveUpdateAPIView):
    """
    Custom user details view that uses our UserDetailsSerializer
    to include authentication information and virtual email.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return UserDetailsSerializer

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        """
        Get user details including auth_info and virtual_email.
        """
        user = self.get_object()
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        """
        Update user details.
        """
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=400)
