"""
This module defines the Profile model for extending the built-in User model
using a one-to-one relationship. The Profile model adds additional fields
to store personal details, preferences, and registration state.

For OAuth/Social authentication, this project uses django-allauth's
SocialAccount model instead of storing provider-specific IDs in Profile.
See: allauth.socialaccount.models.SocialAccount

Django's default User model includes the following fields:
    - username: A unique identifier for the user.
    - first_name: The user's first name.
    - last_name: The user's last name.
    - email: The user's email address.
    - password: The user's hashed password.
    - is_staff: Boolean indicating if the user can access the admin site.
    - is_active: Boolean indicating if the user account is active.
    - date_joined: The date when the user account was created.
    - last_login: The last time the user logged in.

Other methods to extend the User model:
    - Proxy model: Modify behavior without changing the schema.
    - Subclassing User: Create a custom user model with your own fields.
    - Using a ForeignKey: Establish a many-to-one relationship for extensions.
"""
from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    """
    The Profile model extends the built-in User model using a one-to-one
    relationship. It stores personal information, preferences, and
    registration state.

    Note: OAuth/Social authentication uses django-allauth's SocialAccount
    model. To query social accounts:
        from allauth.socialaccount.models import SocialAccount
        social_accounts = SocialAccount.objects.filter(user=user)
        google_account = SocialAccount.objects.get(
            user=user,
            provider='google'
        )
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    registration_completed = models.BooleanField(
        default=False,
        help_text=(
            "Indicates whether user has completed the registration process "
            "(set password, virtual email, scene selection)."
        )
    )

    registration_token = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Temporary token for email registration verification. "
            "Expires after REGISTRATION_TOKEN_EXPIRY_HOURS."
        )
    )

    registration_token_expires = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiration datetime for registration_token."
    )

    nickname = models.CharField(
        max_length=30,
        blank=True,
        help_text="User nickname."
    )

    avatar_url = models.URLField(
        blank=True,
        help_text="URL link to the user's avatar."
    )

    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="Personal biography or description."
    )

    language = models.CharField(
        max_length=10,
        default='en-US',
        choices=[
            ('en-US', 'English'),
            ('zh-CN', '简体中文'),
            ('es', 'Español'),
        ],
        help_text=(
            "Specifies the language used by AI when generating summaries, "
            "titles, and metadata. This is a global setting shared across "
            "all applications."
        )
    )

    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text=(
            "User's timezone for displaying dates and times. "
            "Common values: 'UTC', 'Asia/Shanghai', 'America/New_York', etc."
        )
    )

    def __str__(self):
        """
        Returns the username of the associated User model for a readable
        representation of the Profile instance.
        """
        return self.user.username
