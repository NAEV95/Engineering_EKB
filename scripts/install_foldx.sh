#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${FOLDX_INSTALL_DIR:-$HOME/raid/tools/foldx}"
DOWNLOAD_URL="${FOLDX_DOWNLOAD_URL:-}"
ARCHIVE_PATH="${FOLDX_ARCHIVE:-}"

mkdir -p "$INSTALL_DIR"

find_foldx_binary() {
  if command -v foldx >/dev/null 2>&1; then
    command -v foldx
    return 0
  fi

  if [ -x "$INSTALL_DIR/foldx" ]; then
    printf '%s\n' "$INSTALL_DIR/foldx"
    return 0
  fi

  find "$INSTALL_DIR" -maxdepth 5 -type f \
    \( -iname 'foldx' -o -iname 'foldx_*' -o -iname 'foldx-*' \) \
    -perm -u+x | head -n 1
}

extract_archive() {
  local archive="$1"
  case "$archive" in
    *.tar.gz|*.tgz)
      tar -xzf "$archive" -C "$INSTALL_DIR"
      ;;
    *.tar.bz2|*.tbz2)
      tar -xjf "$archive" -C "$INSTALL_DIR"
      ;;
    *.zip)
      unzip -o "$archive" -d "$INSTALL_DIR"
      ;;
    *)
      echo "Unsupported FoldX archive format: $archive" >&2
      echo "Expected .zip, .tar.gz, .tgz, .tar.bz2, or .tbz2" >&2
      return 1
      ;;
  esac
}

install_from_archive() {
  local archive="$1"
  echo "Extracting FoldX archive: $archive"
  extract_archive "$archive"

  local binary
  binary="$(find "$INSTALL_DIR" -maxdepth 5 -type f \
    \( -iname 'foldx' -o -iname 'foldx_*' -o -iname 'foldx-*' \) | head -n 1)"

  if [ -z "$binary" ]; then
    echo "Could not find a FoldX binary after extracting $archive" >&2
    return 1
  fi

  chmod +x "$binary"
  if [ "$binary" != "$INSTALL_DIR/foldx" ]; then
    ln -sfn "$binary" "$INSTALL_DIR/foldx"
  fi
}

existing_binary="$(find_foldx_binary || true)"
if [ -n "$existing_binary" ]; then
  echo "FoldX already installed: $existing_binary"
  echo "Add this to PATH if needed:"
  echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
  exit 0
fi

if [ -n "$DOWNLOAD_URL" ]; then
  archive_name="${DOWNLOAD_URL##*/}"
  if [ -z "$archive_name" ] || [ "$archive_name" = "$DOWNLOAD_URL" ]; then
    archive_name="foldx-download"
  fi
  archive_path="$INSTALL_DIR/$archive_name"

  echo "Downloading FoldX archive from FOLDX_DOWNLOAD_URL"
  curl -L --fail "$DOWNLOAD_URL" -o "$archive_path"
  install_from_archive "$archive_path"
elif [ -n "$ARCHIVE_PATH" ]; then
  install_from_archive "$ARCHIVE_PATH"
else
  local_archive="$(find "$INSTALL_DIR" -maxdepth 1 -type f \
    \( -iname 'foldx*.zip' -o -iname 'foldx*.tar.gz' -o -iname 'foldx*.tgz' -o -iname 'foldx*.tar.bz2' -o -iname 'foldx*.tbz2' \) \
    | head -n 1)"

  if [ -n "$local_archive" ]; then
    install_from_archive "$local_archive"
  else
    cat >&2 <<EOF
FoldX is not installed and no downloadable archive was provided.

FoldX requires registration/license acceptance, so automatic download only works
when you provide the licensed archive URL or copy the archive into:

  $INSTALL_DIR

Options:
  1. Download FoldX for Linux from https://foldxsuite.crg.eu/
     then copy the .zip/.tar.gz into $INSTALL_DIR and rerun this script.

  2. Provide an explicit archive path:
     FOLDX_ARCHIVE=/path/to/foldx.zip bash scripts/install_foldx.sh

  3. Provide a direct licensed download URL:
     FOLDX_DOWNLOAD_URL='https://...' bash scripts/install_foldx.sh
EOF
    exit 2
  fi
fi

installed_binary="$(find_foldx_binary || true)"
if [ -z "$installed_binary" ]; then
  echo "FoldX install did not produce an executable binary." >&2
  exit 1
fi

if ! find "$INSTALL_DIR" -maxdepth 5 -type f -iname 'rotabase.txt' | grep -q .; then
  echo "WARNING: rotabase.txt was not found under $INSTALL_DIR." >&2
  echo "FoldX normally requires rotabase.txt next to the binary or in the run directory." >&2
fi

echo "FoldX installed: $installed_binary"
echo "To make it available in future shells, run:"
echo "  echo 'export PATH=\"$INSTALL_DIR:\$PATH\"' >> ~/.bashrc"
echo "  source ~/.bashrc"
