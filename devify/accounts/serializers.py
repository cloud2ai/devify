import re

from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from allauth.socialaccount import providers
from allauth.socialaccount.models import SocialAccount

from accounts.models import Profile
from threadline.models import EmailAlias


class SuccessResponseSerializer(serializers.Serializer):
    """
    Standard success response for Swagger documentation.
    """
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()


class TokenVerificationResponseSerializer(serializers.Serializer):
    """
    Token verification response with email.
    """
    success = serializers.BooleanField(default=True)
    email = serializers.EmailField()


class AuthTokenResponseSerializer(serializers.Serializer):
    """
    Authentication token response (JWT).
    """
    access = serializers.CharField(help_text=_("JWT access token"))
    refresh = serializers.CharField(help_text=_("JWT refresh token"))
    user = serializers.DictField(help_text=_("User basic info"))


class UsernameAvailabilityResponseSerializer(serializers.Serializer):
    """
    Username availability check response.
    """
    available = serializers.BooleanField()
    username = serializers.CharField()
    message = serializers.CharField()


class SceneSerializer(serializers.Serializer):
    """
    Scene information serializer.
    """
    key = serializers.CharField(
        help_text=_("Scene key (e.g., 'chat', 'product_issue')")
    )
    name = serializers.CharField(
        help_text=_("Scene display name in requested language")
    )
    description = serializers.CharField(
        help_text=_("Scene description in requested language")
    )


class SendRegistrationEmailSerializer(serializers.Serializer):
    """
    Serializer for sending registration email.
    """
    email = serializers.EmailField(
        required=True,
        help_text=_("User's email address")
    )

    def validate_email(self, value):
        """
        Validate email is not already registered and completed.

        Check if user registered via OAuth and provide friendly hint.
        Allow re-sending email if user exists but registration not completed.
        """
        value = value.lower().strip()

        try:
            user = User.objects.get(email=value)

            try:
                profile = user.profile
                if profile.registration_completed:
                    social_accounts = SocialAccount.objects.filter(
                        user=user
                    )

                    if social_accounts.exists():
                        provider_names = []
                        for acc in social_accounts:
                            try:
                                provider_class = (
                                    providers.registry.by_id(
                                        acc.provider
                                    )
                                )
                                provider_names.append(
                                    provider_class.name
                                )
                            except Exception:
                                provider_names.append(
                                    acc.provider.title()
                                )

                        providers_str = ' or '.join(provider_names)

                        raise serializers.ValidationError(
                            _(
                                "This email is already registered "
                                "via %(providers)s. "
                                "Please use %(providers)s to "
                                "login instead."
                            ) % {'providers': providers_str}
                        )
                    else:
                        raise serializers.ValidationError(
                            _(
                                "This email address is already "
                                "registered. Please login instead."
                            )
                        )
            except Profile.DoesNotExist:
                pass

        except User.DoesNotExist:
            pass

        return value


class VirtualEmailUsernameSerializer(serializers.Serializer):
    """
    Serializer for validating virtual email username.
    """
    username = serializers.CharField(
        min_length=3,
        max_length=64,
        required=True,
        help_text=_(
            "Virtual email username "
            "(will become username@domain)"
        )
    )

    def validate_username(self, value):
        """
        Validate virtual email username format and uniqueness.
        """
        value = value.lower().strip()

        if not re.match(r'^[a-zA-Z0-9._-]+$', value):
            raise serializers.ValidationError(
                _(
                    "Username can only contain letters, numbers, "
                    "dots, hyphens, and underscores"
                )
            )

        if value.startswith('.') or value.endswith('.'):
            raise serializers.ValidationError(
                _("Username cannot start or end with a dot")
            )

        reserved_words = [
            'admin', 'administrator', 'root', 'postmaster',
            'webmaster', 'hostmaster', 'noreply', 'no-reply',
            'support', 'help', 'info', 'contact'
        ]

        if value in reserved_words:
            raise serializers.ValidationError(
                _("This username is reserved and cannot be used")
            )

        if not EmailAlias.is_unique(value):
            raise serializers.ValidationError(
                _("This username is already taken")
            )

        return value


class CompleteRegistrationSerializer(serializers.Serializer):
    """
    Serializer for completing user registration.
    """
    token = serializers.CharField(
        required=True,
        help_text=_("Registration verification token")
    )

    password = serializers.CharField(
        min_length=8,
        max_length=32,
        write_only=True,
        style={'input_type': 'password'},
        help_text=_(
            "User password (8-32 characters, "
            "must contain letters and numbers)"
        )
    )

    virtual_email_username = serializers.CharField(
        min_length=3,
        max_length=64,
        required=True,
        help_text=_("Virtual email username")
    )

    scene = serializers.CharField(
        required=True,
        help_text=_(
            "User's selected scene "
            "(e.g., 'chat', 'product_issue')"
        )
    )

    language = serializers.CharField(
        required=True,
        help_text=_("User's preferred language (e.g., 'en-US', 'zh-CN')")
    )

    timezone = serializers.CharField(
        required=True,
        help_text=_(
            "User's timezone "
            "(e.g., 'UTC', 'Asia/Shanghai')"
        )
    )

    def validate_password(self, value):
        """
        Validate password strength: 8-32 characters,
        must contain letters and numbers.
        """
        if len(value) < 8:
            raise serializers.ValidationError(
                _("Password must be at least 8 characters long")
            )

        if len(value) > 32:
            raise serializers.ValidationError(
                _("Password cannot exceed 32 characters")
            )

        has_letter = re.search(r'[a-zA-Z]', value)
        has_number = re.search(r'[0-9]', value)

        if not (has_letter and has_number):
            raise serializers.ValidationError(
                _("Password must contain both letters and numbers")
            )

        return value

    def validate_virtual_email_username(self, value):
        """
        Validate virtual email username.

        Reuse validation logic from VirtualEmailUsernameSerializer.
        """
        username_serializer = VirtualEmailUsernameSerializer(
            data={'username': value}
        )

        if not username_serializer.is_valid():
            raise serializers.ValidationError(
                username_serializer.errors['username']
            )

        return username_serializer.validated_data['username']

    def validate_language(self, value):
        """
        Validate language is supported.
        """
        supported_languages = ['en-US', 'zh-CN']

        if value not in supported_languages:
            raise serializers.ValidationError(
                _(
                    "Unsupported language. "
                    "Supported: %(languages)s"
                ) % {'languages': ', '.join(supported_languages)}
            )

        return value


class CompleteGoogleSetupSerializer(serializers.Serializer):
    """
    Serializer for completing Google user setup.

    Google users are already authenticated via OAuth,
    so they don't need to provide a password.
    They only need to complete virtual email and preferences setup.
    """

    virtual_email_username = serializers.CharField(
        min_length=3,
        max_length=64,
        required=True,
        help_text=_("Virtual email username")
    )

    scene = serializers.CharField(
        required=True,
        help_text=_("User's selected scene")
    )

    language = serializers.CharField(
        required=True,
        help_text=_("User's preferred language")
    )

    timezone = serializers.CharField(
        required=True,
        help_text=_("User's timezone")
    )

    def validate_scene(self, value):
        """
        Validate scene is valid.
        """
        if not value:
            raise serializers.ValidationError(
                _("Scene is required")
            )

        return value

    def validate_virtual_email_username(self, value):
        """
        Validate virtual email username.

        Reuse validation logic from VirtualEmailUsernameSerializer.
        """
        username_serializer = VirtualEmailUsernameSerializer(
            data={'username': value}
        )

        if not username_serializer.is_valid():
            raise serializers.ValidationError(
                username_serializer.errors['username']
            )

        return username_serializer.validated_data['username']

    def validate_language(self, value):
        """
        Validate language is supported.
        """
        supported_languages = ['en-US', 'zh-CN']

        if value not in supported_languages:
            raise serializers.ValidationError(
                _(
                    "Unsupported language. "
                    "Supported: %(languages)s"
                ) % {'languages': ', '.join(supported_languages)}
            )

        return value


class UserDetailsSerializer(serializers.ModelSerializer):
    """
    Custom user details serializer for dj-rest-auth.
    Includes virtual email address from EmailAlias and profile information.
    Also includes authentication method information and password change capability.
    """
    virtual_email = serializers.SerializerMethodField(
        read_only=True,
        help_text=_(
            "Primary virtual email address for receiving emails"
        )
    )

    profile = serializers.SerializerMethodField(
        read_only=True,
        help_text=_("User profile information")
    )

    auth_info = serializers.SerializerMethodField(
        read_only=True,
        help_text=_("Authentication method and related information")
    )

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'virtual_email',
            'profile',
            'auth_info'
        ]
        read_only_fields = [
            'id',
            'username',
            'email',
            'virtual_email',
            'profile',
            'auth_info'
        ]

    def get_virtual_email(self, obj):
        """
        Get the primary virtual email address for the user.
        Returns the first active EmailAlias.
        """
        try:
            email_alias = EmailAlias.objects.filter(
                user=obj,
                is_active=True
            ).first()

            if email_alias:
                return email_alias.full_email_address()

            return None

        except Exception:
            return None

    def get_profile(self, obj):
        """
        Get user profile information.

        Returns registration status and preferences.
        """
        try:
            profile = obj.profile
            return {
                'registration_completed': (
                    profile.registration_completed
                ),
                'language': profile.language,
                'timezone': profile.timezone,
                'nickname': profile.nickname,
                'avatar_url': profile.avatar_url
            }
        except Profile.DoesNotExist:
            return None

    def get_auth_info(self, obj):
        """
        Get authentication method information.

        Returns authentication type, provider info, and capabilities.
        """
        auth_info = {
            'method': 'email',
            'provider': None,
            'provider_account_id': None,
            'provider_email': None,
            'can_change_password': obj.has_usable_password(),
            'login_identifier': None
        }

        try:
            social_accounts = SocialAccount.objects.filter(user=obj)

            if social_accounts.exists():
                social_account = social_accounts.first()
                provider_id = social_account.provider

                provider_name_map = {
                    'google': 'Google',
                    'github': 'GitHub',
                    'facebook': 'Facebook',
                    'twitter': 'Twitter',
                }

                auth_info['method'] = 'oauth'
                auth_info['provider'] = provider_name_map.get(
                    provider_id,
                    provider_id.title()
                )
                auth_info['provider_account_id'] = social_account.uid
                auth_info['provider_email'] = (
                    social_account.extra_data.get('email')
                )
                auth_info['login_identifier'] = (
                    f"{auth_info['provider']} "
                    f"({auth_info['provider_email'] or social_account.uid})"
                )
            else:
                auth_info['login_identifier'] = obj.email

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Error getting auth info for user {obj.id}: {e}"
            )

        return auth_info


class CustomPasswordResetSerializer(serializers.Serializer):
    """
    Custom password reset serializer that only allows email-registered users.
    OAuth users are rejected with appropriate error message.
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        """
        Validate that the email belongs to an email-registered user.
        """
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("No user found with this email address")
            )

        if not user.has_usable_password():
            raise serializers.ValidationError(
                _(
                    "OAuth users cannot reset password. "
                    "Please login with your OAuth provider."
                )
            )

        try:
            profile = user.profile
            if not profile.registration_completed:
                raise serializers.ValidationError(
                    _("Please complete registration first")
                )
        except Profile.DoesNotExist:
            raise serializers.ValidationError(
                _("User profile not found")
            )

        return value
