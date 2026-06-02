#!/usr/bin/env bash
set -euo pipefail

VERSION="${GROMACS_VERSION:-2026.2}"
PREFIX="${GROMACS_INSTALL_PREFIX:-$HOME/raid/tools/gromacs-$VERSION}"
BUILD_ROOT="${GROMACS_BUILD_ROOT:-$HOME/raid/tools/src/gromacs-$VERSION-build}"
CUDA_ROOT="${CUDA_HOME:-/usr/local/cuda}"
JOBS="${GROMACS_BUILD_JOBS:-$(nproc)}"
DRY_RUN=0

usage() {
  cat <<EOF
Install native CUDA-enabled GROMACS $VERSION.

Environment:
  GROMACS_INSTALL_PREFIX  Install prefix, default: $HOME/raid/tools/gromacs-$VERSION
  GROMACS_BUILD_ROOT      Build/source root, default: $HOME/raid/tools/src/gromacs-$VERSION-build
  CUDA_HOME               CUDA toolkit root, default: /usr/local/cuda
  GROMACS_BUILD_JOBS      Parallel build jobs, default: nproc

Options:
  --dry-run               Print commands without running them
  --help                  Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

SOURCE_URL="https://ftp.gromacs.org/gromacs/gromacs-$VERSION.tar.gz"
ARCHIVE="$BUILD_ROOT/gromacs-$VERSION.tar.gz"
SOURCE_DIR="$BUILD_ROOT/gromacs-$VERSION"
BUILD_DIR="$BUILD_ROOT/build"

run() {
  printf '+'
  for arg in "$@"; do
    printf ' %q' "$arg"
  done
  printf '\n'
  if [ "$DRY_RUN" = "0" ]; then
    "$@"
  fi
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 2
  fi
}

require_command cmake
require_command make
require_command tar
require_command curl

if [ ! -x "$CUDA_ROOT/bin/nvcc" ]; then
  echo "CUDA nvcc not found at $CUDA_ROOT/bin/nvcc." >&2
  echo "Set CUDA_HOME to the CUDA toolkit root." >&2
  exit 2
fi

run mkdir -p "$BUILD_ROOT"

if [ ! -f "$ARCHIVE" ]; then
  run curl -L "$SOURCE_URL" -o "$ARCHIVE"
fi

if [ ! -d "$SOURCE_DIR" ]; then
  run tar -xzf "$ARCHIVE" -C "$BUILD_ROOT"
fi

run mkdir -p "$BUILD_DIR"
run cmake -S "$SOURCE_DIR" -B "$BUILD_DIR" \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DGMX_GPU=CUDA \
  -DCUDAToolkit_ROOT="$CUDA_ROOT" \
  -DGMX_BUILD_OWN_FFTW=ON \
  -DREGRESSIONTEST_DOWNLOAD=ON
run cmake --build "$BUILD_DIR" --parallel "$JOBS"
run cmake --install "$BUILD_DIR"

cat <<EOF

GROMACS $VERSION install complete.

Activate it with:
  source "$PREFIX/bin/GMXRC"

Verify with:
  "$PREFIX/bin/gmx" --version
EOF
