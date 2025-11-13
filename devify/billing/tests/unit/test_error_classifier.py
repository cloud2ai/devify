"""
Unit tests for ErrorClassifier

Pure logic tests without database access.
Tests error classification logic for refund eligibility.
"""

import pytest

from billing.services.error_classifier import ErrorClassifier


class TestSystemErrorClassification:
    """
    Test system error detection logic
    """

    def test_timeout_error_is_system_error(self):
        """
        Timeout errors should be classified as system errors
        """
        assert ErrorClassifier.is_system_error('Request timeout') is True
        assert ErrorClassifier.is_system_error('Connection timeout') is True
        assert ErrorClassifier.is_system_error('TIMEOUT occurred') is True

    def test_http_5xx_errors_are_system_errors(self):
        """
        HTTP 500/502/503 errors should be system errors
        """
        assert ErrorClassifier.is_system_error('HTTP 500 error') is True
        assert ErrorClassifier.is_system_error('502 Bad Gateway') is True
        assert ErrorClassifier.is_system_error('Service 503') is True

    def test_connection_errors_are_system_errors(self):
        """
        Connection errors should be system errors
        """
        assert ErrorClassifier.is_system_error(
            'Connection refused'
        ) is True
        assert ErrorClassifier.is_system_error(
            'Lost connection to API'
        ) is True

    def test_rate_limit_is_system_error(self):
        """
        Rate limit should be system error (not user's fault)
        """
        assert ErrorClassifier.is_system_error('Rate limit exceeded') is True
        assert ErrorClassifier.is_system_error(
            'API rate limit reached'
        ) is True

    def test_api_internal_errors_are_system_errors(self):
        """
        API and service internal errors should be system errors
        """
        assert ErrorClassifier.is_system_error('API error occurred') is True
        assert ErrorClassifier.is_system_error('Service error') is True
        assert ErrorClassifier.is_system_error('Internal error') is True

    def test_case_insensitive_matching(self):
        """
        Error classification should be case-insensitive
        """
        assert ErrorClassifier.is_system_error('TIMEOUT') is True
        assert ErrorClassifier.is_system_error('Timeout') is True
        assert ErrorClassifier.is_system_error('timeout') is True

    def test_empty_message_is_not_system_error(self):
        """
        Empty error message should not be classified as system error
        """
        assert ErrorClassifier.is_system_error('') is False
        assert ErrorClassifier.is_system_error(None) is False

    def test_user_error_is_not_system_error(self):
        """
        User errors should not be classified as system errors
        """
        assert ErrorClassifier.is_system_error('Invalid format') is False
        assert ErrorClassifier.is_system_error(
            'Attachment too large'
        ) is False


class TestUserErrorClassification:
    """
    Test user error detection logic
    """

    def test_invalid_format_is_user_error(self):
        """
        Invalid format errors should be user errors
        """
        assert ErrorClassifier.is_user_error('Invalid format') is True
        assert ErrorClassifier.is_user_error(
            'Invalid format detected'
        ) is True
        assert ErrorClassifier.is_user_error('Data invalid format') is True

    def test_size_limit_errors_are_user_errors(self):
        """
        Size/length limit errors should be user errors
        """
        assert ErrorClassifier.is_user_error('Email too long') is True
        assert ErrorClassifier.is_user_error('Attachment too large') is True

    def test_unsupported_errors_are_user_errors(self):
        """
        Unsupported feature errors should be user errors
        """
        assert ErrorClassifier.is_user_error('Unsupported file type') is True
        assert ErrorClassifier.is_user_error(
            'Unsupported operation'
        ) is True

    def test_policy_violations_are_user_errors(self):
        """
        Policy violation errors should be user errors
        """
        assert ErrorClassifier.is_user_error('Policy violation') is True
        assert ErrorClassifier.is_user_error(
            'Content policy violation'
        ) is True

    def test_insufficient_credits_is_user_error(self):
        """
        Insufficient credits should be user error
        """
        assert ErrorClassifier.is_user_error(
            'Insufficient credits'
        ) is True

    def test_case_insensitive_matching(self):
        """
        User error classification should be case-insensitive
        """
        assert ErrorClassifier.is_user_error('INVALID FORMAT') is True
        assert ErrorClassifier.is_user_error('Invalid Format') is True
        assert ErrorClassifier.is_user_error('invalid format') is True

    def test_empty_message_is_not_user_error(self):
        """
        Empty error message should not be classified as user error
        """
        assert ErrorClassifier.is_user_error('') is False
        assert ErrorClassifier.is_user_error(None) is False

    def test_system_error_is_not_user_error(self):
        """
        System errors should not be classified as user errors
        """
        assert ErrorClassifier.is_user_error('Timeout occurred') is False
        assert ErrorClassifier.is_user_error('500 error') is False


class TestAmbiguousErrorClassification:
    """
    Test edge cases and ambiguous error messages
    """

    def test_unknown_error_not_classified(self):
        """
        Unknown errors should not match either category
        """
        error = 'Something went wrong'

        assert ErrorClassifier.is_system_error(error) is False
        assert ErrorClassifier.is_user_error(error) is False

    def test_partial_match_works(self):
        """
        Partial string match should work
        """
        assert ErrorClassifier.is_system_error(
            'The API error occurred while processing'
        ) is True
        assert ErrorClassifier.is_user_error(
            'The file is too large for upload'
        ) is True

    def test_mixed_message_system_priority(self):
        """
        When message contains both patterns, check classification
        """
        mixed = 'Invalid format due to timeout'

        is_system = ErrorClassifier.is_system_error(mixed)
        is_user = ErrorClassifier.is_user_error(mixed)

        assert is_system is True
        assert is_user is True
