# Technical architecture

## Deployment

Aztlan-route is a desktop-first, single-user application for Windows and Debian Linux. Browser profiles and conversation history remain on the local device. No remote browser farm or account/session synchronization is included.

## Components

1. **Desktop shell (PySide6):** provider selection, browser selection, local profile inventory and session launch.
2. **Provider catalog:** validated metadata loaded from a versioned JSON resource. Provider IDs are stable identifiers.
3. **Browser runtime (Playwright):** persistent Firefox or Chromium contexts. Every provider/browser pair has its own profile path.
4. **Session manager:** discovers profile directories without reading cookies, passwords, tokens or browser storage.
5. **Adapter contract and registry:** only providers explicitly marked as approved documented integrations can register an automated adapter.
6. **Model router:** dispatches to a registered adapter and rejects empty/oversized messages or unsupported providers.
7. **Conversation store:** SQLite persistence for conversation metadata and message text. It never stores browser authentication state.
8. **Local data boundary:** OS-specific application data directory, separate from source and install directories.

## Runtime flows

### Manual browser session

1. User selects provider and browser.
2. Catalog validation checks HTTPS URL, provider ID, browser support and integration mode.
3. Runtime rejects a second launch for an already-open provider/browser profile.
4. A dedicated Qt worker thread creates a provider-specific profile directory with restrictive POSIX permissions.
5. Browser opens the provider's official website; failed navigation closes the partially-created context.
6. A worker-thread timer checks the active page URL, title, common visible CAPTCHA/MFA elements and the presence of a password form; it does not read page body text or authentication storage.
7. CAPTCHA and MFA remain user-operated on the provider website. The UI reports detected challenges and waits without blocking the Qt event loop.
8. The operator explicitly confirms successful sign-in. This is recorded as user-confirmed, not independently verified, and does not imply API/chat integration.
9. Monitoring continues after confirmation. A recognizable sign-in route or password form changes the state to reauthentication-required; a closed final tab is reported separately.
10. Reauthentication brings the existing provider tab forward or reopens the provider's official URL in the same persistent profile. The user completes sign-in manually.
11. The UI lists active sessions and allows each session to be closed independently.
12. Application shutdown attempts to close every remaining session, even if another session reports a cleanup error.
13. The browser profile persists for the next session.

### Documented adapter conversation

1. Provider metadata must explicitly declare `documented_api` and `automation_allowed=true`.
2. A reviewed adapter is registered for that provider ID.
3. The router validates message input and resolves the adapter.
4. Adapter performs the request through the documented, permitted interface.
5. ConversationStore persists the user's message and adapter response when called by the conversation workflow.

No provider adapter is enabled by default in this repository. The initial provider catalog is manual-browser only.

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
