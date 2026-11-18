# Technical architecture

## Deployment

Aztlan-route is a desktop-first, single-user application. Provider browser profiles remain on the user's device. No remote browser farm or account/session synchronization is included.

## Components

1. Desktop shell (PySide6): provider selection, browser selection and session workspace.
2. Provider catalog: validated metadata loaded from versioned JSON.
3. Browser runtime (Playwright): persistent Firefox or Chromium contexts, isolated by provider/browser pair.
4. Local data boundary: profiles under the OS-specific application data directory, never in the repository.
5. Provider adapter boundary: manual browsing is the default. Automated interaction requires a documented, permitted interface and explicit review.

## Runtime flow

1. User selects provider and browser.
2. Catalog validation checks HTTPS URL, provider ID, browser support and integration mode.
3. Runtime creates a provider-specific profile directory with restrictive POSIX permissions.
4. Browser opens the provider's official website.
5. User signs in and operates the site directly.
6. Browser profile persists for the next session.

## Planned extension points

- OS credential vault integration for application-owned secrets (Windows Credential Manager, macOS Keychain or Secret Service).
- Adapter SDK for documented APIs or explicitly authorized integrations.
- Session health checks that do not inspect or export authentication material.
- Unified conversation UI only for providers with supported integration paths.

## Non-goals

CAPTCHA solving, fingerprint spoofing, proxy rotation to evade quotas, paywall bypass, hidden endpoint reverse engineering, cookie extraction, and automated use contrary to provider terms are out of scope.
