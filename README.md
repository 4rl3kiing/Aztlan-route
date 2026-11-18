# Aztlan-route

Aztlan-route is a local-first desktop application for organizing access to AI providers through user-owned browser sessions.

## Selected architecture

- Desktop application for Windows and Debian Linux.
- Firefox and Chromium through Playwright, with a separate persistent profile for each provider/browser pair.
- Provider catalog with explicit integration modes.
- Adapter registry and router that reject providers without a reviewed, documented integration.
- Local SQLite conversation history; browser authentication material is not copied into this database.
- User authentication takes place on the provider's official website. No password collection, cookie export, CAPTCHA bypass, paywall bypass, quota evasion, or anti-automation circumvention.

## Implemented

- PySide6 desktop shell and provider selection.
- Persistent Chromium and Firefox profiles, each isolated by provider/browser.
- Playwright runs on dedicated Qt worker threads rather than blocking the UI thread.
- Active browser-session list, individual session closure and duplicate-profile launch prevention.
- Non-blocking authentication wait state per browser session, with conservative CAPTCHA/MFA and expired-login indicators.
- Periodic session-state checks, closed-tab detection and reauthentication using the same persistent browser profile.
- Failed page navigation triggers context cleanup to release profile locks.
- Provider catalog validation and adapter contract.
- Deterministic router for approved documented adapters.
- Central provider connection manager with explicit manual-session, API-adapter, authentication-required and unavailable states.
- Desktop capability panel that distinguishes a user-confirmed web session from programmatic API readiness.
- Local conversation persistence and profile discovery.
- Debian installer and desktop launcher with preservation of local user data.
- Unit tests plus a CI smoke job that launches real Chromium and Firefox persistent contexts.

The connection panel reports `manual_browser` providers as manual-only, authentication-required, browser-unavailable or user-confirmed web sessions. A user-confirmed browser session is never represented as API connectivity. A `documented_api` provider is reported as adapter-ready only when an approved adapter is registered; this state still does not prove remote service health. No API keys or credentials are collected or stored by the connection manager.

The current provider catalog uses `manual_browser`. These entries open official websites but do not automate chat submission or scrape responses. During sign-in, Aztlan-route keeps the browser open and periodically checks the page URL and narrowly-scoped visible CAPTCHA/MFA elements. Generic page titles, query-string words and arbitrary password forms are not treated as authentication challenges. The user completes every challenge directly with the provider and explicitly confirms successful sign-in in the desktop UI. Challenge detection is heuristic; absence of a challenge is never treated as proof of authentication. The confirmation records the operator's statement only and does not establish API access. If the provider returns to a recognizable sign-in page or the browser tab is closed, the UI reports the state and offers to reopen the official provider page in the same profile for manual reauthentication. No production provider API adapter is enabled until its documented interface and permitted use have been reviewed.

## Debian installation

On Debian 12 or newer:

```bash
bash scripts/install-debian.sh
```

See [Debian deployment notes](debian/README.md).

## Windows / development installation

Python 3.11+:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m playwright install chromium firefox
aztlan-route
```

## Development tests

```bash
python -m pip install -e ".[dev]"
python -m compileall -q src tests
python -m ruff check src tests
python -m pytest
```

## Security

See [docs/SECURITY.md](docs/SECURITY.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Never commit browser profiles, authentication state, API keys, or local configuration.

## License

No license has been selected. All rights remain reserved by default; do not redistribute until a license is chosen.

## Official API router (initial implementation)

The API runtime is separate from the manual browser-session subsystem. It supports
documented OpenAI-compatible HTTPS chat-completion endpoints, request/response JSON,
and SSE streaming. The initial preset catalog contains Groq, Cerebras, Mistral and
OpenRouter endpoints. Presets do not claim that a plan is free or that a model is
available: the operator must select a current model ID and supply an API key.

Configure credentials only as process environment variables; do not put keys in
provider JSON, source control, conversation history or browser profiles:

| Provider | API key variable | Model variable |
| --- | --- | --- |
| Groq | `GROQ_API_KEY` | `AZTLAN_GROQ_MODEL` |
| Cerebras | `CEREBRAS_API_KEY` | `AZTLAN_CEREBRAS_MODEL` |
| Mistral | `MISTRAL_API_KEY` | `AZTLAN_MISTRAL_MODEL` |
| OpenRouter | `OPENROUTER_API_KEY` | `AZTLAN_OPENROUTER_MODEL` |

Only entries with both variables configured are activated. The router orders active
providers by catalog priority, uses a per-provider circuit breaker, retries another
provider only for transient network/rate-limit/server errors, and exposes bounded
local p50/p95 latency and success metrics. Authentication/configuration errors are
not silently retried. Streaming fallback is allowed only before the first event;
after output begins, a stream failure is surfaced rather than splicing two model
responses together.

This initial runtime is a backend extension point; it does not yet add a chat-completion
HTTP server or connect the desktop chat UI. It does not include Google AI Studio's
native Gemini protocol, local inference endpoints, web-session scraping, cookie reuse,
CAPTCHA solving, anti-bot evasion, or quota circumvention. Provider quotas and free
tiers are subject to each provider's current terms and account limits.

## TypeScript AI Router service

A separate Node.js 20+ service now lives in `services/ai-browser-router`. It reads provider definitions from YAML as data, validates them, and exposes a loopback-only OpenAI-compatible HTTP surface:

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions` (including upstream SSE forwarding)

The first catalog includes documented HTTPS API endpoints for Groq, OpenRouter, Mistral, Cerebras and OpenAI. API keys are read from environment variables; YAML cannot name executable hooks or browser selectors. See `services/ai-browser-router/README.md` for setup and security boundaries. The browser-session subsystem remains manual-only and is not used as an API transport.
