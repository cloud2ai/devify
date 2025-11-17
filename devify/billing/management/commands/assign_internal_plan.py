"""
Management command to assign internal plan to users

Supports:
1. Assign internal plan to new user (create user if needed)
2. Upgrade existing free user to internal plan
3. Downgrade internal user to free plan
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from billing.models import Plan, PaymentProvider, Subscription
from billing.services.credits_service import CreditsService

# Import models at module level to avoid circular imports
try:
    from accounts.models import Profile
except ImportError:
    Profile = None

try:
    from threadline.models import EmailAlias
except ImportError:
    EmailAlias = None


class Command(BaseCommand):
    help = (
        'Assign internal plan to users. Supports creating new users, '
        'upgrading free users, and downgrading internal users to free plan.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username of the user'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email of the user'
        )
        parser.add_argument(
            '--create-user',
            action='store_true',
            help='Create user if not exists (requires --password)'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for new user (required with --create-user)'
        )
        parser.add_argument(
            '--downgrade-to-free',
            action='store_true',
            help='Downgrade internal user to free plan'
        )

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email')
        create_user = options.get('create_user', False)
        password = options.get('password')
        downgrade_to_free = options.get('downgrade_to_free', False)

        if not username and not email:
            raise CommandError('Either --username or --email is required')

        try:
            if downgrade_to_free:
                self.downgrade_to_free(username, email)
            elif create_user:
                self.create_internal_user(username, email, password)
            else:
                self.upgrade_to_internal(username, email)
        except Exception as e:
            raise CommandError(f'Failed: {e}')

    def get_user(self, username=None, email=None):
        """
        Get user by username or email
        """
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(
                    f'User with username "{username}" not found'
                )
        elif email:
            try:
                return User.objects.get(email=email)
            except User.DoesNotExist:
                raise CommandError(f'User with email "{email}" not found')
        return None

    @transaction.atomic
    def create_internal_user(self, username=None, email=None, password=None):
        """
        Create new user and assign internal plan
        """
        if not password:
            raise CommandError(
                '--password is required when using --create-user'
            )

        if username:
            if User.objects.filter(username=username).exists():
                raise CommandError(f'User "{username}" already exists')
            user = User.objects.create_user(
                username=username,
                email=email or f'{username}@devify.local',
                password=password
            )
        elif email:
            if User.objects.filter(email=email).exists():
                raise CommandError(f'User with email "{email}" already exists')
            username = email.split('@')[0]
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
        else:
            raise CommandError('Either --username or --email is required')

        # Create EmailAlias for the user (required for AI email display)
        self.create_email_alias(user)

        # Create Profile if it doesn't exist
        self.create_profile(user)

        self.assign_internal_plan(user)
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Created user "{user.username}" and assigned '
                f'internal plan'
            )
        )

    @transaction.atomic
    def upgrade_to_internal(self, username=None, email=None):
        """
        Upgrade existing free user to internal plan
        """
        user = self.get_user(username, email)

        # Check current subscription
        current_subscription = Subscription.objects.filter(
            user=user,
            status='active'
        ).select_related('plan').first()

        if not current_subscription:
            raise CommandError(
                f'User "{user.username}" has no active subscription'
            )

        if current_subscription.plan.slug == 'internal':
            self.stdout.write(
                self.style.WARNING(
                    f'User "{user.username}" already has internal plan'
                )
            )
            return

        # Check if user has paid subscription
        if current_subscription.plan.slug != 'free':
            error_msg = (
                f'User "{user.username}" has paid subscription '
                f'({current_subscription.plan.name}). '
                f'Only free users can be upgraded to internal plan. '
                f'Please cancel the subscription first or contact '
                f'administrator.'
            )

            # Additional check: if has Stripe subscription
            if current_subscription.djstripe_subscription:
                error_msg += (
                    '\n  Note: User has active Stripe subscription. '
                    'Cancel it in Stripe first before upgrading to '
                    'internal plan.'
                )

            raise CommandError(error_msg)

        # Additional safety check: verify no Stripe subscription exists
        if current_subscription.djstripe_subscription:
            raise CommandError(
                f'User "{user.username}" has Stripe subscription linked. '
                f'This should not happen with Free plan. '
                f'Please verify subscription status or contact '
                f'administrator.'
            )

        # Cancel free plan subscription
        current_subscription.status = 'canceled'
        current_subscription.auto_renew = False
        current_subscription.save()

        # Assign internal plan
        self.assign_internal_plan(user)

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Upgraded user "{user.username}" from Free Plan to '
                f'Internal Plan'
            )
        )

    @transaction.atomic
    def downgrade_to_free(self, username=None, email=None):
        """
        Downgrade internal user to free plan
        """
        user = self.get_user(username, email)

        # Check current subscription
        current_subscription = Subscription.objects.filter(
            user=user,
            status='active'
        ).select_related('plan').first()

        if not current_subscription:
            raise CommandError(
                f'User "{user.username}" has no active subscription'
            )

        if current_subscription.plan.slug != 'internal':
            raise CommandError(
                f'User "{user.username}" does not have internal plan. '
                f'Current plan: {current_subscription.plan.name}'
            )

        # Cancel internal plan subscription
        current_subscription.status = 'canceled'
        current_subscription.auto_renew = False
        current_subscription.save()

        # Assign free plan
        self.assign_free_plan(user)

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Downgraded user "{user.username}" from Internal Plan '
                f'to Free Plan'
            )
        )

    def assign_internal_plan(self, user):
        """
        Assign internal plan to user
        """
        try:
            internal_plan = Plan.objects.get(
                slug='internal',
                is_internal=True
            )
        except Plan.DoesNotExist:
            raise CommandError(
                'Internal plan not found. '
                'Please run init_billing_stripe first.'
            )

        try:
            payment_provider = PaymentProvider.objects.get(name='stripe')
        except PaymentProvider.DoesNotExist:
            raise CommandError(
                'Payment provider not found. '
                'Please run init_billing_stripe first.'
            )

        current_time = timezone.now()
        period_days = internal_plan.metadata.get('period_days', 30)
        period_end = current_time + timedelta(days=period_days)
        base_credits = internal_plan.metadata.get(
            'credits_per_period',
            10000
        )

        # Create internal plan subscription
        subscription = Subscription.objects.create(
            user=user,
            plan=internal_plan,
            provider=payment_provider,
            status='active',
            current_period_start=current_time,
            current_period_end=period_end,
            auto_renew=True
        )

        # Initialize or update user credits
        user_credits = CreditsService.get_user_credits(user.id)
        user_credits.subscription = subscription
        user_credits.base_credits = base_credits
        user_credits.consumed_credits = 0
        user_credits.period_start = current_time
        user_credits.period_end = period_end
        user_credits.save()

    def create_email_alias(self, user):
        """
        Create EmailAlias for user if it doesn't exist
        Required for AI email display in frontend
        """
        if EmailAlias is None:
            self.stdout.write(
                self.style.WARNING(
                    '  ⚠ EmailAlias model not found, '
                    'skipping email alias creation'
                )
            )
            return None

        try:
            existing_alias = EmailAlias.objects.filter(
                user=user,
                is_active=True
            ).first()

            if existing_alias:
                return existing_alias

            alias = EmailAlias.objects.create(
                user=user,
                alias=user.username,
                is_active=True
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ Created email alias: '
                    f'{alias.full_email_address()}'
                )
            )
            return alias
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f'  ⚠ Failed to create email alias: {e}'
                )
            )
            return None

    def create_profile(self, user):
        """
        Create Profile for user if it doesn't exist
        Required for user settings and preferences
        """
        if Profile is None:
            self.stdout.write(
                self.style.WARNING(
                    '  ⚠ Profile model not found, '
                    'skipping profile creation'
                )
            )
            return None

        try:
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'registration_completed': True,
                    'language': 'en-US',
                    'timezone': 'UTC'
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Created profile for user: {user.username}'
                    )
                )
            return profile
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f'  ⚠ Failed to create profile: {e}'
                )
            )
            return None

    def assign_free_plan(self, user):
        """
        Assign free plan to user
        """
        try:
            free_plan = Plan.objects.get(slug='free')
        except Plan.DoesNotExist:
            raise CommandError(
                'Free plan not found. '
                'Please run init_billing_stripe first.'
            )

        try:
            payment_provider = PaymentProvider.objects.get(name='stripe')
        except PaymentProvider.DoesNotExist:
            raise CommandError(
                'Payment provider not found. '
                'Please run init_billing_stripe first.'
            )

        current_time = timezone.now()
        period_days = free_plan.metadata.get('period_days', 30)
        period_end = current_time + timedelta(days=period_days)
        base_credits = free_plan.metadata.get('credits_per_period', 10)

        # Create free plan subscription
        subscription = Subscription.objects.create(
            user=user,
            plan=free_plan,
            provider=payment_provider,
            status='active',
            current_period_start=current_time,
            current_period_end=period_end,
            auto_renew=True
        )

        # Initialize or update user credits
        user_credits = CreditsService.get_user_credits(user.id)
        user_credits.subscription = subscription
        user_credits.base_credits = base_credits
        user_credits.consumed_credits = 0
        user_credits.period_start = current_time
        user_credits.period_end = period_end
        user_credits.save()
