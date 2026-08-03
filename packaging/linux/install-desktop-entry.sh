#!/usr/bin/env bash
# Installs FaTest as an application with an icon in the menu (Linux).
# Launches `fatest` in the user's default terminal, just like any other app.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DESKTOP_SRC="$SCRIPT_DIR/fatest.desktop"
ICON_SRC="$REPO_ROOT/assets/fatest-256.png"

APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

mkdir -p "$APPS_DIR" "$ICONS_DIR"

if ! command -v fatest >/dev/null 2>&1; then
    echo "Note: the 'fatest' command was not found on your PATH."
    echo "Build and install it first — see the README's 'Build from source' section."
    echo "(Installing the shortcut anyway — it will start working once 'fatest' is on PATH.)"
fi

cp "$ICON_SRC" "$ICONS_DIR/fatest.png"
cp "$DESKTOP_SRC" "$APPS_DIR/fatest.desktop"
chmod +x "$APPS_DIR/fatest.desktop"

# Refresh menu/icon caches, if the tools are available
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS_DIR" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "Done. FaTest should now appear in your application menu with its icon."
echo "Launching it opens your default terminal and starts 'fatest' — its interactive menu."
