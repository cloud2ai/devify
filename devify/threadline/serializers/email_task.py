"""
EmailTask Serializers

Serializers for EmailTask model CRUD operations.
"""

from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import EmailTask


class EmailTaskSerializer(serializers.ModelSerializer):
    """
    Main serializer for EmailTask model - used for display
    """

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    task_type_display = serializers.CharField(
        source='get_task_type_display',
        read_only=True
    )

    class Meta:
        model = EmailTask
        fields = [
            'id', 'task_type', 'task_type_display', 'status',
            'status_display', 'started_at', 'completed_at',
            'error_message', 'details', 'task_id', 'created_at'
        ]
        read_only_fields = [
            'id', 'status', 'started_at', 'completed_at', 'created_at'
        ]


class EmailTaskCreateSerializer(serializers.ModelSerializer):
    """
    Create serializer for EmailTask model
    """

    class Meta:
        model = EmailTask
        fields = ['user_id']

    def validate_user_id(self, value):
        """
        Validate user exists and set from request context
        """
        # Auto-set user from request
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return request.user.id

        try:
            User.objects.get(id=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this ID does not exist")
            )


class EmailTaskUpdateSerializer(serializers.ModelSerializer):
    """
    Update serializer for EmailTask model
    """

    class Meta:
        model = EmailTask
        fields = ['status', 'error_message']
