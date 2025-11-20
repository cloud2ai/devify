"""
EmailAlias Serializers

Serializers for EmailAlias model CRUD operations.
"""

import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import EmailAlias
from .base import UserSerializer


class EmailAliasSerializer(serializers.ModelSerializer):
    """
    EmailAlias serializer for display and read operations
    """

    full_email_address = serializers.ReadOnlyField()
    user = UserSerializer(read_only=True)

    class Meta:
        model = EmailAlias
        fields = [
            'id', 'alias', 'domain', 'full_email_address',
            'is_active', 'user', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'domain', 'full_email_address',
            'user', 'created_at', 'updated_at'
        ]


class EmailAliasCreateSerializer(serializers.ModelSerializer):
    """
    EmailAlias serializer for create and update operations
    """

    class Meta:
        model = EmailAlias
        fields = ['alias', 'is_active']

    def validate_alias(self, value):
        """Validate alias format and constraints"""
        # Convert to lowercase for consistency
        value = value.lower().strip()

        # Basic format validation
        if not re.match(r'^[a-zA-Z0-9._-]+$', value):
            raise serializers.ValidationError(
                _('Alias can only contain letters, numbers, dots, '
                  'hyphens, and underscores')
            )

        # Length validation
        if len(value) < 1:
            raise serializers.ValidationError(
                _('Alias cannot be empty')
            )

        if len(value) > 64:
            raise serializers.ValidationError(
                _('Alias cannot be longer than 64 characters')
            )

        # Start/end validation
        if value.startswith('.') or value.endswith('.'):
            raise serializers.ValidationError(
                _('Alias cannot start or end with a dot')
            )

        # Reserved words validation
        reserved_words = [
            'admin', 'administrator', 'root', 'postmaster',
            'webmaster', 'hostmaster', 'noreply', 'no-reply'
        ]

        if value in reserved_words:
            raise serializers.ValidationError(
                _('This alias is reserved and cannot be used')
            )

        return value
