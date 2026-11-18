#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR="${HOME}/.local/opt/aztlan-route"
BIN_FILE="${HOME}/.local/bin/aztlan-route"
DESKTOP_FILE="${HOME}/.local/share/applications/aztlan-route.desktop"

rm -rf -- "$APP_DIR"
rm -f -- "$BIN_FILE" "$DESKTOP_FILE"

echo "Aplicación eliminada. Los perfiles y conversaciones locales se conservaron en:"
echo "${HOME}/.local/share/aztlan-route"
echo "Para borrarlos también, elimina esa carpeta manualmente después de respaldar lo necesario."
