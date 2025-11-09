"""
Database helper for E2E test verification
"""
from billing.models import Plan, Subscription, UserCredits


class DBHelper:
    """
    Helper class for database verification in E2E tests
    """

    @staticmethod
    def get_active_subscription(user_id: int):
        """
        Get active subscription for user
        Returns None if no active subscription
        """
        return Subscription.objects.filter(
            user_id=user_id,
            status='active'
        ).select_related('plan').first()

    @staticmethod
    def get_all_subscriptions(user_id: int):
        """
        Get all subscriptions for user
        """
        return Subscription.objects.filter(
            user_id=user_id
        ).select_related('plan').order_by('-created_at')

    @staticmethod
    def get_credits(user_id: int):
        """
        Get UserCredits for user
        """
        try:
            return UserCredits.objects.get(user_id=user_id)
        except UserCredits.DoesNotExist:
            return None

    @staticmethod
    def get_plan_by_slug(slug: str):
        """
        Get plan by slug
        """
        try:
            return Plan.objects.get(slug=slug)
        except Plan.DoesNotExist:
            return None

    @staticmethod
    def verify_subscription_state(
        user_id: int,
        expected_plan_slug: str,
        expected_status: str = 'active',
        expected_auto_renew: bool = True
    ) -> dict:
        """
        Verify subscription state matches expectations
        Returns dict with verification results
        """
        results = {
            'success': True,
            'errors': [],
            'subscription': None,
        }

        subscription = DBHelper.get_active_subscription(user_id)
        results['subscription'] = subscription

        if subscription is None:
            results['success'] = False
            results['errors'].append(
                f"No active subscription found for user {user_id}"
            )
            return results

        # Verify plan
        if subscription.plan.slug != expected_plan_slug:
            results['success'] = False
            results['errors'].append(
                f"Plan mismatch: expected '{expected_plan_slug}', "
                f"got '{subscription.plan.slug}'"
            )

        # Verify status
        if subscription.status != expected_status:
            results['success'] = False
            results['errors'].append(
                f"Status mismatch: expected '{expected_status}', "
                f"got '{subscription.status}'"
            )

        # Verify auto_renew
        if subscription.auto_renew != expected_auto_renew:
            results['success'] = False
            results['errors'].append(
                f"Auto-renew mismatch: expected {expected_auto_renew}, "
                f"got {subscription.auto_renew}"
            )

        return results

    @staticmethod
    def verify_credits_state(
        user_id: int,
        expected_base_credits: int,
        expected_consumed: int = 0
    ) -> dict:
        """
        Verify credits state matches expectations
        Returns dict with verification results
        """
        results = {
            'success': True,
            'errors': [],
            'credits': None,
        }

        credits = DBHelper.get_credits(user_id)
        results['credits'] = credits

        if credits is None:
            results['success'] = False
            results['errors'].append(
                f"No UserCredits found for user {user_id}"
            )
            return results

        # Verify base_credits
        if credits.base_credits != expected_base_credits:
            results['success'] = False
            results['errors'].append(
                f"Base credits mismatch: "
                f"expected {expected_base_credits}, "
                f"got {credits.base_credits}"
            )

        # Verify consumed_credits
        if credits.consumed_credits != expected_consumed:
            results['success'] = False
            results['errors'].append(
                f"Consumed credits mismatch: "
                f"expected {expected_consumed}, "
                f"got {credits.consumed_credits}"
            )

        return results

    @staticmethod
    def assert_subscription_state(
        user_id: int,
        expected_plan_slug: str,
        expected_status: str = 'active',
        expected_auto_renew: bool = True
    ):
        """
        Assert subscription state (raises AssertionError if mismatch)
        """
        results = DBHelper.verify_subscription_state(
            user_id,
            expected_plan_slug,
            expected_status,
            expected_auto_renew
        )

        if not results['success']:
            error_msg = "\n".join(results['errors'])
            raise AssertionError(
                f"Subscription state verification failed:\n{error_msg}"
            )

    @staticmethod
    def assert_credits_state(
        user_id: int,
        expected_base_credits: int,
        expected_consumed: int = 0
    ):
        """
        Assert credits state (raises AssertionError if mismatch)
        """
        results = DBHelper.verify_credits_state(
            user_id,
            expected_base_credits,
            expected_consumed
        )

        if not results['success']:
            error_msg = "\n".join(results['errors'])
            raise AssertionError(
                f"Credits state verification failed:\n{error_msg}"
            )

    @staticmethod
    def count_active_subscriptions(user_id: int) -> int:
        """
        Count number of active subscriptions for user
        Should always be 0 or 1
        """
        return Subscription.objects.filter(
            user_id=user_id,
            status='active'
        ).count()
