import os

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    """
    Initialize Django Site and OAuth providers

    This command handles:
    - Django Site configuration (domain and name)
    - OAuth providers (Google, WeChat, etc.)

    Usage:
        python manage.py init_social_apps
        python manage.py init_social_apps --site-domain=example.com --site-name="My Site"
        python manage.py init_social_apps --google-client-id=xxx --google-secret=yyy
        python manage.py init_social_apps --list
    """
    help = 'Initialize Django Site and OAuth providers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--google-client-id',
            type=str,
            help='Google OAuth Client ID'
        )
        parser.add_argument(
            '--google-secret',
            type=str,
            help='Google OAuth Client Secret'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List existing SocialApp configurations'
        )
        parser.add_argument(
            '--site-domain',
            type=str,
            help='Override SITE_DOMAIN from environment'
        )
        parser.add_argument(
            '--site-name',
            type=str,
            help='Override SITE_NAME from environment'
        )

    def handle(self, *args, **options):
        self.options = options

        if options['list']:
            self.list_social_apps()
            return

        self.stdout.write('=' * 70)
        self.stdout.write(
            self.style.SUCCESS('Initializing Site & Social Apps...')
        )
        self.stdout.write('=' * 70)
        self.stdout.write('')

        self.init_site_config()
        self.stdout.write('')

        site = Site.objects.get_current()
        self.stdout.write(f'Current site: {site.domain}')
        self.stdout.write('')

        google_client_id = (
            options.get('google_client_id') or
            os.getenv('GOOGLE_OAUTH_CLIENT_ID') or
            os.getenv('GOOGLE_CLIENT_ID')
        )
        google_client_secret = (
            options.get('google_secret') or
            os.getenv('GOOGLE_OAUTH_CLIENT_SECRET') or
            os.getenv('GOOGLE_CLIENT_SECRET')
        )

        if google_client_id and google_client_secret:
            google_app, created = SocialApp.objects.get_or_create(
                provider='google',
                defaults={
                    'name': 'Google OAuth',
                    'client_id': google_client_id,
                    'secret': google_client_secret,
                }
            )

            if created:
                google_app.sites.add(site)
                self.stdout.write(
                    self.style.SUCCESS(
                        '✓ Created Google OAuth app'
                    )
                )
            else:
                google_app.client_id = google_client_id
                google_app.secret = google_client_secret
                google_app.save()

                if site not in google_app.sites.all():
                    google_app.sites.add(site)

                self.stdout.write(
                    self.style.WARNING(
                        '✓ Updated Google OAuth app'
                    )
                )

            self.stdout.write(f'  Provider: {google_app.provider}')
            self.stdout.write(
                f'  Client ID: {google_app.client_id[:30]}...'
            )
            self.stdout.write(f'  Sites: {list(google_app.sites.all())}')
        else:
            self.stdout.write(
                self.style.WARNING(
                    '⚠ Google OAuth not configured'
                )
            )
            self.stdout.write(
                '  Please provide GOOGLE_CLIENT_ID and '
                'GOOGLE_CLIENT_SECRET'
            )
            self.stdout.write('  via environment variables or command arguments')

        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(
            self.style.SUCCESS('Social Apps initialization completed!')
        )
        self.stdout.write('=' * 70)

    def init_site_config(self):
        """
        Initialize Django Site configuration from environment variables
        """
        site_domain = (
            self.options.get('site_domain') or
            os.getenv('SITE_DOMAIN', 'localhost:8000')
        )
        site_name = (
            self.options.get('site_name') or
            os.getenv('SITE_NAME', 'Devify')
        )

        try:
            site = Site.objects.get(pk=settings.SITE_ID)
            site.domain = site_domain
            site.name = site_name
            site.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Site configured: {site.domain} ({site.name})'
                )
            )
        except Site.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'✗ Site with ID {settings.SITE_ID} not found'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Failed to configure Site: {e}')
            )

    def list_social_apps(self):
        """
        List all configured SocialApps
        """
        apps = SocialApp.objects.all()

        self.stdout.write('=' * 70)
        self.stdout.write('Configured Social Apps:')
        self.stdout.write('=' * 70)
        self.stdout.write('')

        if apps.count() == 0:
            self.stdout.write(
                self.style.WARNING('No SocialApps configured')
            )
        else:
            for app in apps:
                self.stdout.write(
                    self.style.SUCCESS(f'Provider: {app.provider}')
                )
                self.stdout.write(f'  Name: {app.name}')
                self.stdout.write(
                    f'  Client ID: {app.client_id[:30]}...'
                )
                self.stdout.write(
                    f'  Sites: {[s.domain for s in app.sites.all()]}'
                )
                self.stdout.write('')

        self.stdout.write('=' * 70)
