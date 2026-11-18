#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR="${HOME}/.local/opt/aztlan-route"
BIN_FILE="${HOME}/.local/bin/aztlan-route"
DESKTOP_FILE="${HOME}/.local/share/applications/aztlan-route.desktop"
DATA_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}/Aztlan-route"

rm -rf -- "$APP_DIR"
rm -f -- "$BIN_FILE" "$DESKTOP_FILE"

echo "Aplicación eliminada. Los perfiles y conversaciones locales se conservaron en:"
echo "$DATA_DIR"
echo "Para borrarlos también, elimina esa carpeta manualmente después de respaldar lo necesario."
echo "La caché de navegadores de Playwright (~/.cache/ms-playwright) se conserva y puede borrarse manualmente si ya no la usa otra aplicación."
