# Debian deployment

Target: Debian 12 (Bookworm) or newer, 64-bit desktop installation, Python 3.11+, and an active graphical session.

From a cloned repository, run:

```bash
bash scripts/install-debian.sh
```

The installer:
- installs Python and the system libraries needed by Qt and Playwright;
- creates an isolated virtual environment under `~/.local/opt/aztlan-route`;
- installs both Chromium and Firefox with their required runtime dependencies;
- creates a command at `~/.local/bin/aztlan-route` and a desktop launcher.

Uninstall with:

```bash
bash scripts/uninstall-debian.sh
```

By design, uninstall preserves local browser profiles and conversation history under the user's application data directory. Remove that directory manually only if permanent deletion is intended.
