#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_ROOT="${PROMUT_E2E_ROOT:-$HOME/raid/promut-md-e2e}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

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
promut-md build-mutants \
  --wild-type-pdb "$GB1_DIR/1PGA.pdb" \
  --mutations "$GB1_DIR/gb1_mutations.csv" \
  --output-dir "$GB1_DIR/mutants"

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
