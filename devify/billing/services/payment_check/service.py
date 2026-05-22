from __future__ import annotations

from billing.constants import is_platform_payment_provider
from billing.services.config_service import get_billing_config

from .registry import get_payment_check_provider, register_payment_check_provider
from .stripe import StripePaymentCheckProvider

register_payment_check_provider(StripePaymentCheckProvider())


class PaymentCheckService:
    @staticmethod
    def _normalize_providers(providers):
        normalized = []
        for provider in providers or []:
            provider_name = str(provider).strip().lower()
            if provider_name and provider_name not in normalized:
                normalized.append(provider_name)
        return normalized

    @staticmethod
    def _is_platform_provider(provider_name: str) -> bool:
        return is_platform_payment_provider(provider_name)

    @classmethod
    def run(
        cls,
        *,
        providers=None,
        mode: str = 'report_only',
        actor_context: dict | None = None,
    ) -> dict:
        config = get_billing_config()
        provider_names = cls._normalize_providers(
            providers if providers is not None else config.payment_check_providers
        )
        runs = []
        requested_providers = list(provider_names)
        skipped_providers = []
        totals = {
            'scanned_count': 0,
            'repaired_count': 0,
            'failed_count': 0,
            'manual_count': 0,
            'would_fix_count': 0,
            'in_sync_count': 0,
            'skipped_count': 0,
        }
        for provider_name in provider_names:
            if cls._is_platform_provider(provider_name):
                skipped_providers.append(provider_name)
                totals['skipped_count'] += 1
                runs.append(
                    {
                        'provider': provider_name,
                        'status': 'skipped',
                        'reason': 'Platform subscriptions are managed locally',
                        'scanned_count': 0,
                        'repaired_count': 0,
                        'failed_count': 0,
                        'manual_count': 0,
                        'would_fix_count': 0,
                        'in_sync_count': 0,
                        'differences': [],
                    }
                )
                continue
            try:
                provider = get_payment_check_provider(provider_name)
            except ValueError as exc:
                skipped_providers.append(provider_name)
                totals['skipped_count'] += 1
                runs.append(
                    {
                        'provider': provider_name,
                        'status': 'skipped',
                        'reason': str(exc),
                        'scanned_count': 0,
                        'repaired_count': 0,
                        'failed_count': 0,
                        'manual_count': 0,
                        'would_fix_count': 0,
                        'in_sync_count': 0,
                        'differences': [],
                    }
                )
                continue
            if not provider.is_configured():
                skipped_providers.append(provider_name)
                totals['skipped_count'] += 1
                runs.append(
                    {
                        'provider': provider_name,
                        'status': 'skipped',
                        'reason': 'Provider is not configured',
                        'scanned_count': 0,
                        'repaired_count': 0,
                        'failed_count': 0,
                        'manual_count': 0,
                        'would_fix_count': 0,
                        'in_sync_count': 0,
                        'differences': [],
                    }
                )
                continue
            run_result = provider.run(mode=mode, actor_context=actor_context)
            runs.append(run_result)
            totals['scanned_count'] += run_result.get('scanned_count', 0)
            totals['repaired_count'] += run_result.get('repaired_count', 0)
            totals['failed_count'] += run_result.get('failed_count', 0)
            totals['manual_count'] += run_result.get('manual_count', 0)
            totals['would_fix_count'] += run_result.get('would_fix_count', 0)
            totals['in_sync_count'] += run_result.get('in_sync_count', 0)

        return {
            'mode': mode,
            'requested_providers': requested_providers,
            'skipped_providers': skipped_providers,
            'providers': runs,
            'provider_runs': runs,
            'totals': totals,
        }
