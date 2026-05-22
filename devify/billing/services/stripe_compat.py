from __future__ import annotations


class StripePlanMappingError(ValueError):
    def __init__(self, *, price_id: str | None = None):
        self.price_id = price_id
        message = 'No Stripe plan mapping found'
        if price_id:
            message = f'{message} for price_id={price_id}'
        super().__init__(message)


def stripe_value(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def stripe_to_dict(obj) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    return dict(getattr(obj, '__dict__', {}) or {})
