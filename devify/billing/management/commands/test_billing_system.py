import threading

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from billing.exceptions import InsufficientCreditsError
from billing.models import (
    EmailCreditsTransaction,
    PaymentProvider,
    Plan,
    UserCredits,
)
from billing.services.credits_service import CreditsService
from billing.services.error_classifier import ErrorClassifier


class Command(BaseCommand):
    help = 'Run comprehensive billing system tests'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quick',
            action='store_true',
            help='Run only quick tests (skip heavy tests)'
        )

    def handle(self, *args, **options):
        quick_mode = options.get('quick', False)

        self.stdout.write(
            self.style.SUCCESS('=' * 70)
        )
        self.stdout.write(
            self.style.SUCCESS('  SaaS Billing System Tests')
        )
        self.stdout.write(
            self.style.SUCCESS('=' * 70)
        )

        tests = [
            ('Basic Data Validation', self.test_basic_data),
            ('Credits Query', self.test_credits_query),
            ('Credits Consumption', self.test_credits_consume),
            ('Idempotency Protection', self.test_idempotency),
            ('Insufficient Credits', self.test_insufficient_credits),
            ('Credits Refund', self.test_credits_refund),
            ('Error Classifier', self.test_error_classifier),
        ]

        if not quick_mode:
            tests.append(('Concurrent Consumption', self.test_concurrent_consume))

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            self.stdout.write('\n' + '─' * 70)
            self.stdout.write(f'Test: {test_name}')
            self.stdout.write('─' * 70)

            try:
                test_func()
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {test_name} - PASSED')
                )
                passed += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ {test_name} - FAILED')
                )
                self.stdout.write(
                    self.style.ERROR(f'   Error: {str(e)}')
                )
                failed += 1

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('Test Summary')
        self.stdout.write('=' * 70)
        self.stdout.write(
            f'Total: {passed + failed} | '
            f'Passed: {passed} | '
            f'Failed: {failed}'
        )

        if failed == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    '\n🎉 All tests passed! System is healthy.'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f'\n⚠️  {failed} test(s) failed. '
                    'Please check error messages.'
                )
            )

    def test_basic_data(self):
        """
        Test 1: Basic data validation
        """
        plan_count = Plan.objects.count()
        self.stdout.write(f'  Plans: {plan_count}')
        assert plan_count >= 3, "Should have at least 3 plans"

        credits_count = UserCredits.objects.count()
        self.stdout.write(f'  UserCredits: {credits_count}')
        assert credits_count > 0, "Should have user credits"

        provider_count = PaymentProvider.objects.count()
        self.stdout.write(f'  Payment Providers: {provider_count}')
        assert provider_count >= 1, "Should have at least 1 provider"

    def test_credits_query(self):
        """
        Test 2: Credits query
        """
        user = User.objects.first()
        assert user, "No users found"

        credits = CreditsService.get_user_credits(user.id)
        self.stdout.write(
            f'  User {user.username} credits: '
            f'{credits.available_credits}/{credits.total_credits}'
        )

        balance = CreditsService.get_credits_balance(user.id)
        self.stdout.write(f'  Balance: {balance}')

        assert 'available_credits' in balance, (
            "Balance should have available_credits"
        )

    def test_credits_consume(self):
        """
        Test 3: Credits consume
        """
        from threadline.models import EmailMessage

        user = User.objects.first()

        with transaction.atomic():
            credits_before = CreditsService.get_user_credits(user.id)
            available_before = credits_before.available_credits

            test_email = EmailMessage.objects.filter(user=user).first()

            if not test_email:
                self.stdout.write(
                    '  No email found, skipping email_message_id'
                )
                email_id = None
            else:
                email_id = test_email.id

            transaction_record = CreditsService.consume_credits(
                user_id=user.id,
                amount=1,
                reason='test_consume',
                email_message_uuid='test-uuid-consume',
                email_message_id=email_id,
                idempotency_key=f'test_consume_{timezone.now().timestamp()}'
            )

            credits_after = CreditsService.get_user_credits(user.id)
            available_after = credits_after.available_credits

            self.stdout.write(
                f'  Before: {available_before}, '
                f'After: {available_after}'
            )

            assert available_after == available_before - 1, \
                "Credits should decrease by 1"

            transaction.set_rollback(True)

    def test_idempotency(self):
        """
        Test 4: Idempotency protection
        """
        from threadline.models import EmailMessage

        user = User.objects.first()
        idempotency_key = f'test_idempotency_{timezone.now().timestamp()}'

        with transaction.atomic():
            test_email = EmailMessage.objects.filter(user=user).first()
            email_id = test_email.id if test_email else None

            credits_before = CreditsService.get_user_credits(user.id)
            available_before = credits_before.available_credits

            t1 = CreditsService.consume_credits(
                user_id=user.id,
                amount=1,
                reason='test_idempotency',
                email_message_uuid='test-uuid-idempotency',
                email_message_id=email_id,
                idempotency_key=idempotency_key
            )

            t2 = CreditsService.consume_credits(
                user_id=user.id,
                amount=1,
                reason='test_idempotency',
                email_message_uuid='test-uuid-idempotency',
                email_message_id=email_id,
                idempotency_key=idempotency_key
            )

            self.stdout.write(
                f'  Transaction 1 ID: {t1.id}, '
                f'Transaction 2 ID: {t2.id}'
            )

            assert t1.id == t2.id, \
                "Same idempotency key should return same transaction"

            credits_after = CreditsService.get_user_credits(user.id)
            available_after = credits_after.available_credits

            assert available_after == available_before - 1, \
                "Should only consume once"

            transaction.set_rollback(True)

    def test_insufficient_credits(self):
        """
        Test 5: Insufficient credits
        """
        from threadline.models import EmailMessage

        user = User.objects.first()

        with transaction.atomic():
            credits = UserCredits.objects.get(user=user)
            original_consumed = credits.consumed_credits

            credits.consumed_credits = (
                credits.base_credits + credits.bonus_credits
            )
            credits.save()

            self.stdout.write(
                f'  Available: {credits.available_credits}'
            )

            test_email = EmailMessage.objects.filter(user=user).first()
            email_id = test_email.id if test_email else None

            try:
                CreditsService.consume_credits(
                    user_id=user.id,
                    amount=1,
                    reason='test_insufficient',
                    email_message_uuid='test-uuid-insufficient',
                    email_message_id=email_id,
                    idempotency_key=f'test_insufficient_{timezone.now().timestamp()}'
                )
                raise AssertionError(
                    "Should raise InsufficientCreditsError"
                )
            except InsufficientCreditsError as e:
                self.stdout.write(f'  ✅ Correctly raised: {e}')

            credits.consumed_credits = original_consumed
            credits.save()

            transaction.set_rollback(True)

    def test_credits_refund(self):
        """
        Test 6: Credits refund
        """
        from threadline.models import EmailMessage

        user = User.objects.first()

        with transaction.atomic():
            test_email = EmailMessage.objects.filter(user=user).first()
            email_id = test_email.id if test_email else None

            credits_before = CreditsService.get_user_credits(user.id)
            available_before = credits_before.available_credits

            transaction_record = CreditsService.consume_credits(
                user_id=user.id,
                amount=1,
                reason='test_refund',
                email_message_uuid='test-uuid-refund',
                email_message_id=email_id,
                idempotency_key=f'test_refund_{timezone.now().timestamp()}'
            )

            self.stdout.write(
                f'  Consumed transaction ID: {transaction_record.id}'
            )

            CreditsService.refund_credits(
                transaction_id=transaction_record.id,
                reason='test_refund'
            )

            credits_after = CreditsService.get_user_credits(user.id)
            available_after = credits_after.available_credits

            self.stdout.write(
                f'  Before: {available_before}, '
                f'After refund: {available_after}'
            )

            assert available_after == available_before, \
                "Credits should be restored after refund"

            transaction.set_rollback(True)

    def test_error_classifier(self):
        """
        Test 7: Error classifier
        """
        system_errors = [
            'Connection timeout',
            'API rate limit exceeded',
            '500 Internal Server Error'
        ]

        user_errors = [
            'Invalid format',
            'Email too long',
            'Insufficient credits'
        ]

        for error in system_errors:
            result = ErrorClassifier.is_system_error(error)
            self.stdout.write(
                f'  "{error}": '
                f'{"✅ System" if result else "❌ Not System"}'
            )
            assert result, f"{error} should be system error"

        for error in user_errors:
            result = ErrorClassifier.is_user_error(error)
            self.stdout.write(
                f'  "{error}": '
                f'{"✅ User" if result else "❌ Not User"}'
            )
            assert result, f"{error} should be user error"

    def test_concurrent_consume(self):
        """
        Test 8: Concurrent consume (heavy test)
        """
        from threadline.models import EmailMessage

        user = User.objects.first()

        results = []
        errors = []

        def consume_thread(thread_id):
            try:
                with transaction.atomic():
                    test_email = (
                        EmailMessage.objects.filter(user=user).first()
                    )
                    email_id = test_email.id if test_email else None

                    CreditsService.consume_credits(
                        user_id=user.id,
                        amount=1,
                        reason=f'concurrent_test_{thread_id}',
                        email_message_uuid=f'test-uuid-concurrent-{thread_id}',
                        email_message_id=email_id,
                        idempotency_key=f'concurrent_test_{thread_id}_{timezone.now().timestamp()}'
                    )
                    results.append(thread_id)

                    transaction.set_rollback(True)
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = []
        for i in range(5):
            t = threading.Thread(target=consume_thread, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.stdout.write(
            f'  Successful: {len(results)}, '
            f'Failed: {len(errors)}'
        )

        if errors:
            for thread_id, error in errors:
                self.stdout.write(
                    f'    Thread {thread_id}: {error}'
                )
