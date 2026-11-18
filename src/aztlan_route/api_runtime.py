"""Official OpenAI-compatible API runtime with safe fallback and local telemetry.

Secrets are read from environment variables at request time and are never persisted.
Only explicitly configured HTTPS API endpoints are contacted; browser sessions are
not used as API credentials.
"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class ProviderRequestError(RuntimeError):
    """Sanitized provider error; response bodies and credentials are not exposed."""

    def __init__(self, provider_id: str, message: str, *, status: int | None = None,
                 transient: bool = False) -> None:
        super().__init__(f"{provider_id}: {message}")
        self.provider_id = provider_id
        self.status = status
        self.transient = transient


@dataclass(frozen=True, slots=True)
class ApiProviderConfig:
    id: str
    name: str
    base_url: str
    api_key_env: str
    model_env: str
    priority: int = 100
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.id or not self.id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Invalid API provider id")
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("API base URL must be HTTPS and contain no user information")
        if parsed.query or parsed.fragment:
            raise ValueError("API base URL cannot contain query or fragment components")
        for name in (self.name, self.api_key_env, self.model_env):
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Provider name and environment variable names are required")
        if type(self.priority) is not int or self.priority < 0:
            raise ValueError("Provider priority must be a non-negative integer")
        if type(self.enabled) is not bool:
            raise ValueError("Provider enabled flag must be boolean")


def load_api_catalog(path: Path) -> list[ApiProviderConfig]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Unsupported API catalog schema")
    entries = payload.get("providers")
    if not isinstance(entries, list):
        raise ValueError("API catalog providers must be an array")
    providers = [ApiProviderConfig(**entry) for entry in entries]
    ids = [provider.id for provider in providers]
    if len(ids) != len(set(ids)):
        raise ValueError("API provider ids must be unique")
    return providers


@dataclass(slots=True)
class ProviderMetrics:
    requests: int = 0
    successes: int = 0
    failures: int = 0
    latencies_ms: list[float] = field(default_factory=list)

    def record(self, success: bool, elapsed_ms: float) -> None:
        self.requests += 1
        if success:
            self.successes += 1
        else:
            self.failures += 1
        self.latencies_ms.append(max(0.0, elapsed_ms))
        if len(self.latencies_ms) > 500:
            del self.latencies_ms[:-500]

    def snapshot(self) -> dict[str, int | float | None]:
        values = sorted(self.latencies_ms)
        def percentile(fraction: float) -> float | None:
            if not values:
                return None
            index = min(len(values) - 1, int((len(values) - 1) * fraction))
            return round(values[index], 2)
        return {
            "requests": self.requests,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": round(self.successes / self.requests, 4) if self.requests else None,
            "latency_p50_ms": percentile(0.50),
            "latency_p95_ms": percentile(0.95),
        }


@dataclass(slots=True)
class CircuitBreaker:
    failure_threshold: int = 3
    reset_after_seconds: float = 30.0
    failures: int = 0
    opened_at: float | None = None

    def __post_init__(self) -> None:
        if self.failure_threshold < 1 or self.reset_after_seconds <= 0:
            raise ValueError("Invalid circuit breaker configuration")

    @property
    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if time.monotonic() - self.opened_at >= self.reset_after_seconds:
            self.opened_at = None
            self.failures = 0
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.monotonic()


class OpenAICompatibleAdapter:
    """Adapter for a provider's documented OpenAI-compatible HTTPS API."""

    def __init__(self, config: ApiProviderConfig, model: str, *,
                 timeout: float = 60.0,
                 opener: Callable[..., Any] = urlopen) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("A model id must be configured explicitly")
        if timeout <= 0:
            raise ValueError("Timeout must be positive")
        self.config = config
        self.provider_id = config.id
        self.model = model
        self.timeout = timeout
        self._opener = opener

    def _build_request(self, payload: Mapping[str, Any]) -> Request:
        api_key = os.environ.get(self.config.api_key_env, "").strip()
        if not api_key:
            raise ProviderRequestError(self.provider_id, "API key is not configured")
        requested_model = payload.get("model", self.model)
        if requested_model != self.model:
            raise ValueError("Requested model does not match the configured provider model")
        messages = payload.get("messages")
        if (not isinstance(messages, list) or not messages
                or not all(isinstance(item, dict) and item.get("role") in {
                    "system", "developer", "user", "assistant", "tool"
                } and "content" in item for item in messages)):
            raise ValueError("messages must be a non-empty array of valid chat messages")
        allowed = {
            "temperature", "top_p", "max_tokens", "max_completion_tokens", "stop",
            "presence_penalty", "frequency_penalty", "seed", "response_format",
            "tools", "tool_choice", "parallel_tool_calls", "stream", "stream_options",
        }
        body = {"model": self.model, "messages": messages}
        for key in allowed:
            if key in payload:
                body[key] = payload[key]
        if "stream" in body and type(body["stream"]) is not bool:
            raise ValueError("stream must be a boolean")
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if body.get("stream") else "application/json",
            "User-Agent": "Aztlan-route/0.1",
        }
        return Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")

    def complete(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = self._build_request(payload)
        try:
            with self._opener(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            transient = exc.code == 429 or exc.code == 408 or exc.code >= 500
            raise ProviderRequestError(self.provider_id, "HTTP request failed",
                                       status=exc.code, transient=transient) from None
        except (URLError, TimeoutError, ConnectionError):
            raise ProviderRequestError(self.provider_id, "network request failed",
                                       transient=True) from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProviderRequestError(self.provider_id, "provider returned invalid JSON") from None
        if not isinstance(result, dict) or not isinstance(result.get("choices"), list):
            raise ProviderRequestError(self.provider_id, "provider response has an invalid schema")
        return result

    def stream(self, payload: Mapping[str, Any]) -> Iterator[str]:
        if payload.get("stream", True) is not True:
            raise ValueError("Streaming request must set stream=true")
        request = self._build_request({**payload, "stream": True})
        try:
            with self._opener(request, timeout=self.timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        if data == "[DONE]":
                            yield "data: [DONE]\n\n"
                            return
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            raise ProviderRequestError(
                                self.provider_id, "provider emitted invalid streaming data"
                            ) from None
                        if not isinstance(chunk, dict) or not isinstance(chunk.get("choices", []), list):
                            raise ProviderRequestError(
                                self.provider_id, "provider emitted an invalid streaming chunk"
                            )
                        yield "data: " + json.dumps(chunk, separators=(",", ":")) + "\n\n"
        except HTTPError as exc:
            transient = exc.code == 429 or exc.code == 408 or exc.code >= 500
            raise ProviderRequestError(self.provider_id, "HTTP streaming request failed",
                                       status=exc.code, transient=transient) from None
        except (URLError, TimeoutError, ConnectionError):
            raise ProviderRequestError(self.provider_id, "streaming network request failed",
                                       transient=True) from None


class OpenAICompatibleRouter:
    """Priority router with per-provider circuit breakers and bounded telemetry."""

    def __init__(self, adapters: Sequence[OpenAICompatibleAdapter], *,
                 failure_threshold: int = 3, reset_after_seconds: float = 30.0) -> None:
        self._adapters = sorted(adapters, key=lambda adapter: adapter.config.priority)
        if len({adapter.provider_id for adapter in self._adapters}) != len(self._adapters):
            raise ValueError("API adapter provider ids must be unique")
        self._breakers = {
            adapter.provider_id: CircuitBreaker(failure_threshold, reset_after_seconds)
            for adapter in self._adapters
        }
        self._metrics = {adapter.provider_id: ProviderMetrics() for adapter in self._adapters}

    def metrics(self) -> dict[str, dict[str, int | float | None]]:
        return {provider_id: metric.snapshot() for provider_id, metric in self._metrics.items()}

    def complete(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        errors: list[ProviderRequestError] = []
        for adapter in self._adapters:
            breaker = self._breakers[adapter.provider_id]
            if breaker.is_open:
                continue
            started = time.monotonic()
            try:
                result = adapter.complete(payload)
            except ProviderRequestError as exc:
                self._metrics[adapter.provider_id].record(False, (time.monotonic() - started) * 1000)
                if exc.transient:
                    breaker.record_failure()
                    errors.append(exc)
                    continue
                raise
            self._metrics[adapter.provider_id].record(True, (time.monotonic() - started) * 1000)
            breaker.record_success()
            return result
        if errors:
            raise errors[-1]
        raise ProviderRequestError("router", "no eligible API provider is available", transient=True)

    def stream(self, payload: Mapping[str, Any]) -> Iterator[str]:
        errors: list[ProviderRequestError] = []
        for adapter in self._adapters:
            breaker = self._breakers[adapter.provider_id]
            if breaker.is_open:
                continue
            started = time.monotonic()
            iterator = adapter.stream(payload)
            try:
                first = next(iterator)
            except StopIteration:
                self._metrics[adapter.provider_id].record(True, (time.monotonic() - started) * 1000)
                breaker.record_success()
                return
            except ProviderRequestError as exc:
                self._metrics[adapter.provider_id].record(False, (time.monotonic() - started) * 1000)
                if exc.transient:
                    breaker.record_failure()
                    errors.append(exc)
                    continue
                raise
            yield first
            try:
                yield from iterator
            except ProviderRequestError:
                self._metrics[adapter.provider_id].record(
                    False, (time.monotonic() - started) * 1000
                )
                breaker.record_failure()
                raise
            self._metrics[adapter.provider_id].record(
                True, (time.monotonic() - started) * 1000
            )
            breaker.record_success()
            return
        if errors:
            raise errors[-1]
        raise ProviderRequestError("router", "no eligible API provider is available", transient=True)


def build_configured_adapters(
    catalog: Sequence[ApiProviderConfig], *,
    environ: Mapping[str, str] | None = None,
) -> list[OpenAICompatibleAdapter]:
    """Build adapters only when both a key and explicit model are configured."""
    values = os.environ if environ is None else environ
    result = []
    for config in catalog:
        if not config.enabled:
            continue
        model = values.get(config.model_env, "").strip()
        key = values.get(config.api_key_env, "").strip()
        if model and key:
            result.append(OpenAICompatibleAdapter(config, model))
    return result
