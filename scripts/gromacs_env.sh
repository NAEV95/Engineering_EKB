#!/usr/bin/env bash

default_gromacs_prefix() {
  printf '%s\n' "${GROMACS_INSTALL_PREFIX:-$HOME/raid/tools/gromacs-2026.2}"
}

resolve_gromacs_bin() {
  local prefix
  prefix="$(default_gromacs_prefix)"

  if [ -n "${GMX_BIN:-}" ] && [ -x "${GMX_BIN:-}" ]; then
    printf '%s\n' "$GMX_BIN"
    return 0
  fi

  if [ -x "$prefix/bin/gmx" ]; then
    printf '%s\n' "$prefix/bin/gmx"
    return 0
  fi

  if command -v gmx >/dev/null 2>&1; then
    command -v gmx
    return 0
  fi

  if command -v gmx_mpi >/dev/null 2>&1; then
    command -v gmx_mpi
    return 0
  fi

  cat >&2 <<'EOF'
GROMACS was not found.

Install native GROMACS with:
  scripts/install_gromacs_2026_2.sh

Or set:
  GMX_BIN=/path/to/gmx
EOF
  return 2
}

check_gromacs_version() {
  local gmx_bin="$1"
  "$gmx_bin" --version | sed -n '1,20p'
}

check_gpu_runtime() {
  local mode="${1:-gpu}"
  if [ "$mode" != "gpu" ]; then
    return 0
  fi

  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "GPU mode requested, but nvidia-smi is not on PATH." >&2
    return 2
  fi

  if ! nvidia-smi >/dev/null 2>&1; then
    echo "GPU mode requested, but nvidia-smi cannot communicate with the NVIDIA driver." >&2
    return 2
  fi
}
