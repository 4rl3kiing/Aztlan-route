# Aztlán Route Mobile

Android MVP alpha. This application is intentionally isolated under `android/`; it does not replace or alter the Python desktop application.

## Current scope
- Native Android launchable application.
- Manual opening of official provider websites in the external browser.
- No cookie/session extraction, CAPTCHA automation, browser scraping, or automated website chat submission.
- No API key storage or model chat runtime in this alpha build.

## Build
Requires JDK 17 and Android SDK Platform 35. From this directory:

```sh
gradle assembleDebug
```

APK output: `app/build/outputs/apk/debug/app-debug.apk`.

## Next milestones
1. Import and validate the existing provider catalog.
2. Add encrypted API credential storage backed by Android Keystore.
3. Implement provider API adapters and connection checks.
4. Add local conversation persistence and tests.
