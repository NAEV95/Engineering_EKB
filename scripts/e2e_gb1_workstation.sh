#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_ROOT="${PROMUT_E2E_ROOT:-$HOME/raid/promut-md-e2e}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
FOLDX_INSTALL_DIR="${FOLDX_INSTALL_DIR:-$HOME/raid/tools/foldx}"
FOLDX_BIN="${FOLDX_BIN:-$FOLDX_INSTALL_DIR/foldx}"
PROMUT_ALLOW_PDBFIXER_INSTALL="${PROMUT_ALLOW_PDBFIXER_INSTALL:-1}"

mkdir -p "$WORK_ROOT"
cd "$ROOT_DIR"

echo "== Environment =="
hostname
pwd
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
else
  echo "nvidia-smi not found"
fi

echo "== Python environment =="
if [ ! -d "$WORK_ROOT/.venv" ]; then
  "$PYTHON_BIN" -m venv "$WORK_ROOT/.venv"
fi
# shellcheck disable=SC1091
source "$WORK_ROOT/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .

echo "== Test suite =="
python -m pytest -q

echo "== GB1 test inputs =="
GB1_DIR="$WORK_ROOT/gb1"
mkdir -p "$GB1_DIR"
curl -L https://files.rcsb.org/download/1PGA.pdb -o "$GB1_DIR/1PGA.pdb"
cat > "$GB1_DIR/gb1_mutations.csv" <<'CSV'
mutation_id,chain,wild_type,position,mutant,fitness_note
M1A,A,M,1,A,GB1 public DMS plumbing test mutation
T2A,A,T,2,A,GB1 public DMS plumbing test mutation
Y3F,A,Y,3,F,GB1 public DMS plumbing test mutation
K4A,A,K,4,A,GB1 public DMS plumbing test mutation
L5A,A,L,5,A,GB1 public DMS plumbing test mutation
CSV

echo "== Build mutant structures =="
STRUCTURE_BACKEND="${PROMUT_STRUCTURE_BACKEND:-}"
FOLDX_ARG=()
ensure_pdbfixer_backend() {
  if python -c 'import pdbfixer, openmm' >/dev/null 2>&1; then
    return 0
  fi
  if [ "$PROMUT_ALLOW_PDBFIXER_INSTALL" != "1" ]; then
    return 1
  fi
  echo "PDBFixer/OpenMM not found; installing open-source interim structure backend"
  python -m pip install openmm pdbfixer
  python -c 'import pdbfixer, openmm'
}

if [ -z "$STRUCTURE_BACKEND" ]; then
  if command -v foldx >/dev/null 2>&1; then
    STRUCTURE_BACKEND="foldx"
  elif [ -x "$FOLDX_BIN" ]; then
    STRUCTURE_BACKEND="foldx"
    FOLDX_ARG=(--foldx-bin "$FOLDX_BIN")
  else
    LOCAL_FOLDX_ARCHIVE="$(find "$FOLDX_INSTALL_DIR" -maxdepth 1 -type f \
      \( -iname 'foldx*.zip' -o -iname 'foldx*.tar.gz' -o -iname 'foldx*.tgz' -o -iname 'foldx*.tar.bz2' -o -iname 'foldx*.tbz2' \) \
      2>/dev/null | head -n 1 || true)"
    if [ -n "${FOLDX_DOWNLOAD_URL:-}" ] || [ -n "${FOLDX_ARCHIVE:-}" ] || [ -n "$LOCAL_FOLDX_ARCHIVE" ]; then
      echo "FoldX was not found; attempting install via scripts/install_foldx.sh"
      bash scripts/install_foldx.sh || true
    fi
  fi

  if [ -z "$STRUCTURE_BACKEND" ]; then
    if command -v foldx >/dev/null 2>&1; then
      STRUCTURE_BACKEND="foldx"
    elif [ -x "$FOLDX_BIN" ]; then
      STRUCTURE_BACKEND="foldx"
      FOLDX_ARG=(--foldx-bin "$FOLDX_BIN")
    elif ensure_pdbfixer_backend; then
      STRUCTURE_BACKEND="pdbfixer"
    else
      STRUCTURE_BACKEND="simple"
      echo "WARNING: FoldX and PDBFixer/OpenMM were not found; using simple residue-name substitution backend for smoke testing only."
      echo "Run scripts/install_foldx.sh, set FOLDX_BIN, or enable PDBFixer/OpenMM for better interim mutant models."
    fi
  fi
elif [ "$STRUCTURE_BACKEND" = "foldx" ]; then
  if [ -x "$FOLDX_BIN" ]; then
    FOLDX_ARG=(--foldx-bin "$FOLDX_BIN")
  elif ! command -v foldx >/dev/null 2>&1; then
    echo "FoldX backend requested; attempting install via scripts/install_foldx.sh"
    bash scripts/install_foldx.sh
    if [ -x "$FOLDX_BIN" ]; then
      FOLDX_ARG=(--foldx-bin "$FOLDX_BIN")
    fi
  fi
elif [ "$STRUCTURE_BACKEND" = "pdbfixer" ]; then
  ensure_pdbfixer_backend
fi
promut-md build-mutants \
  --wild-type-pdb "$GB1_DIR/1PGA.pdb" \
  --mutations "$GB1_DIR/gb1_mutations.csv" \
  --output-dir "$GB1_DIR/mutants" \
  --backend "$STRUCTURE_BACKEND" \
  "${FOLDX_ARG[@]}"

echo "== Stage MD inputs =="
python scripts/md_simulations/run_md.py \
  --input-dir "$GB1_DIR/mutants" \
  --output-dir "$GB1_DIR/md_staged"

echo "== No-MDS bundled-data smoke =="
python run_pipeline_no_mds.py \
  --data-dir data \
  --output-dir "$WORK_ROOT/no_mds_output" \
  --skip-optuna \
  --skip-bootstrap

echo "== Output summary =="
find "$GB1_DIR" -maxdepth 3 -type f | sort
find "$WORK_ROOT/no_mds_output" -maxdepth 3 -type f | wc -l
echo "E2E workflow completed. Outputs are under $WORK_ROOT"
