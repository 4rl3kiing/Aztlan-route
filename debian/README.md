# Debian deployment

Target: Debian 12 (Bookworm) or newer, 64-bit desktop installation, Python 3.11+, and an active graphical session.

From a cloned repository, run:

```bash
bash scripts/install-debian.sh
```

The installer:
- installs Python and the system libraries needed by Qt and Playwright;
- stages only `pyproject.toml`, `README.md` and the application source under `~/.local/opt/aztlan-route/source` (it does not copy Git metadata, virtual environments, profiles or local data);
- recreates the isolated virtual environment on every installation to prevent stale package files;
- installs both Chromium and Firefox with their required runtime dependencies;
- creates a command at `~/.local/bin/aztlan-route` and a desktop launcher.

Uninstall with:

```bash
bash scripts/uninstall-debian.sh
```

By design, uninstall preserves local browser profiles and conversation history in the platformdirs XDG data directory: `${XDG_DATA_HOME:-~/.local/share}/Aztlan/Aztlan-route`. It also preserves Playwright's shared browser cache at `~/.cache/ms-playwright`.
