import pytest

from aztlan_route.adapters import AdapterRegistry
from aztlan_route.connection_manager import (
    ConnectionState,
    ProviderConnectionManager,
)
from aztlan_route.providers import Provider


def provider(mode="manual_browser", automation=False):
    return Provider("sample", "Sample", "https://example.com", ("chromium",),
                    mode, automation, "test")


def test_manual_provider_without_session_is_manual_only():
    manager = ProviderConnectionManager([provider()])
    status = manager.get_status("sample")
    assert status.state is ConnectionState.MANUAL_ONLY


def test_confirmed_web_session_is_not_reported_as_api_ready():
    manager = ProviderConnectionManager([provider()])
    status = manager.get_status("sample", "authenticated_user_confirmed")
    assert status.state is ConnectionState.WEB_SESSION_CONFIRMED
    assert "no habilita" in status.detail


@pytest.mark.parametrize("session_state", [
    "awaiting_user", "captcha_required", "mfa_required", "reauthentication_required"
])
def test_authentication_challenges_require_manual_action(session_state):
    manager = ProviderConnectionManager([provider()])
    assert manager.get_status("sample", session_state).state is (
        ConnectionState.AUTHENTICATION_REQUIRED
    )


@pytest.mark.parametrize("session_state", ["browser_page_closed", "browser_session_closed"])
def test_closed_browser_is_unavailable(session_state):
    manager = ProviderConnectionManager([provider()])
    assert manager.get_status("sample", session_state).state is (
        ConnectionState.BROWSER_UNAVAILABLE
    )


def test_documented_api_without_adapter_is_not_configured():
    api_provider = provider("documented_api", True)
    manager = ProviderConnectionManager([api_provider])
    assert manager.get_status("sample").state is ConnectionState.API_NOT_CONFIGURED


def test_registered_documented_api_adapter_is_reported_ready():
    api_provider = provider("documented_api", True)

    class Adapter:
        provider_id = "sample"

        def send_message(self, conversation_id, message):
            return "ok"

    registry = AdapterRegistry()
    registry.register(api_provider, Adapter())
    manager = ProviderConnectionManager([api_provider], registry)
    assert manager.get_status("sample").state is ConnectionState.API_ADAPTER_READY


def test_disabled_provider_is_disabled():
    manager = ProviderConnectionManager([provider("disabled")])
    assert manager.get_status("sample").state is ConnectionState.DISABLED


def test_unknown_provider_is_rejected():
    manager = ProviderConnectionManager([provider()])
    with pytest.raises(KeyError, match="Unknown provider"):
        manager.get_status("missing")
