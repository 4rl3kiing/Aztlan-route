"""Deterministic routing to registered, approved provider adapters."""
from __future__ import annotations

from .adapters import AdapterRegistry
from .providers import Provider


class ModelRouter:
    def __init__(self, registry: AdapterRegistry) -> None:
        self._registry = registry

    def route(self, provider: Provider, conversation_id: str, message: str) -> str:
        if not message.strip():
            raise ValueError("Message cannot be empty")
        if len(message) > 100_000:
            raise ValueError("Message exceeds the 100000-character limit")
        adapter = self._registry.get(provider)
        return adapter.send_message(conversation_id, message)
