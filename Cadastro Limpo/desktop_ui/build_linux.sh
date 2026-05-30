#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${TOOLS_DIR}"
python -m pip install --upgrade pip
python -m pip install pyinstaller
pyinstaller \
  --noconfirm \
  --windowed \
  --name cadastro-limpo \
  --icon "${SCRIPT_DIR}/icon.png" \
  --add-data "${SCRIPT_DIR}/icon.png:desktop_ui" \
  --add-data "${TOOLS_DIR}/patterns.json:." \
  --paths "${TOOLS_DIR}" \
  desktop_ui/main.py
