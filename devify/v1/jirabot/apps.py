from django.apps import AppConfig


class JirabotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'v1.jirabot'
    app_label = 'jirabot'

    def ready(self):
        """
        Register signal handlers when the app is ready.
        """
        import v1.jirabot.signals
