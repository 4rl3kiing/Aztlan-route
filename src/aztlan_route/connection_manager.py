"""Centralized, conservative provider connection state reporting."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from .adapters import AdapterRegistry, AdapterUnavailable
from .providers import Provider


class ConnectionState(StrEnum):
    DISABLED = "disabled"
    MANUAL_ONLY = "manual_only"
    AUTHENTICATION_REQUIRED = "authentication_required"
    WEB_SESSION_CONFIRMED = "web_session_confirmed"
    BROWSER_UNAVAILABLE = "browser_unavailable"
    API_NOT_CONFIGURED = "api_not_configured"
    API_ADAPTER_READY = "api_adapter_ready"


@dataclass(frozen=True, slots=True)
class ProviderConnection:
    provider_id: str
    state: ConnectionState
    detail: str


class ProviderConnectionManager:
    """Reports capabilities without treating browser login as API access."""

    def __init__(
        self,
        providers: Iterable[Provider],
        adapter_registry: AdapterRegistry | None = None,
    ) -> None:
        self._providers = {provider.id: provider for provider in providers}
        self._adapter_registry = adapter_registry

    def get_status(
        self, provider_id: str, browser_session_state: str | None = None
    ) -> ProviderConnection:
        try:
            provider = self._providers[provider_id]
        except KeyError as exc:
            raise KeyError(f"Unknown provider: {provider_id}") from exc

        if provider.integration_mode == "disabled":
            return ProviderConnection(
                provider_id, ConnectionState.DISABLED,
                "Proveedor deshabilitado en el catálogo.",
            )

        if provider.integration_mode == "documented_api" and provider.automation_allowed:
            if self._adapter_registry is not None:
                try:
                    self._adapter_registry.get(provider)
                except AdapterUnavailable:
                    pass
                else:
                    return ProviderConnection(
                        provider_id, ConnectionState.API_ADAPTER_READY,
                        "Adaptador API registrado; la disponibilidad remota "
                        "requiere una prueba aparte.",
                    )
            return ProviderConnection(
                provider_id, ConnectionState.API_NOT_CONFIGURED,
                "No hay un adaptador API aprobado y registrado.",
            )

        if browser_session_state == "authenticated_user_confirmed":
            return ProviderConnection(
                provider_id, ConnectionState.WEB_SESSION_CONFIRMED,
                "El usuario confirmó la sesión web; esto no habilita el envío programático.",
            )
        if browser_session_state in {
            "captcha_required", "mfa_required", "reauthentication_required", "awaiting_user"
        }:
            return ProviderConnection(
                provider_id, ConnectionState.AUTHENTICATION_REQUIRED,
                "La sesión requiere intervención o confirmación manual.",
            )
        if browser_session_state in {"browser_page_closed", "browser_session_closed"}:
            return ProviderConnection(
                provider_id, ConnectionState.BROWSER_UNAVAILABLE,
                "La pestaña o el contexto del navegador está cerrado.",
            )
        return ProviderConnection(
            provider_id, ConnectionState.MANUAL_ONLY,
            "Sólo se permite navegación manual; no existe integración API aprobada.",
        )

    def snapshot(
        self, browser_sessions: dict[str, str] | None = None
    ) -> list[ProviderConnection]:
        sessions = browser_sessions or {}
        return [
            self.get_status(provider_id, sessions.get(provider_id))
            for provider_id in self._providers
        ]
