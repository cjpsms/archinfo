#!/usr/bin/env bash
# Put `archinfo` on your PATH as a symlink to this checkout.
set -euo pipefail
dir="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.local/bin"
chmod +x "$dir/archinfo.py"
ln -sf "$dir/archinfo.py" "$HOME/.local/bin/archinfo"
echo "installed: ~/.local/bin/archinfo -> $dir/archinfo.py"
command -v checkupdates >/dev/null || echo "tip: sudo pacman -S pacman-contrib  (live update count via checkupdates)"
