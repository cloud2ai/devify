from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        """
        Import signals when app is ready
        This ensures signals are registered when Django starts
        """
        import accounts.signals  # noqa
