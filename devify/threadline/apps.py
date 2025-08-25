from django.apps import AppConfig


class ThreadlineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'threadline'
    app_label = 'threadline'

    def ready(self):
        """
        Register signal handlers when the app is ready.
        """
        import threadline.signals
