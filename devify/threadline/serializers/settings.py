"""
Settings Serializers

Serializers for Settings model CRUD operations.
"""

import re

from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import Settings
from .base import UserSerializer


class SettingsSerializer(serializers.ModelSerializer):
    """
    Main serializer for Settings model - used for display
    """

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Settings
        fields = [
            'id', 'user', 'user_id', 'key', 'value', 'description',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_key(self, value):
        """
        Validate setting key format
        """
        if not value or not value.strip():
            raise serializers.ValidationError(
                _("Setting key cannot be empty")
            )

        # Check for valid key format (alphanumeric, underscore, dot)
        if not re.match(r'^[a-zA-Z0-9_.-]+$', value):
            raise serializers.ValidationError(
                _("Setting key can only contain letters, numbers, "
                  "underscores, dots, and hyphens")
            )

        return value.strip()

    def validate_user_id(self, value):
        """
        Validate user exists and user can access it
        """
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this ID does not exist")
            )

        # Check if user can access this setting
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if request.user != user and not request.user.is_superuser:
                raise serializers.ValidationError(
                    _("You can only create settings for yourself")
                )

        return value

    def validate(self, attrs):
        """
        Object-level validation
        """
        user_id = attrs.get('user_id')
        key = attrs.get('key')

        if user_id and key:
            # Check for duplicate key for the same user
            queryset = Settings.objects.filter(user_id=user_id, key=key)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    _("A setting with this key already exists for this user")
                )

        return attrs


class SettingsCreateSerializer(serializers.ModelSerializer):
    """
    Create serializer for Settings model
    """

    class Meta:
        model = Settings
        fields = ['user_id', 'key', 'value', 'description', 'is_active']

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

    def validate_key(self, value):
        """
        Validate key format
        """
        # Key should only contain alphanumeric characters,
        # underscores, and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise serializers.ValidationError(
                _("Key can only contain letters, numbers, "
                  "underscores, and hyphens")
            )
        return value

    def create(self, validated_data):
        """
        Create a new setting instance
        """
        # Set user from request context or user_id
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        else:
            user_id = validated_data.pop('user_id', None)
            if user_id:
                validated_data['user'] = User.objects.get(id=user_id)

        return super().create(validated_data)


class SettingsUpdateSerializer(serializers.ModelSerializer):
    """
    Update serializer for Settings model
    """

    class Meta:
        model = Settings
        fields = ['value', 'description', 'is_active']
