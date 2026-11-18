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
