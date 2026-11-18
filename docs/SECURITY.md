# Security model

## Protected assets

Provider authentication state and browser cookies, local browser profiles, user prompts, provider catalog integrity and application updates.

## Controls in this scaffold

- HTTPS-only provider destinations.
- Shared strict provider ID validation (ASCII, 1-64 characters) across catalog, browser profiles and conversation storage.
- Provider catalog type validation; automation flags must be real booleans and browser lists are normalized before use.
- Disabled providers are excluded from the UI and rejected by the browser launcher.
- Separate persistent profile directory per provider and browser.
- POSIX profile directories and SQLite parent directory restricted to mode 0700; SQLite database restricted to mode 0600.
- SQLite connections are closed deterministically after each operation.
- No cookie, password, token or browser storage export.
- No secrets in provider catalog, source code or logs.
- No provider page DOM scraping or chat automation.
- Playwright runs on dedicated Qt worker threads; each session is closed independently during application shutdown.

## Required before production

- Use OS-native credential storage for application-owned secrets; do not implement custom cryptography.
- Apply restrictive ACLs to profile directories on Windows and verify supported filesystems.
- Add signed release artifacts and update integrity verification.
- Add dependency pinning/lockfile, vulnerability scanning, SBOM and reproducible build checks.
- Define data retention, secure logout/profile deletion and backup behavior.
- Threat-model local malware, shared-device access, crash dumps, diagnostic bundles and malicious provider content.
- Review provider terms and document a permitted integration route before enabling automated adapters.

## User guidance

Treat the operating-system user account as the security boundary. Use full-disk encryption and lock the device when unattended. Do not copy profile folders to shared/cloud storage unless the risk is accepted.
