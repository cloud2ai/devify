"""
This module defines the Profile model for extending the built-in User model
using a one-to-one relationship. The Profile model adds additional fields
to store WeChat-related information, personal details, and preferences
for the user.

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
from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    """
    The Profile model extends the built-in User model using a one-to-one
    relationship. It stores additional information about the user, including
    fields specific to WeChat and personal details.
    """

    # Establishes a one-to-one relationship with the User model.
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # WeChat-related fields
    openid = models.CharField(
        max_length=128,
        unique=False,
        blank=True,
        help_text="Unique identifier for the WeChat user."
    )
    unionid = models.CharField(
        max_length=128,
        unique=False,
        blank=True,
        help_text="Unique identifier for the WeChat Open Platform user."
    )
    nickname = models.CharField(
        max_length=30,
        blank=True,
        help_text="WeChat user nickname."
    )
    avatar_url = models.URLField(
        blank=True,
        help_text="URL link to the WeChat user's avatar."
    )
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female')],
        blank=True,
        help_text="User's gender."
    )
    country = models.CharField(
        max_length=30,
        blank=True,
        help_text="Country of the user."
    )
    province = models.CharField(
        max_length=30,
        blank=True,
        help_text="Province of the user."
    )
    city = models.CharField(
        max_length=30,
        blank=True,
        help_text="City of the user."
    )
    language = models.CharField(
        max_length=30,
        blank=True,
        help_text="Language preference of the user."
    )

    # Other personal information fields
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="Personal biography."
    )
    location = models.CharField(
        max_length=30,
        blank=True,
        help_text="Geographical location."
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of birth."
    )

    def __str__(self):
        """
        Returns the username of the associated User model for a readable
        representation of the Profile instance.
        """
        return self.user.username
