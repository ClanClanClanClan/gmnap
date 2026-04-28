#!/usr/bin/env bash
# Install GMNAP's git hooks into the local clone.
#
# Run this once after cloning the repo, before making your first
# commit. It copies the tracked hook files from `scripts/git_hooks/`
# into the clone-local `.git/hooks/` directory and marks them
# executable. Idempotent — re-running is safe and overwrites in
# place.
#
# Worktree-aware: respects `git rev-parse --git-common-dir` so
# hooks installed in a primary clone are available to every worktree.
#
# Usage:
#   bash scripts/install_hooks.sh
#
# Skip with:
#   GMNAP_SKIP_HOOK_INSTALL=1 bash scripts/install_hooks.sh
#
# Override the hook directory (test environments / CI):
#   GMNAP_HOOK_DIR=/tmp/foo bash scripts/install_hooks.sh

set -euo pipefail

if [[ "${GMNAP_SKIP_HOOK_INSTALL:-}" == "1" ]]; then
    echo "GMNAP_SKIP_HOOK_INSTALL=1 set; skipping."
    exit 0
fi

# Find the repo root (works inside worktrees too).
REPO_ROOT="$(git rev-parse --show-toplevel)"

# `git rev-parse --git-common-dir` resolves to the *primary* .git
# directory even from a worktree, so hooks installed once cover
# every worktree of this clone.
HOOK_DIR="${GMNAP_HOOK_DIR:-$(git rev-parse --git-common-dir)/hooks}"

SOURCE_DIR="${REPO_ROOT}/scripts/git_hooks"

if [[ ! -d "${SOURCE_DIR}" ]]; then
    echo "ERROR: ${SOURCE_DIR} does not exist; nothing to install." >&2
    exit 1
fi

mkdir -p "${HOOK_DIR}"

count=0
for hook_path in "${SOURCE_DIR}"/*; do
    [[ -f "${hook_path}" ]] || continue
    name="$(basename "${hook_path}")"
    target="${HOOK_DIR}/${name}"
    cp "${hook_path}" "${target}"
    chmod +x "${target}"
    echo "Installed ${name} → ${target}"
    count=$((count + 1))
done

if [[ "${count}" == 0 ]]; then
    echo "WARNING: no hooks found under ${SOURCE_DIR}" >&2
fi

echo "Done. ${count} hook(s) installed."
