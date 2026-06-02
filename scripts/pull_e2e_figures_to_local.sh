#!/usr/bin/env bash
set -euo pipefail

REMOTE="${1:-nvenanzi@2cab62a-lcedt}"
LOCAL_DIR="${2:-$HOME/Downloads/promut-md-full-md-e2e-figures}"
REMOTE_DIR="${PROMUT_REMOTE_FIGURES_DIR:-~/raid/promut-md-full-md-e2e/figures}"

usage() {
  cat <<EOF
Pull ProMut-MD E2E figures from the RTX workstation to this local machine.

Run this script on your local machine, not inside the remote SSH session.

Usage:
  $0 [remote] [local-dir]

Defaults:
  remote:    nvenanzi@2cab62a-lcedt
  local-dir: \$HOME/Downloads/promut-md-full-md-e2e-figures

Environment:
  PROMUT_REMOTE_FIGURES_DIR  Remote figures directory.
                             Default: ~/raid/promut-md-full-md-e2e/figures

Examples:
  $0
  $0 nvenanzi@2cab62a-lcedt ~/Desktop/promut-figures
  PROMUT_REMOTE_FIGURES_DIR=/home/nvenanzi/raid/promut-md-full-md-e2e/figures $0
EOF
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

mkdir -p "$LOCAL_DIR"

echo "Remote: $REMOTE"
echo "Remote figures: $REMOTE_DIR"
echo "Local output: $LOCAL_DIR"

if command -v rsync >/dev/null 2>&1; then
  rsync -av \
    --include='*/' \
    --include='*.png' \
    --exclude='*' \
    "$REMOTE:$REMOTE_DIR/" \
    "$LOCAL_DIR/"
else
  echo "rsync not found; falling back to scp."
  scp -r "$REMOTE:$REMOTE_DIR/." "$LOCAL_DIR/"
fi

echo
echo "Copied figures to: $LOCAL_DIR"
