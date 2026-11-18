# Debian deployment

From a cloned repository, run:

```bash
chmod +x scripts/install-debian.sh
./scripts/install-debian.sh
```

The installer uses a private virtual environment under `~/.local/opt/aztlan-route`, installs Chromium and Firefox with Playwright's Debian dependency installer, and creates a desktop launcher.

Supported target: Debian 12 (Bookworm) or newer, 64-bit desktop installation, Python 3.11+. A graphical session is required to launch the desktop UI.

Uninstall with `scripts/uninstall-debian.sh`. By design, uninstall preserves local browser profiles and conversation history under the user's data directory.
