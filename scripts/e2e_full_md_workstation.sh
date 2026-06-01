#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_ROOT="${PROMUT_FULL_MD_ROOT:-$HOME/raid/promut-md-full-md-e2e}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
GMX_BIN="${GMX_BIN:-}"
GROMACS_CONTAINER="${GROMACS_CONTAINER:-nvcr.io/hpc/gromacs:2023.2}"
GROMACS_CONTAINER_FALLBACKS="${GROMACS_CONTAINER_FALLBACKS:-nvcr.io/hpc/gromacs:2023.2 nvcr.io/hpc/gromacs:2022.5}"
PROMUT_USE_GROMACS_CONTAINER="${PROMUT_USE_GROMACS_CONTAINER:-auto}"
MD_STEPS="${PROMUT_FULL_MD_STEPS:-500}"
EQUIL_STEPS="${PROMUT_FULL_MD_EQUIL_STEPS:-100}"
MAX_MUTANTS="${PROMUT_FULL_MD_MAX_MUTANTS:-5}"
MDRUN_MODE="${PROMUT_FULL_MD_MDRUN_MODE:-cpu}"

mkdir -p "$WORK_ROOT"
cd "$ROOT_DIR"

echo "== Environment =="
hostname
pwd
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
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
python -m pip install openmm pdbfixer

echo "== Test suite =="
python -m pytest -q

echo "== GROMACS check =="
GMX_MODE="native"
if [ -z "$GMX_BIN" ]; then
  GMX_BIN="$(command -v gmx || command -v gmx_mpi || true)"
fi
if [ -z "$GMX_BIN" ]; then
  if [ "$PROMUT_USE_GROMACS_CONTAINER" = "0" ]; then
    cat >&2 <<'EOF'
GROMACS was not found and container fallback is disabled.

Install GROMACS, set GMX_BIN=/path/to/gmx, or rerun with container fallback enabled.
EOF
    exit 2
  fi
  if ! command -v docker >/dev/null 2>&1; then
    cat >&2 <<'EOF'
GROMACS was not found, and Docker is not installed or not on PATH.

Install GROMACS directly, or install Docker plus NVIDIA Container Toolkit.
You can also set GMX_BIN=/path/to/gmx.
EOF
    exit 2
  fi
  GMX_MODE="container"
  echo "Native GROMACS was not found; using NGC container: $GROMACS_CONTAINER"
  if ! docker pull "$GROMACS_CONTAINER"; then
    pulled_container=""
    for candidate in $GROMACS_CONTAINER_FALLBACKS; do
      if [ "$candidate" = "$GROMACS_CONTAINER" ]; then
        continue
      fi
      echo "Failed to pull $GROMACS_CONTAINER; trying fallback: $candidate"
      if docker pull "$candidate"; then
        pulled_container="$candidate"
        break
      fi
    done
    if [ -z "$pulled_container" ]; then
      echo "Could not pull any configured GROMACS container image." >&2
      echo "Set GROMACS_CONTAINER to a valid NGC GROMACS tag and rerun." >&2
      exit 2
    fi
    GROMACS_CONTAINER="$pulled_container"
  fi
fi

run_gmx() {
  if [ "$GMX_MODE" = "native" ]; then
    "$GMX_BIN" "$@"
  else
    docker run --rm --interactive --gpus all \
      --user "$(id -u):$(id -g)" \
      --volume "$ROOT_DIR:$ROOT_DIR" \
      --volume "$WORK_ROOT:$WORK_ROOT" \
      --workdir "$PWD" \
      "$GROMACS_CONTAINER" \
      /usr/bin/nventry -build_base_dir=/usr/local/gromacs -build_default=avx2_256 gmx "$@"
  fi
}

run_gmx --version | head -20
echo "GROMACS mdrun mode: $MDRUN_MODE"

GB1_DIR="$WORK_ROOT/gb1"
FULL_MD_DIR="$WORK_ROOT/full_md"
FEATURES_FILE="$WORK_ROOT/features/full_md_features.csv"
TARGET_FILE="$WORK_ROOT/features/full_md_targets.csv"
CONFIG_FILE="$WORK_ROOT/full_md_config.yml"
MODEL_DIR="$WORK_ROOT/models"
RESULTS_DIR="$WORK_ROOT/results"
FIGURES_DIR="$WORK_ROOT/figures"

rm -rf "$GB1_DIR" "$FULL_MD_DIR" "$WORK_ROOT/features" "$MODEL_DIR" "$RESULTS_DIR" "$FIGURES_DIR"
mkdir -p "$GB1_DIR" "$FULL_MD_DIR" "$WORK_ROOT/features" "$MODEL_DIR" "$RESULTS_DIR" "$FIGURES_DIR"

echo "== GB1 test inputs =="
curl -L https://files.rcsb.org/download/1PGA.pdb -o "$GB1_DIR/1PGA.pdb"
cat > "$GB1_DIR/gb1_mutations_all.csv" <<'CSV'
mutation_id,chain,wild_type,position,mutant,DELTA30
M1A,A,M,1,A,-0.20
T2A,A,T,2,A,-0.08
Y3F,A,Y,3,F,0.12
K4A,A,K,4,A,-0.15
L5A,A,L,5,A,0.05
CSV
head -n "$((MAX_MUTANTS + 1))" "$GB1_DIR/gb1_mutations_all.csv" > "$GB1_DIR/gb1_mutations.csv"

echo "== Build PDBFixer mutant structures =="
promut-md build-mutants \
  --wild-type-pdb "$GB1_DIR/1PGA.pdb" \
  --mutations "$GB1_DIR/gb1_mutations.csv" \
  --output-dir "$GB1_DIR/mutants"

python - <<'PY' "$GB1_DIR/gb1_mutations.csv" "$TARGET_FILE"
import pandas as pd
import sys

mutations = pd.read_csv(sys.argv[1])
targets = mutations[["mutation_id", "DELTA30"]].set_index("mutation_id")
targets.to_csv(sys.argv[2])
PY

write_mdp_files() {
  local dir="$1"
  cat > "$dir/ions.mdp" <<'EOF'
integrator = steep
emtol = 1000.0
emstep = 0.01
nsteps = 200
cutoff-scheme = Verlet
coulombtype = PME
rcoulomb = 1.0
rvdw = 1.0
pbc = xyz
EOF

  cat > "$dir/minim.mdp" <<'EOF'
integrator = steep
emtol = 1000.0
emstep = 0.01
nsteps = 500
cutoff-scheme = Verlet
coulombtype = PME
rcoulomb = 1.0
rvdw = 1.0
pbc = xyz
EOF

  cat > "$dir/nvt.mdp" <<EOF
integrator = md
nsteps = $EQUIL_STEPS
dt = 0.002
cutoff-scheme = Verlet
coulombtype = PME
rcoulomb = 1.0
rvdw = 1.0
pbc = xyz
constraints = h-bonds
constraint-algorithm = lincs
tcoupl = V-rescale
tc-grps = System
tau_t = 0.1
ref_t = 300
pcoupl = no
gen_vel = yes
gen_temp = 300
gen_seed = 42
nstxout-compressed = 50
nstenergy = 50
EOF

  cat > "$dir/md.mdp" <<EOF
integrator = md
nsteps = $MD_STEPS
dt = 0.002
cutoff-scheme = Verlet
coulombtype = PME
rcoulomb = 1.0
rvdw = 1.0
pbc = xyz
constraints = h-bonds
constraint-algorithm = lincs
tcoupl = V-rescale
tc-grps = System
tau_t = 0.1
ref_t = 300
pcoupl = no
gen_vel = no
nstxout-compressed = 50
nstenergy = 50
EOF
}

strip_xvg() {
  grep -v '^[#@]' "$1" > "$2"
}

run_mdrun() {
  if [ "$MDRUN_MODE" = "gpu" ]; then
    run_gmx mdrun "$@"
  else
    run_gmx mdrun "$@" -nb cpu -pme cpu -bonded cpu -update cpu -ntmpi 1
  fi
}

run_one_md() {
  local pdb="$1"
  local name
  name="$(basename "$pdb" .pdb)"
  local sim_dir="$FULL_MD_DIR/$name"
  mkdir -p "$sim_dir"
  cp "$pdb" "$sim_dir/input.pdb"
  write_mdp_files "$sim_dir"

  (
    cd "$sim_dir"
    run_gmx pdb2gmx -f input.pdb -o processed.gro -p topol.top -ff amber99sb-ildn -water tip3p -ignh
    run_gmx editconf -f processed.gro -o boxed.gro -c -d 1.0 -bt cubic
    run_gmx solvate -cp boxed.gro -cs spc216.gro -o solv.gro -p topol.top
    run_gmx grompp -f ions.mdp -c solv.gro -p topol.top -o ions.tpr -maxwarn 2
    if ! printf '13\n' | run_gmx genion -s ions.tpr -o solv_ions.gro -p topol.top -pname NA -nname CL -neutral -conc 0.15; then
      printf 'SOL\n' | run_gmx genion -s ions.tpr -o solv_ions.gro -p topol.top -pname NA -nname CL -neutral -conc 0.15
    fi
    run_gmx grompp -f minim.mdp -c solv_ions.gro -p topol.top -o em.tpr -maxwarn 2
    run_mdrun -deffnm em
    run_gmx grompp -f nvt.mdp -c em.gro -r em.gro -p topol.top -o nvt.tpr -maxwarn 2
    run_mdrun -deffnm nvt
    run_gmx grompp -f md.mdp -c nvt.gro -t nvt.cpt -p topol.top -o md.tpr -maxwarn 2
    run_mdrun -deffnm md

    printf '0\n' | run_gmx trjconv -s md.tpr -f md.xtc -o md_noPBC.xtc -pbc mol -ur compact
    printf '4\n4\n' | run_gmx rms -s md.tpr -f md_noPBC.xtc -o rmsd_backbone_raw.xvg -tu ps
    printf '1\n' | run_gmx gyrate -s md.tpr -f md_noPBC.xtc -o gyrate_raw.xvg
    printf '1\n' | run_gmx rmsf -s md.tpr -f md_noPBC.xtc -o rmsf_10ns_raw.xvg -res
    printf 'Potential\n0\n' | run_gmx energy -f md.edr -o energy_raw.xvg

    strip_xvg rmsd_backbone_raw.xvg rmsd_backbone.dat
    strip_xvg gyrate_raw.xvg gyrate.xvg
    strip_xvg rmsf_10ns_raw.xvg rmsf_10ns.xvg
    strip_xvg energy_raw.xvg energy.xvg
  )
}

echo "== Run short real GROMACS MD =="
for pdb in "$GB1_DIR"/mutants/*.pdb; do
  run_one_md "$pdb"
done

cat > "$CONFIG_FILE" <<EOF
paths:
  data:
    raw: $GB1_DIR/mutants
    processed: $WORK_ROOT/features
    results: $RESULTS_DIR
  figures: $FIGURES_DIR
  models: $MODEL_DIR
feature_extraction:
  pocket_analysis:
    enabled: false
  sequence_features:
    enabled: false
  secondary_structure:
    enabled: false
  dynamic_features:
    enabled: true
    md_files:
      rmsf: rmsf_*.xvg
      rmsd: rmsd_*.dat
      rg: gyrate.xvg
      energy: energy.xvg
  target_file: $TARGET_FILE
model:
  type: random_forest
  target_column: DELTA30
  train_test_split: 0.6
  random_seed: 42
  cross_validation: 0
  lightgbm:
    n_estimators: 50
    max_depth: 3
visualization:
  target_column: DELTA30
  figures:
    format: png
    dpi: 150
  interactive:
    enabled: false
  top_n_features: 20
  top_n_features_to_plot: 5
EOF

echo "== Extract MD features =="
python scripts/feature_extraction/extract_features.py \
  --md-dir "$FULL_MD_DIR" \
  --output "$FEATURES_FILE" \
  --config "$CONFIG_FILE"

echo "== Train, evaluate, and visualize =="
python - <<'PY' "$FEATURES_FILE" "$MODEL_DIR" "$RESULTS_DIR" "$FIGURES_DIR" "$CONFIG_FILE"
import sys
import yaml
from src.models.train_model import train_model
from src.models.evaluate_model import evaluate_model
from src.visualization.visualize import generate_visualizations

features_file, model_dir, results_dir, figures_dir, config_file = sys.argv[1:]
with open(config_file, "r", encoding="utf-8") as handle:
    config = yaml.safe_load(handle)

model_file = train_model(features_file, model_dir, config["model"])
results_file = evaluate_model(model_file, features_file, results_dir, config["model"])
generate_visualizations(features_file, model_file, results_file, figures_dir, config["visualization"])
print(f"MODEL_FILE={model_file}")
print(f"RESULTS_FILE={results_file}")
PY

echo "== Full MD E2E output summary =="
find "$FULL_MD_DIR" -maxdepth 2 -type f \( -name '*.gro' -o -name '*.xtc' -o -name '*.edr' -o -name '*.dat' -o -name '*.xvg' \) | sort | head -200 || true
find "$WORK_ROOT" -maxdepth 3 -type f | wc -l
echo "Full MD E2E completed. Outputs are under $WORK_ROOT"
