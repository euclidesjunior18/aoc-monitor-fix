#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications"

echo "Instalando script em ~/.local/bin/aoc-monitor-fix..."
cp "$DIR/src/main.py" "$HOME/.local/bin/aoc-monitor-fix"
chmod +x "$HOME/.local/bin/aoc-monitor-fix"

echo "Instalando atalho em ~/.local/share/applications/aoc-monitor-fix.desktop..."
cp "$DIR/desktop/aoc-monitor-fix.desktop" "$HOME/.local/share/applications/"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "Concluído com sucesso!"
