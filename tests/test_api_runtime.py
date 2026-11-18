import json
from pathlib import Path

import pytest

from aztlan_route.api_runtime import (
    ApiProviderConfig,
    OpenAICompatibleAdapter,
    OpenAICompatibleRouter,
    ProviderRequestError,
    build_configured_adapters,
    load_api_catalog,
)


def config(provider_id="groq", priority=10):
    return ApiProviderConfig(
        provider_id, "Test", "https://api.example.test/v1",
        "TEST_API_KEY", "TEST_MODEL", priority,
    )


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def test_catalog_loads_official_api_presets():
    path = Path(__file__).parents[1] / "src" / "aztlan_route" / "api_providers.json"
    providers = load_api_catalog(path)
    assert [item.id for item in providers] == ["groq", "cerebras", "mistral", "openrouter"]


def test_build_activates_only_providers_with_key_and_model():
    provider = config()
    assert build_configured_adapters(
        [provider], environ={"TEST_API_KEY": "secret"}
    ) == []
    adapters = build_configured_adapters(
        [provider], environ={"TEST_API_KEY": "secret", "TEST_MODEL": "model-a"}
    )
    assert len(adapters) == 1
    assert adapters[0].model == "model-a"


def test_catalog_rejects_non_https_and_url_credentials():
    with pytest.raises(ValueError, match="HTTPS"):
        config_obj = ApiProviderConfig(
            "bad", "Bad", "http://api.example.test/v1", "KEY", "MODEL"
        )
        assert config_obj
    with pytest.raises(ValueError, match="user information"):
        ApiProviderConfig("bad", "Bad", "https://user:pass@example.test/v1", "KEY", "MODEL")


def test_adapter_sends_openai_compatible_request_without_persisting_key(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "test-secret")
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data)
        return FakeResponse(json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode())

    adapter = OpenAICompatibleAdapter(config(), "model-a", opener=opener)
    result = adapter.complete({"messages": [{"role": "user", "content": "hello"}]})
    assert result["choices"][0]["message"]["content"] == "ok"
    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert captured["auth"] == "Bearer test-secret"
    assert captured["body"]["model"] == "model-a"
    assert "test-secret" not in repr(adapter)


def test_adapter_requires_explicit_key_and_model(monkeypatch):
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    adapter = OpenAICompatibleAdapter(config(), "model-a")
    with pytest.raises(ProviderRequestError, match="API key is not configured"):
        adapter.complete({"messages": [{"role": "user", "content": "hello"}]})


def test_adapter_rejects_model_override(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret")
    adapter = OpenAICompatibleAdapter(config(), "model-a")
    with pytest.raises(ValueError, match="configured provider model"):
        adapter.complete({"model": "other", "messages": [{"role": "user", "content": "hi"}]})


def test_router_falls_back_after_transient_provider_failure():
    class Broken:
        provider_id = "broken"
        config = config_obj = ApiProviderConfig(
            "broken", "Broken", "https://broken.example/v1", "K1", "M1", 1
        )

        def complete(self, _payload):
            raise ProviderRequestError("broken", "offline", transient=True)

    class Working:
        provider_id = "working"
        config = ApiProviderConfig(
            "working", "Working", "https://working.example/v1", "K2", "M2", 2
        )

        def complete(self, _payload):
            return {"choices": [{"message": {"content": "fallback"}}]}

    router = OpenAICompatibleRouter([Working(), Broken()])
    result = router.complete({"messages": [{"role": "user", "content": "hi"}]})
    assert result["choices"][0]["message"]["content"] == "fallback"
    assert router.metrics()["broken"]["failures"] == 1
    assert router.metrics()["working"]["successes"] == 1


def test_router_does_not_retry_non_transient_authentication_failure():
    class Unauthorized:
        provider_id = "unauthorized"
        config = ApiProviderConfig("unauthorized", "Unauthorized",
                                   "https://unauth.example/v1", "K", "M", 1)

        def complete(self, _payload):
            raise ProviderRequestError("unauthorized", "HTTP request failed",
                                       status=401, transient=False)

    class MustNotRun:
        provider_id = "second"
        config = ApiProviderConfig("second", "Second",
                                   "https://second.example/v1", "K2", "M2", 2)

        def complete(self, _payload):
            raise AssertionError("must not fall back after invalid credentials")

    router = OpenAICompatibleRouter([Unauthorized(), MustNotRun()])
    with pytest.raises(ProviderRequestError):
        router.complete({"messages": [{"role": "user", "content": "hi"}]})
