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
- Non-blocking authentication wait state per browser session, with conservative CAPTCHA/MFA challenge indicators and explicit operator confirmation.
- Failed page navigation triggers context cleanup to release profile locks.
- Provider catalog validation and adapter contract.
- Deterministic router for approved documented adapters.
- Local conversation persistence and profile discovery.
- Debian installer and desktop launcher with preservation of local user data.
- Unit tests plus a CI smoke job that launches real Chromium and Firefox persistent contexts.

The current provider catalog uses `manual_browser`. These entries open official websites but do not automate chat submission or scrape responses. During sign-in, Aztlan-route keeps the browser open and periodically checks only the page URL, title and common visible CAPTCHA/MFA elements. The user completes every challenge directly with the provider and explicitly confirms successful sign-in in the desktop UI. Challenge detection is heuristic; absence of a challenge is never treated as proof of authentication. The confirmation records the operator's statement only and does not establish API access. No production provider API adapter is enabled until its documented interface and permitted use have been reviewed.

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
