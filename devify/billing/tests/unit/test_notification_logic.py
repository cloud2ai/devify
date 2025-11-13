"""
Unit tests for payment notification logic

Pure logic tests for multi-language email content generation.
Tests without sending actual emails.
"""

import uuid
from unittest.mock import Mock, patch, call

import pytest
from django.contrib.auth import get_user_model
from django.utils import translation

User = get_user_model()


class TestGetUserLanguage:
    """
    Test _get_user_language helper function
    """

    def test_get_language_from_profile(self):
        """
        Get language from user profile
        """
        from billing.tasks import _get_user_language

        user = Mock()
        user.profile = Mock()
        user.profile.language = 'zh-CN'

        language = _get_user_language(user)

        assert language == 'zh-CN'

    def test_get_language_profile_none(self):
        """
        Return default when profile.language is None
        """
        from billing.tasks import _get_user_language

        user = Mock()
        user.profile = Mock()
        user.profile.language = None

        language = _get_user_language(user)

        assert language == 'en-US'

    def test_get_language_no_profile(self):
        """
        Return default when user has no profile
        """
        from billing.tasks import _get_user_language

        user = Mock()
        user.profile = None

        language = _get_user_language(user)

        assert language == 'en-US'

    def test_get_language_profile_exception(self):
        """
        Return default when accessing profile raises exception
        """
        from billing.tasks import _get_user_language

        user = Mock()

        def raise_exception():
            raise Exception('Profile error')

        type(user).profile = property(lambda self: raise_exception())

        language = _get_user_language(user)

        assert language == 'en-US'


@pytest.mark.django_db
class TestPaymentSuccessNotification:
    """
    Test payment success notification logic
    """

    @patch('billing.tasks.send_mail')
    def test_send_success_notification_english(self, mock_send_mail):
        """
        Send payment success notification in English
        """
        from billing.tasks import send_payment_success_notification

        unique_id = str(uuid.uuid4())[:8]
        user = User.objects.create_user(
            username=f'testuser_en_{unique_id}',
            email=f'test_en_{unique_id}@example.com'
        )

        send_payment_success_notification(user.id, 29.99)

        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args[1]

        assert 'Payment Successful' in call_kwargs['subject']
        assert '29.99' in call_kwargs['message']
        assert user.email in call_kwargs['recipient_list']

    @patch('billing.tasks.send_mail')
    def test_send_success_notification_user_not_found(
        self, mock_send_mail
    ):
        """
        Handle user not found gracefully (no email sent)
        """
        from billing.tasks import send_payment_success_notification

        send_payment_success_notification(99999, 10.00)

        mock_send_mail.assert_not_called()

    @patch('billing.tasks.send_mail')
    def test_send_success_notification_email_fails(self, mock_send_mail):
        """
        Handle email sending failure gracefully
        """
        from billing.tasks import send_payment_success_notification

        unique_id = str(uuid.uuid4())[:8]
        user = User.objects.create_user(
            username=f'testuser_emailfail_{unique_id}',
            email=f'emailfail_{unique_id}@example.com'
        )

        mock_send_mail.side_effect = Exception('SMTP error')

        send_payment_success_notification(user.id, 10.00)


@pytest.mark.django_db
class TestPaymentFailureNotification:
    """
    Test payment failure notification logic
    """

    @patch('billing.tasks.send_mail')
    def test_send_failure_notification_with_details(
        self, mock_send_mail
    ):
        """
        Send payment failure notification with attempt count and reason
        """
        from billing.tasks import send_payment_failure_notification

        unique_id = str(uuid.uuid4())[:8]
        user = User.objects.create_user(
            username=f'testuser_fail_{unique_id}',
            email=f'fail_{unique_id}@example.com'
        )

        send_payment_failure_notification(
            user.id,
            attempt_count=2,
            failure_reason='Insufficient funds'
        )

        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args[1]

        assert 'Payment Failed' in call_kwargs['subject']
        assert '2' in call_kwargs['message']
        assert 'Insufficient funds' in call_kwargs['message']
        assert user.email in call_kwargs['recipient_list']

    @patch('billing.tasks.send_mail')
    def test_send_failure_notification_multiple_attempts(
        self, mock_send_mail
    ):
        """
        Notification shows correct attempt count
        """
        from billing.tasks import send_payment_failure_notification

        unique_id = str(uuid.uuid4())[:8]
        user = User.objects.create_user(
            username=f'testuser_attempts_{unique_id}',
            email=f'attempts_{unique_id}@example.com'
        )

        send_payment_failure_notification(
            user.id,
            attempt_count=3,
            failure_reason='Card declined'
        )

        call_kwargs = mock_send_mail.call_args[1]
        assert '3' in call_kwargs['message']
        assert 'Card declined' in call_kwargs['message']

    @patch('billing.tasks.send_mail')
    def test_send_failure_notification_user_not_found(
        self, mock_send_mail
    ):
        """
        Handle user not found gracefully
        """
        from billing.tasks import send_payment_failure_notification

        send_payment_failure_notification(
            99999,
            attempt_count=1,
            failure_reason='Test'
        )

        mock_send_mail.assert_not_called()

    @patch('billing.tasks.send_mail')
    def test_send_failure_notification_email_fails(
        self, mock_send_mail
    ):
        """
        Handle email sending failure gracefully
        """
        from billing.tasks import send_payment_failure_notification

        unique_id = str(uuid.uuid4())[:8]
        user = User.objects.create_user(
            username=f'testuser_smtp_fail_{unique_id}',
            email=f'smtp_fail_{unique_id}@example.com'
        )

        mock_send_mail.side_effect = Exception('SMTP connection failed')

        send_payment_failure_notification(
            user.id,
            attempt_count=1,
            failure_reason='Test'
        )
