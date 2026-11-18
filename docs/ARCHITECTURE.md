# Technical architecture

## Deployment

Aztlan-route is a desktop-first, single-user application for Windows and Debian Linux. Browser profiles and conversation history remain on the local device. No remote browser farm or account/session synchronization is included.

## Components

1. **Desktop shell (PySide6):** provider selection, browser selection, local profile inventory and session launch.
2. **Provider catalog:** validated metadata loaded from a versioned JSON resource. Provider IDs are stable identifiers.
3. **Browser runtime (Playwright):** persistent Firefox or Chromium contexts. Every provider/browser pair has its own profile path.
4. **Session manager:** discovers profile directories without reading cookies, passwords, tokens or browser storage.
5. **Adapter contract and registry:** only providers explicitly marked as approved documented integrations can register an automated adapter.
6. **Provider connection manager:** derives conservative capability states from catalog policy, registered adapters and browser-session signals. It never equates web login with API access.
7. **Model router:** dispatches to a registered adapter and rejects empty/oversized messages or unsupported providers.
8. **Conversation store:** SQLite persistence for conversation metadata and message text. It never stores browser authentication state.
9. **Local data boundary:** OS-specific application data directory, separate from source and install directories.

## Runtime flows

### Manual browser session

1. User selects provider and browser.
2. Catalog validation checks HTTPS URL, provider ID, browser support and integration mode.
3. Runtime rejects a second launch for an already-open provider/browser profile.
4. A dedicated Qt worker thread creates a provider-specific profile directory with restrictive POSIX permissions.
5. Browser opens the provider's official website; failed navigation closes the partially-created context.
6. A worker-thread timer checks the active page URL and narrowly-scoped visible CAPTCHA/MFA elements; generic titles, query-string markers and arbitrary password forms are ignored to reduce false positives. It does not read page body text or authentication storage.
7. CAPTCHA and MFA remain user-operated on the provider website. The UI reports detected challenges and waits without blocking the Qt event loop.
8. The operator explicitly confirms successful sign-in. This is recorded as user-confirmed, not independently verified, and does not imply API/chat integration.
9. Monitoring continues after confirmation. A recognizable sign-in route or password form changes the state to reauthentication-required; a closed final tab or browser context is reported separately.
10. Reauthentication brings the existing provider tab forward, reopens the official URL in the existing context, or recreates a closed context using the same persistent profile. The user completes sign-in manually.
11. The UI lists active sessions and allows each session to be closed independently.
12. Session closure is queued to each browser worker so Playwright calls do not block the Qt event loop; application shutdown waits asynchronously for worker completion and attempts to close every remaining session.
13. The browser profile persists for the next session.

### Documented adapter conversation

1. Provider metadata must explicitly declare `documented_api` and `automation_allowed=true`.
2. A reviewed adapter is registered for that provider ID.
3. The router validates message input and resolves the adapter.
4. Adapter performs the request through the documented, permitted interface.
5. ConversationStore persists the user's message and adapter response when called by the conversation workflow.

No provider adapter is enabled by default in this repository. The initial provider catalog is manual-browser only.

### Centralized provider status

The connection manager distinguishes disabled providers, manual-only browser access, pending manual authentication, user-confirmed web sessions, closed browser contexts, missing API adapters and registered API adapters. A registered adapter is only a local capability signal: remote reachability, credentials, quota and model availability require a separate documented health check. A browser login confirmation never changes a manual-browser provider into an API-capable provider.

## Debian

The Debian installer creates a private virtual environment, installs Playwright browser dependencies and Chromium/Firefox, and creates a desktop entry. Target is Debian 12+ on 64-bit desktop systems with Python 3.11+.

## Planned extension points

- OS credential vault integration for application-owned secrets (Windows Credential Manager, macOS Keychain or Secret Service).
- Reviewed adapters for documented APIs or expressly authorized provider integrations.
- Session health checks that do not inspect or export authentication material.
- Provider-specific, documented authentication-completion checks where officially supported.
- Unified chat UI only for providers with supported integration paths.
- Background browser launch workers and graceful session lifecycle management.

## Non-goals

CAPTCHA solving, fingerprint spoofing, proxy rotation to evade quotas, paywall bypass, hidden endpoint reverse engineering, cookie extraction, and automated use contrary to provider terms are out of scope.

## Official API router extension

The independent `api_runtime` module provides:
- a validated HTTPS endpoint catalog with no embedded credentials;
- OpenAI-compatible `/chat/completions` requests and SSE event forwarding;
- explicit model selection per provider via environment configuration;
- per-provider circuit breakers and bounded local latency/success telemetry;
- fallback on transient transport, rate-limit and server errors only.

API credentials are read from the process environment for each request and are not
written to SQLite, browser profiles, logs or catalog files. A confirmed browser login
is not accepted as an API key or authorization mechanism. Model IDs are operator
configured because availability and naming change over time.

The first implementation is backend-only. The next integration stage is to connect
this router to the desktop conversation workflow and add an explicit settings UI for
provider order, model IDs and secret storage using an OS credential vault. Streaming
fallback is deliberately prohibited after the first event to avoid mixing partial
answers from different providers.

## Independent TypeScript router service

`services/ai-browser-router` is a separately deployable Node.js service alongside the Python/PySide6 desktop application. Its provider catalog is declarative YAML. The schema permits only provider identity, HTTPS base URL, environment-variable name for the API key, enabled state and model metadata. It does not accept module paths, hook names, selectors, scripts or arbitrary request templates.

The initial service exposes `/health`, `/v1/models` and `/v1/chat/completions`, forwards JSON and SSE from documented OpenAI-compatible HTTPS APIs, and binds to loopback by default. The initial implementation intentionally has no cross-provider fallback, admin API, browser adapter or session store. Browser sign-in remains a user-controlled desktop workflow, not an API credential.
