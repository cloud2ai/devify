from django.apps import AppConfig


class JirabotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jirabot'
    app_label = 'jirabot'

    def ready(self):
        """
        Register signal handlers when the app is ready.
        """
        import jirabot.signals
