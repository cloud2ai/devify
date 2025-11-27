"""
Serializers for Threadline share link functionality.
"""

import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import ThreadlineShareLink


EXPIRATION_CHOICES = (
    ('7d', _('7 Days')),
    ('30d', _('30 Days')),
    ('forever', _('Forever')),
)


class ThreadlineShareLinkSerializer(serializers.ModelSerializer):
    """
    Serializer describing the state of a share link.
    """

    token = serializers.UUIDField(source='uuid', read_only=True)
    share_url = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()
    password = serializers.SerializerMethodField()

    class Meta:
        model = ThreadlineShareLink
        fields = [
            'token',
            'share_url',
            'expires_at',
            'is_active',
            'is_expired',
            'has_password',
            'password',
            'view_count',
            'last_viewed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_share_url(self, obj):
        """
        Build public share URL based on configured frontend URL.
        """
        path = f"/share/{obj.uuid}"
        frontend_url = getattr(settings, 'FRONTEND_URL', '').rstrip('/')
        if frontend_url:
            return f"{frontend_url}{path}"

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(path)
        return path

    def get_is_expired(self, obj):
        """
        Determine whether share link has expired.
        """
        return obj.is_expired()

    def get_has_password(self, obj):
        """
        Indicate if password protection is enabled.
        """
        return bool(obj.password_hash)

    def get_password(self, obj):
        """
        Return plain password if available (for owner only).

        Returns plain password from database or from object attribute
        (set during creation/update).
        """
        return obj.password or getattr(obj, 'plain_password', None) or ''


class ThreadlineShareLinkCreateSerializer(serializers.Serializer):
    """
    Serializer handling creation/refresh logic for share links.
    """

    expiration = serializers.ChoiceField(
        choices=EXPIRATION_CHOICES,
        default='7d'
    )
    password = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=6
    )
    require_password = serializers.BooleanField(default=True)

    def validate_password(self, value):
        """
        Validate the password is a numeric string (6 digits) if provided.
        """
        if not value:
            return ''
        if not value.isdigit():
            raise serializers.ValidationError(
                _("Password must contain only digits")
            )
        if len(value) != 6:
            raise serializers.ValidationError(
                _("Password must be exactly 6 digits")
            )
        return value

    def create(self, validated_data):
        """
        Create or update share link for the given email message.
        If an active share link exists, update it instead of creating a new one
        to preserve the UUID and share URL.
        """
        email_message = self.context['email_message']
        owner = self.context['owner']

        expiration_option = validated_data.get('expiration', '7d')
        expires_at = self._resolve_expiration(expiration_option)

        require_password = validated_data.get('require_password', True)
        password = validated_data.get('password')
        password_hash = ''

        if require_password:
            if not password:
                # Generate random 6-digit numeric password as default
                password = f"{random.randint(100000, 999999)}"
            password_hash = make_password(password)
        else:
            password = ''

        # Check if an active share link already exists
        existing_share_link = ThreadlineShareLink.objects.filter(
            email_message=email_message,
            is_active=True
        ).first()

        if existing_share_link:
            # Update existing share link to preserve UUID and share URL
            existing_share_link.expires_at = expires_at
            existing_share_link.password_hash = password_hash
            existing_share_link.password = password
            existing_share_link.save(
                update_fields=[
                    'expires_at',
                    'password_hash',
                    'password',
                    'updated_at'
                ]
            )
            existing_share_link.plain_password = password
            return existing_share_link
        else:
            # Create new share link only if none exists
            share_link = ThreadlineShareLink.objects.create(
                email_message=email_message,
                owner=owner,
                expires_at=expires_at,
                password_hash=password_hash,
                password=password
            )
            share_link.plain_password = password
            return share_link

    @staticmethod
    def _resolve_expiration(option: str):
        """
        Convert expiration option to concrete datetime.
        """
        now = timezone.now()
        if option == '7d':
            return now + timedelta(days=7)
        if option == '30d':
            return now + timedelta(days=30)
        return None


class SharePasswordSerializer(serializers.Serializer):
    """
    Serializer validating password submission for public links.
    """

    password = serializers.CharField(
        max_length=6,
        min_length=6,
        error_messages={
            'min_length': _("Password must be exactly 6 digits"),
            'max_length': _("Password must be exactly 6 digits")
        }
    )

    def validate_password(self, value):
        """
        Ensure password is exactly 6 digits.
        """
        if not value.isdigit():
            raise serializers.ValidationError(
                _("Password must contain digits only")
            )
        if len(value) != 6:
            raise serializers.ValidationError(
                _("Password must be exactly 6 digits")
            )
        return value
