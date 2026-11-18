# Aztlan-route

Aztlan-route is a local-first desktop application for organizing access to AI providers through user-owned browser sessions.

## Selected architecture

- Desktop application; browser profiles and session data remain on the user's device.
- Supports Firefox and Chromium through Playwright, with an explicit browser choice per launch.
- Provider adapters are isolated behind a small registry. A provider is not marked automation-compatible unless its published terms and supported integration path have been reviewed.
- Authentication is performed by the user in the provider's own website. The application does not collect passwords, export cookies, inspect private page internals, or bypass CAPTCHA, paywalls, quotas, or anti-automation controls.
- Persistent browser profiles are isolated by provider and protected by operating-system file permissions. OS credential storage is reserved for future application secrets; raw cookies are never copied into application configuration or logs.

## Current implementation scope

This initial scaffold provides:
- a desktop UI shell;
- a provider catalog with compatibility status;
- launch of an isolated Firefox or Chromium persistent browser profile at the provider's official website;
- local profile-directory permissions on POSIX systems;
- tests for provider validation and profile path isolation.

It does **not** automate chat submission or scrape provider responses. Those capabilities require a documented, permitted integration path for each provider.

## Development

Python 3.11+ is required.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
playwright install chromium firefox
aztlan-route
```

On Windows, activate with `.venv\\Scripts\\activate`.

## Configuration

Provider metadata lives in `config/providers.json`. The default catalog intentionally labels browser-only providers as `manual_browser`: opening an authenticated website is supported, but automated interaction is not implied.

## Security

See [docs/SECURITY.md](docs/SECURITY.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Never commit browser profiles, authentication state, API keys, or local configuration.

## License

License not yet selected.
