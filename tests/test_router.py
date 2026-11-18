import pytest

from aztlan_route.adapters import AdapterRegistry, AdapterUnavailable
from aztlan_route.providers import Provider
from aztlan_route.router import ModelRouter


def provider(approved=False, mode="manual_browser"):
    return Provider("demo", "Demo", "https://example.com", ("chromium",),
                    mode, approved, "test")


def test_router_refuses_manual_browser_provider():
    router = ModelRouter(AdapterRegistry())
    with pytest.raises(AdapterUnavailable, match="manual browser"):
        router.route(provider(), "conversation", "hello")


def test_router_uses_registered_documented_adapter():
    class DemoAdapter:
        provider_id = "demo"

        def send_message(self, conversation_id, message):
            return f"{conversation_id}:{message}"

    item = provider(True, "documented_api")
    registry = AdapterRegistry()
    registry.register(item, DemoAdapter())
    assert ModelRouter(registry).route(item, "c1", "hello") == "c1:hello"


def test_registry_rejects_unapproved_adapter():
    class DemoAdapter:
        provider_id = "demo"

        def send_message(self, conversation_id, message):
            return message

    with pytest.raises(ValueError, match="not approved"):
        AdapterRegistry().register(provider(), DemoAdapter())
