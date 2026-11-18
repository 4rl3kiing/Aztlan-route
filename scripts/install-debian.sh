#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
  echo "No ejecutes este instalador como root; se solicitará sudo cuando sea necesario." >&2
  exit 1
fi
if ! command -v apt-get >/dev/null 2>&1; then
  echo "Este instalador requiere Debian o una distribución compatible con apt." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ASOUND_PACKAGE=libasound2
if ! apt-cache show "$ASOUND_PACKAGE" >/dev/null 2>&1 && apt-cache show libasound2t64 >/dev/null 2>&1; then
  ASOUND_PACKAGE=libasound2t64
fi

sudo apt-get update
sudo apt-get install -y \
  "$PYTHON_BIN" "${PYTHON_BIN}-venv" "${PYTHON_BIN}-pip" \
  ca-certificates libglib2.0-0 libnss3 libnspr4 libatk1.0-0 \
  libatk-bridge2.0-0 libatspi2.0-0 libx11-6 libxcomposite1 \
  libxdamage1 libxext6 libxfixes3 libxrandr2 libgbm1 libxcb1 \
  libxkbcommon0 "$ASOUND_PACKAGE"

APP_DIR="${HOME}/.local/opt/aztlan-route"
SOURCE_DIR="${APP_DIR}/source"
mkdir -p "$APP_DIR" "${HOME}/.local/bin" "${HOME}/.local/share/applications"
rm -rf -- "$SOURCE_DIR"
mkdir -p "$SOURCE_DIR"
cp -a "$ROOT_DIR/pyproject.toml" "$ROOT_DIR/README.md" "$ROOT_DIR/src" "$SOURCE_DIR/"

# Recreate the environment to prevent stale packages from surviving upgrades.
"${PYTHON_BIN}" -m venv --clear "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${APP_DIR}/.venv/bin/python" -m pip install --upgrade --force-reinstall "$SOURCE_DIR"

sudo "${APP_DIR}/.venv/bin/python" -m playwright install-deps chromium firefox
"${APP_DIR}/.venv/bin/python" -m playwright install chromium firefox

cat > "${HOME}/.local/bin/aztlan-route" <<EOF
#!/usr/bin/env bash
exec "${APP_DIR}/.venv/bin/aztlan-route" "\$@"
EOF
chmod 755 "${HOME}/.local/bin/aztlan-route"

cat > "${HOME}/.local/share/applications/aztlan-route.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Aztlan-route
Comment=Local desktop interface for permitted AI provider sessions
Exec=${HOME}/.local/bin/aztlan-route
Terminal=false
Categories=Network;Utility;
StartupNotify=true
EOF

echo "Instalación terminada."
echo "Ejecuta: ${HOME}/.local/bin/aztlan-route"
echo "Los perfiles e historial se conservan en la carpeta de datos XDG."
