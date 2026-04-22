#!/usr/bin/env bash
#
# Install the fastText CLI binary for GMNAP.
#
# Usage:
#   scripts/install_fasttext.sh             # installs to ~/.local/bin/fasttext
#   scripts/install_fasttext.sh /usr/local/bin/fasttext   # custom destination
#
# Exits 0 if fasttext is already available (no-op). Compiles from source
# otherwise; requires git, make, and g++.

set -euo pipefail

DEST="${1:-$HOME/.local/bin/fasttext}"

# Already installed?
if command -v fasttext >/dev/null 2>&1; then
    echo "fasttext already in PATH: $(command -v fasttext)"
    exit 0
fi
if [ -x "$DEST" ]; then
    echo "fasttext already at $DEST"
    exit 0
fi

# Toolchain check
missing=()
for tool in git make; do
    command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
# macOS ships with clang aliased as g++; either is fine
if ! command -v g++ >/dev/null 2>&1 && ! command -v clang++ >/dev/null 2>&1; then
    missing+=("g++ or clang++")
fi
if [ "${#missing[@]}" -gt 0 ]; then
    echo "ERROR: missing build tools: ${missing[*]}" >&2
    echo "Install with: apt-get install build-essential git   (Linux)" >&2
    echo "           or: xcode-select --install               (macOS)" >&2
    exit 1
fi

BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

echo "Cloning fastText..."
git clone --depth 1 --quiet \
    https://github.com/facebookresearch/fastText.git "$BUILD_DIR"

echo "Compiling (this takes ~15 seconds)..."
CORES="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)"
( cd "$BUILD_DIR" && make -j"$CORES" >/dev/null 2>&1 )

mkdir -p "$(dirname "$DEST")"
cp "$BUILD_DIR/fasttext" "$DEST"
chmod +x "$DEST"

echo "Installed fasttext to $DEST"
case ":$PATH:" in
    *":$(dirname "$DEST"):"*) ;;
    *)
        echo ""
        echo "⚠️  $(dirname "$DEST") is NOT on your PATH."
        echo "   Add this to your shell profile:"
        echo "     export PATH=\"$(dirname "$DEST"):\$PATH\""
        ;;
esac
