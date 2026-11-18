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

sudo apt-get update
sudo apt-get install -y \
  "${PYTHON_BIN}" "${PYTHON_BIN}-venv" "${PYTHON_BIN}-pip" \
  ca-certificates curl libglib2.0-0 libnss3 libnspr4 libatk1.0-0 \
  libatk-bridge2.0-0 libatspi2.0-0 libx11-6 libxcomposite1 \
  libxdamage1 libxext6 libxfixes3 libxrandr2 libgbm1 libxcb1 \
  libxkbcommon0 libasound2

APP_DIR="${HOME}/.local/opt/aztlan-route"
DATA_DIR="${HOME}/.local/share/aztlan-route"
mkdir -p "${APP_DIR}" "${DATA_DIR}" "${HOME}/.local/bin" "${HOME}/.local/share/applications"
cp -a "${ROOT_DIR}/." "${APP_DIR}/"

"${PYTHON_BIN}" -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${APP_DIR}/.venv/bin/python" -m pip install "${APP_DIR}"

# Install both browser engines and their Debian runtime libraries.
"${APP_DIR}/.venv/bin/python" -m playwright install-deps chromium firefox
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
echo "Si ~/.local/bin no está en PATH, usa la ruta completa."
