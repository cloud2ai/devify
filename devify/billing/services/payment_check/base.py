from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PaymentCheckProvider(ABC):
    name = ''

    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list_remote_subscriptions(
        self,
        *,
        actor_context: dict | None = None,
    ) -> list[Any]:
        raise NotImplementedError

    @abstractmethod
    def build_local_match_key(self, remote_subscription: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def compare_local_and_remote(
        self,
        *,
        local_subscription: Any,
        remote_subscription: Any,
        mode: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def repair_local_state(
        self,
        *,
        user: Any,
        remote_subscription: Any,
        actor_context: dict | None = None,
        mode: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def run(
        self,
        *,
        mode: str = 'report_only',
        actor_context: dict | None = None,
    ) -> dict:
        raise NotImplementedError
