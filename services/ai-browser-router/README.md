# Aztlan AI Router

Independent TypeScript service alongside the existing Python/PySide6 desktop application.

## Scope and trust boundaries

- Provider definitions are YAML data; they cannot name modules, scripts, hooks, selectors, or executable code.
- Only HTTPS OpenAI-compatible API endpoints are supported in this first increment.
- API credentials are read from environment variables and must not be stored in YAML, source control, browser profiles, or logs.
- The service binds to loopback by default. Remote binding is refused unless explicitly enabled; remote deployments require an authenticated gateway and TLS.
- Browser-based chat scraping, cookie/token extraction, CAPTCHA/MFA bypass, anti-bot circumvention, and proof-of-work bypass are out of scope.
- A signed-in browser profile is not treated as an API credential or API transport.

## Run

Requires Node.js 20 or newer.

```sh
cd services/ai-browser-router
npm install
cp .env.example .env
# Export the provider keys needed by your deployment.
npm run doctor
npm run build
npm start
```

Endpoints: `GET /health`, `GET /v1/models`, and `POST /v1/chat/completions`.

The first release intentionally implements a single selected provider per request. Automatic cross-provider fallback, admin endpoints, persistent session state, and browser adapters are not enabled until their security and compatibility contracts are separately tested.
