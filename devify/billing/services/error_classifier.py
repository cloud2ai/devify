"""
Error classification service for automatic credit refund decisions.

This module classifies workflow errors into system errors (our fault)
and user errors (user's fault) to determine refund eligibility.
"""


class ErrorClassifier:
    """
    Classify errors to determine if credits should be refunded
    """

    SYSTEM_ERROR_PATTERNS = [
        'timeout',
        'connection',
        'unavailable',
        '500',
        '502',
        '503',
        'rate limit',
        'api error',
        'service error',
        'internal error',
    ]

    USER_ERROR_PATTERNS = [
        'invalid format',
        'too long',
        'too large',
        'unsupported',
        'policy violation',
        'insufficient credits',
    ]

    @classmethod
    def is_system_error(cls, error_message: str) -> bool:
        """
        System errors should trigger refund
        """
        if not error_message:
            return False

        error_lower = error_message.lower()
        return any(
            pattern in error_lower
            for pattern in cls.SYSTEM_ERROR_PATTERNS
        )

    @classmethod
    def is_user_error(cls, error_message: str) -> bool:
        """
        User errors should NOT trigger refund
        """
        if not error_message:
            return False

        error_lower = error_message.lower()
        return any(
            pattern in error_lower
            for pattern in cls.USER_ERROR_PATTERNS
        )
