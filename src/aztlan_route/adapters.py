"""Provider adapter contracts; no undocumented website automation is provided."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .providers import Provider


class AdapterUnavailable(RuntimeError):
    """Raised when a provider has no permitted machine interface."""


@runtime_checkable
class ProviderAdapter(Protocol):
    provider_id: str

    def send_message(self, conversation_id: str, message: str) -> str:
        """Send a message through a documented, permitted provider interface."""


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    def register(self, provider: Provider, adapter: ProviderAdapter) -> None:
        if not provider.automation_allowed or provider.integration_mode != "documented_api":
            raise ValueError("Provider is not approved for automated integration")
        if adapter.provider_id != provider.id:
            raise ValueError("Adapter provider id does not match catalog entry")
        self._adapters[provider.id] = adapter

    def get(self, provider: Provider) -> ProviderAdapter:
        if not provider.automation_allowed:
            raise AdapterUnavailable(
                f"{provider.name} is configured for manual browser access only"
            )
        try:
            return self._adapters[provider.id]
        except KeyError as exc:
            raise AdapterUnavailable(f"No adapter is installed for {provider.name}") from exc
