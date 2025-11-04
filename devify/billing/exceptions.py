class BillingException(Exception):
    """
    Base exception for billing module
    """
    pass


class InsufficientCreditsError(BillingException):
    """
    Raised when user has insufficient credits
    """
    pass


class SubscriptionError(BillingException):
    """
    Raised when subscription operation fails
    """
    pass


class PaymentError(BillingException):
    """
    Raised when payment operation fails
    """
    pass
