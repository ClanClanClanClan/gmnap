#!/usr/bin/env bash
set -euo pipefail
BIN="$HOME/Library/Python/3.13/bin"
RC="$HOME/.zshrc"; [ -f "$HOME/.bash_profile" ] && RC="$HOME/.bash_profile"
LINE="export PATH=\"$PATH:$BIN\""
grep -q "$BIN" "$RC" 2>/dev/null || echo "$LINE" >> "$RC"
echo "Added $BIN to PATH in $RC"
