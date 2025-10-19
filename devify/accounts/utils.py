"""
Utility functions for working with user accounts and social authentication.
"""

from allauth.socialaccount.models import SocialAccount


class SocialAccountHelper:
    """
    Helper class for accessing social account information.

    This provides convenient methods to query OAuth provider data that was
    previously stored in Profile model fields (google_id, openid, unionid).
    """

    @staticmethod
    def get_google_account(user):
        """
        Get user's Google account information.

        Args:
            user: Django User instance

        Returns:
            SocialAccount instance or None

        Example:
            google = SocialAccountHelper.get_google_account(user)
            if google:
                google_id = google.uid
                email = google.extra_data.get('email')
                name = google.extra_data.get('name')
                picture = google.extra_data.get('picture')
        """
        try:
            return SocialAccount.objects.get(
                user=user,
                provider='google'
            )
        except SocialAccount.DoesNotExist:
            return None

    @staticmethod
    def get_wechat_account(user):
        """
        Get user's WeChat account information.

        Args:
            user: Django User instance

        Returns:
            SocialAccount instance or None

        Example:
            wechat = SocialAccountHelper.get_wechat_account(user)
            if wechat:
                openid = wechat.uid
                unionid = wechat.extra_data.get('unionid')
                nickname = wechat.extra_data.get('nickname')
        """
        try:
            return SocialAccount.objects.get(
                user=user,
                provider='weixin'
            )
        except SocialAccount.DoesNotExist:
            return None

    @staticmethod
    def get_github_account(user):
        """
        Get user's GitHub account information.

        Args:
            user: Django User instance

        Returns:
            SocialAccount instance or None

        Example:
            github = SocialAccountHelper.get_github_account(user)
            if github:
                github_id = github.uid
                username = github.extra_data.get('login')
                avatar = github.extra_data.get('avatar_url')
        """
        try:
            return SocialAccount.objects.get(
                user=user,
                provider='github'
            )
        except SocialAccount.DoesNotExist:
            return None

    @staticmethod
    def get_all_social_accounts(user):
        """
        Get all social accounts linked to a user.

        Args:
            user: Django User instance

        Returns:
            QuerySet of SocialAccount instances

        Example:
            accounts = SocialAccountHelper.get_all_social_accounts(user)
            for account in accounts:
                print(
                    f"{account.provider}: {account.uid}"
                )
        """
        return SocialAccount.objects.filter(user=user)

    @staticmethod
    def has_provider(user, provider):
        """
        Check if user has linked a specific provider.

        Args:
            user: Django User instance
            provider: Provider name ('google', 'weixin', 'github', etc.)

        Returns:
            bool

        Example:
            if SocialAccountHelper.has_provider(user, 'google'):
                print("User has Google account")
        """
        return SocialAccount.objects.filter(
            user=user,
            provider=provider
        ).exists()

    @staticmethod
    def get_provider_uid(user, provider):
        """
        Get provider's user ID directly.

        This is a convenience method to get the uid without fetching
        the whole SocialAccount object.

        Args:
            user: Django User instance
            provider: Provider name

        Returns:
            str or None

        Example:
            google_id = SocialAccountHelper.get_provider_uid(
                user,
                'google'
            )
            if google_id:
                print(f"Google ID: {google_id}")
        """
        account = SocialAccount.objects.filter(
            user=user,
            provider=provider
        ).first()
        return account.uid if account else None


def migrate_old_profile_code():
    """
    Migration helper: Examples of how to update old code that used
    Profile model fields to access OAuth data.

    This is for reference only, to help developers update their code.
    """

    examples = """
    # ========================================
    # Migration Examples
    # ========================================

    # Example 1: Access Google ID
    # ========================================
    # OLD CODE:
    google_id = user.profile.google_id

    # NEW CODE (Option 1 - Direct):
    from allauth.socialaccount.models import SocialAccount
    google_account = SocialAccount.objects.filter(
        user=user,
        provider='google'
    ).first()
    google_id = google_account.uid if google_account else None

    # NEW CODE (Option 2 - Using Helper):
    from accounts.utils import SocialAccountHelper
    google_id = SocialAccountHelper.get_provider_uid(user, 'google')


    # Example 2: Access WeChat openid/unionid
    # ========================================
    # OLD CODE:
    openid = user.profile.openid
    unionid = user.profile.unionid

    # NEW CODE:
    wechat = SocialAccountHelper.get_wechat_account(user)
    if wechat:
        openid = wechat.uid
        unionid = wechat.extra_data.get('unionid')


    # Example 3: Check if user has Google account
    # ========================================
    # OLD CODE:
    has_google = bool(user.profile.google_id)

    # NEW CODE:
    has_google = SocialAccountHelper.has_provider(user, 'google')


    # Example 4: Get all user's OAuth accounts
    # ========================================
    # NEW CODE (no old equivalent):
    accounts = SocialAccountHelper.get_all_social_accounts(user)
    for account in accounts:
        print(
            f"Provider: {account.provider}, "
            f"ID: {account.uid}"
        )
    """

    return examples
