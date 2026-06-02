# Native GROMACS Full MD E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install native CUDA-enabled GROMACS 2026.2 and make the workstation full-MD E2E use it for simulation, extraction, model building, analysis, and plotting.

**Architecture:** Add a native installer, small GROMACS shell helper functions, and update the existing full-MD workstation script to prefer the native install and GPU mode. Keep the existing scientific flow intact and test repository logic without trying to compile GROMACS inside pytest.

**Tech Stack:** Bash, GROMACS 2026.2, CMake, CUDA Toolkit, pytest, Python pipeline modules already in the repo.

---

## File Structure

- Create `scripts/install_gromacs_2026_2.sh`: downloads, configures, builds, and installs native GROMACS 2026.2.
- Create `scripts/gromacs_env.sh`: resolves `gmx`, checks version, and checks GPU runtime when requested.
- Modify `scripts/e2e_full_md_workstation.sh`: use native GROMACS discovery, default GPU mode, remove automatic NGC fallback from the default path.
- Create `tests/test_gromacs_env.py`: tests shell helper behavior with temporary fake binaries.
- Optionally modify `ReadMe.md` or `USAGE.md`: document native install and E2E command if implementation changes user-facing commands.

---

### Task 1: Add GROMACS Shell Helper

**Files:**
- Create: `scripts/gromacs_env.sh`
- Test: `tests/test_gromacs_env.py`

- [ ] **Step 1: Write failing tests for GROMACS discovery**

Create `tests/test_gromacs_env.py` with:

```python
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "gromacs_env.sh"


def run_bash(script, env=None):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["bash", "-lc", script],
        text=True,
        capture_output=True,
        cwd=ROOT,
        env=merged_env,
        check=False,
    )


def test_resolve_gromacs_bin_prefers_explicit_gmx_bin(tmp_path):
    fake = tmp_path / "explicit-gmx"
    fake.write_text("#!/usr/bin/env bash\necho fake gmx\n", encoding="utf-8")
    fake.chmod(0o755)

    result = run_bash(
        f"source {HELPER}; resolve_gromacs_bin",
        env={
            "GMX_BIN": str(fake),
            "GROMACS_INSTALL_PREFIX": str(tmp_path / "missing-prefix"),
            "PATH": "/usr/bin:/bin",
        },
    )

    assert result.returncode == 0
    assert result.stdout.strip() == str(fake)


def test_resolve_gromacs_bin_prefers_install_prefix_before_path(tmp_path):
    prefix_gmx = tmp_path / "prefix" / "bin" / "gmx"
    path_gmx_dir = tmp_path / "path-bin"
    path_gmx = path_gmx_dir / "gmx"
    prefix_gmx.parent.mkdir(parents=True)
    path_gmx_dir.mkdir()
    prefix_gmx.write_text("#!/usr/bin/env bash\necho prefix\n", encoding="utf-8")
    path_gmx.write_text("#!/usr/bin/env bash\necho path\n", encoding="utf-8")
    prefix_gmx.chmod(0o755)
    path_gmx.chmod(0o755)

    result = run_bash(
        f"source {HELPER}; resolve_gromacs_bin",
        env={
            "GMX_BIN": "",
            "GROMACS_INSTALL_PREFIX": str(tmp_path / "prefix"),
            "PATH": f"{path_gmx_dir}:/usr/bin:/bin",
        },
    )

    assert result.returncode == 0
    assert result.stdout.strip() == str(prefix_gmx)


def test_check_gpu_runtime_allows_cpu_mode_without_nvidia_smi(tmp_path):
    result = run_bash(
        f"source {HELPER}; check_gpu_runtime cpu",
        env={"PATH": "/usr/bin:/bin"},
    )

    assert result.returncode == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_gromacs_env.py -q
```

Expected: FAIL because `scripts/gromacs_env.sh` does not exist.

- [ ] **Step 3: Implement `scripts/gromacs_env.sh`**

Create `scripts/gromacs_env.sh`:

```bash
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

  cat >&2 <<EOF
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
```

- [ ] **Step 4: Run helper tests**

Run:

```bash
python -m pytest tests/test_gromacs_env.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit helper**

Run:

```bash
git add scripts/gromacs_env.sh tests/test_gromacs_env.py
git commit -m "Add native GROMACS environment helper"
```

---

### Task 2: Add Native GROMACS 2026.2 Installer

**Files:**
- Create: `scripts/install_gromacs_2026_2.sh`
- Test: `tests/test_gromacs_installer.py`

- [ ] **Step 1: Write failing installer tests**

Create `tests/test_gromacs_installer.py`:

```python
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_gromacs_2026_2.sh"


def test_installer_help_mentions_prefix_and_version():
    result = subprocess.run(
        ["bash", str(INSTALLER), "--help"],
        text=True,
        capture_output=True,
        cwd=ROOT,
        check=False,
    )

    assert result.returncode == 0
    assert "GROMACS 2026.2" in result.stdout
    assert "GROMACS_INSTALL_PREFIX" in result.stdout


def test_installer_dry_run_prints_cmake_cuda_flags(tmp_path):
    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--dry-run",
        ],
        text=True,
        capture_output=True,
        cwd=ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
            "CUDA_HOME": "/usr/local/cuda",
            "GROMACS_INSTALL_PREFIX": str(tmp_path / "tools" / "gromacs-2026.2"),
            "GROMACS_BUILD_ROOT": str(tmp_path / "tools" / "src" / "gromacs-build"),
        },
        check=False,
    )

    assert result.returncode == 0
    assert "-DGMX_GPU=CUDA" in result.stdout
    assert "-DGMX_BUILD_OWN_FFTW=ON" in result.stdout
    assert "-DREGRESSIONTEST_DOWNLOAD=ON" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_gromacs_installer.py -q
```

Expected: FAIL because the installer does not exist.

- [ ] **Step 3: Implement installer**

Create `scripts/install_gromacs_2026_2.sh`:

```bash
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
    --dry-run) DRY_RUN=1 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

SOURCE_URL="https://ftp.gromacs.org/gromacs/gromacs-$VERSION.tar.gz"
ARCHIVE="$BUILD_ROOT/gromacs-$VERSION.tar.gz"
SOURCE_DIR="$BUILD_ROOT/gromacs-$VERSION"
BUILD_DIR="$BUILD_ROOT/build"

run() {
  printf '+ %q' "$1"
  shift
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
```

- [ ] **Step 4: Make installer executable**

Run:

```bash
chmod +x scripts/install_gromacs_2026_2.sh
```

- [ ] **Step 5: Run installer tests**

Run:

```bash
python -m pytest tests/test_gromacs_installer.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit installer**

Run:

```bash
git add scripts/install_gromacs_2026_2.sh tests/test_gromacs_installer.py
git commit -m "Add native GROMACS 2026.2 installer"
```

---

### Task 3: Update Full MD E2E To Use Native GROMACS

**Files:**
- Modify: `scripts/e2e_full_md_workstation.sh`
- Test: `tests/test_full_md_workstation_script.py`

- [ ] **Step 1: Write failing script tests**

Create `tests/test_full_md_workstation_script.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "e2e_full_md_workstation.sh"


def test_full_md_script_sources_gromacs_helper():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "source \"$ROOT_DIR/scripts/gromacs_env.sh\"" in text


def test_full_md_script_defaults_to_gpu_mode():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'MDRUN_MODE="${PROMUT_FULL_MD_MDRUN_MODE:-gpu}"' in text


def test_full_md_script_uses_resolve_gromacs_bin():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "GMX_BIN=\"$(resolve_gromacs_bin)\"" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_full_md_workstation_script.py -q
```

Expected: FAIL because the current script does not source the helper and defaults to CPU mode.

- [ ] **Step 3: Modify the script header and GROMACS check**

In `scripts/e2e_full_md_workstation.sh`, change the top variable block so it includes:

```bash
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/gromacs_env.sh"

WORK_ROOT="${PROMUT_FULL_MD_ROOT:-$HOME/raid/promut-md-full-md-e2e}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
GMX_BIN="${GMX_BIN:-}"
GROMACS_CONTAINER="${GROMACS_CONTAINER:-}"
PROMUT_USE_GROMACS_CONTAINER="${PROMUT_USE_GROMACS_CONTAINER:-0}"
MD_STEPS="${PROMUT_FULL_MD_STEPS:-500}"
EQUIL_STEPS="${PROMUT_FULL_MD_EQUIL_STEPS:-100}"
MAX_MUTANTS="${PROMUT_FULL_MD_MAX_MUTANTS:-5}"
MDRUN_MODE="${PROMUT_FULL_MD_MDRUN_MODE:-gpu}"
```

Replace the existing `== GROMACS check ==` block with:

```bash
echo "== GROMACS check =="
GMX_MODE="native"
if [ "$PROMUT_USE_GROMACS_CONTAINER" = "1" ]; then
  if [ -z "$GROMACS_CONTAINER" ]; then
    echo "PROMUT_USE_GROMACS_CONTAINER=1 requires GROMACS_CONTAINER to be set." >&2
    exit 2
  fi
  if ! command -v docker >/dev/null 2>&1; then
    echo "Container mode requested, but Docker is not installed or not on PATH." >&2
    exit 2
  fi
  GMX_MODE="container"
  docker pull "$GROMACS_CONTAINER"
else
  GMX_BIN="$(resolve_gromacs_bin)"
fi

check_gpu_runtime "$MDRUN_MODE"
```

Keep the existing `run_gmx` function shape, but make the container branch use
the user-provided image and leave the native branch as:

```bash
if [ "$GMX_MODE" = "native" ]; then
  "$GMX_BIN" "$@"
else
  docker run --rm --interactive --gpus all \
    --user "$(id -u):$(id -g)" \
    --volume "$ROOT_DIR:$ROOT_DIR" \
    --volume "$WORK_ROOT:$WORK_ROOT" \
    --workdir "$PWD" \
    "$GROMACS_CONTAINER" \
    gmx "$@"
fi
```

- [ ] **Step 4: Run script tests**

Run:

```bash
python -m pytest tests/test_full_md_workstation_script.py -q
```

Expected: PASS.

- [ ] **Step 5: Run existing MD CLI tests**

Run:

```bash
python -m pytest tests/test_md_simulation_cli.py tests/test_entrypoints.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit E2E update**

Run:

```bash
git add scripts/e2e_full_md_workstation.sh tests/test_full_md_workstation_script.py
git commit -m "Use native GROMACS in full MD E2E"
```

---

### Task 4: Install Native GROMACS

**Files:**
- No repository file changes expected.

- [ ] **Step 1: Run installer**

Run:

```bash
CUDA_HOME=/usr/local/cuda-13.2 \
GROMACS_INSTALL_PREFIX="$HOME/raid/tools/gromacs-2026.2" \
scripts/install_gromacs_2026_2.sh
```

Expected: command completes and prints activation instructions.

- [ ] **Step 2: Verify native GROMACS**

Run:

```bash
source "$HOME/raid/tools/gromacs-2026.2/bin/GMXRC"
gmx --version | sed -n '1,30p'
```

Expected: output contains `GROMACS version: 2026.2` and CUDA/GPU support details.

- [ ] **Step 3: Verify GPU visibility from the invoking shell**

Run:

```bash
nvidia-smi --query-gpu=name,driver_version,cuda_version,memory.total --format=csv,noheader
```

Expected: two RTX PRO 6000 Blackwell GPUs are listed.

---

### Task 5: Run Full MD E2E Smoke

**Files:**
- No repository file changes expected unless runtime bugs are discovered.

- [ ] **Step 1: Run short full-MD E2E**

Run:

```bash
PROMUT_FULL_MD_MAX_MUTANTS=2 \
PROMUT_FULL_MD_STEPS=100 \
PROMUT_FULL_MD_EQUIL_STEPS=50 \
PROMUT_FULL_MD_MDRUN_MODE=gpu \
GMX_BIN="$HOME/raid/tools/gromacs-2026.2/bin/gmx" \
scripts/e2e_full_md_workstation.sh
```

Expected: pipeline completes and prints `Full MD E2E completed`.

- [ ] **Step 2: Inspect generated outputs**

Run:

```bash
find "$HOME/raid/promut-md-full-md-e2e" -maxdepth 3 -type f | sort | sed -n '1,120p'
```

Expected: output includes MD files, feature CSV, model pickle, evaluation JSON, and figure PNGs.

- [ ] **Step 3: Run final test suite**

Run:

```bash
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 4: Commit any bug fixes from the E2E run**

If runtime fixes were needed, run:

```bash
git status --short
git add <changed-files>
git commit -m "Fix full MD E2E runtime issues"
```

If no fixes were needed, leave the repository clean.

---

## Self-Review

- Spec coverage: installer, native discovery, GPU runtime check, E2E update, tests, and manual full-MD verification are covered.
- Placeholder scan: no placeholder markers or vague implementation steps are present.
- Type/signature consistency: shell function names are `resolve_gromacs_bin`, `check_gromacs_version`, and `check_gpu_runtime` throughout.
