# Native GROMACS Full MD E2E Design

## Context

The repository already contains a workstation full-MD E2E script at
`scripts/e2e_full_md_workstation.sh`. It builds GB1 mutant structures, runs
short GROMACS simulations, extracts RMSD/RMSF/radius-of-gyration/energy
features, trains a model, evaluates it, and writes plots.

The current weak point is the GROMACS dependency. The script falls back to the
old NGC image `nvcr.io/hpc/gromacs:2023.2`, and defaults `mdrun` to CPU mode.
The target workstation has RTX PRO 6000 Blackwell GPUs visible from the user's
interactive shell via `nvidia-smi`, with driver 580.126.09 and CUDA 13.0
reported by the driver. CUDA Toolkit 13.2 is available locally under
`/usr/local/cuda-13.2`, and CMake 3.28.3 is installed.

## Goal

Install a modern native CUDA-enabled GROMACS 2026.2 under
`$HOME/raid/tools/gromacs-2026.2`, then make the full MD E2E pipeline use that
native install for simulation, data extraction, model building, analysis, and
plotting.

## Non-Goals

- Do not keep relying on the old NGC GROMACS container.
- Do not redesign the scientific protocol beyond the existing short GB1 smoke
  workflow.
- Do not install system packages or modify global driver configuration from
  repository scripts.
- Do not make long production MD defaults. The E2E remains a fast validation
  workflow unless the user increases step counts.

## Architecture

### Native GROMACS Installer

Add `scripts/install_gromacs_2026_2.sh`.

The script will:

- Install into `${GROMACS_INSTALL_PREFIX:-$HOME/raid/tools/gromacs-2026.2}`.
- Use `${GROMACS_BUILD_ROOT:-$HOME/raid/tools/src/gromacs-2026.2-build}` for
  source and build artifacts.
- Download the official `gromacs-2026.2.tar.gz` source archive if not already
  present.
- Configure with CMake for NVIDIA CUDA:
  - `-DGMX_GPU=CUDA`
  - `-DCUDAToolkit_ROOT=${CUDA_HOME:-/usr/local/cuda}`
  - `-DGMX_BUILD_OWN_FFTW=ON`
  - `-DREGRESSIONTEST_DOWNLOAD=ON`
  - `-DCMAKE_INSTALL_PREFIX=<install prefix>`
- Build with `${GROMACS_BUILD_JOBS:-$(nproc)}`.
- Install into the prefix.
- Print the commands needed to source `bin/GMXRC` and verify `gmx --version`.

The installer will not use `sudo`. If prerequisite compilers, CMake, CUDA, or
network access are missing, it will fail with a direct message.

### GROMACS Discovery

Add a small shell helper, likely `scripts/gromacs_env.sh`, used by workstation
E2E scripts.

Discovery order:

1. `GMX_BIN`, if explicitly set.
2. `$HOME/raid/tools/gromacs-2026.2/bin/gmx`.
3. `gmx` or `gmx_mpi` on `PATH`.

The helper will expose:

- `resolve_gromacs_bin`
- `check_gromacs_version`
- `check_gpu_runtime`

`check_gpu_runtime` will run `nvidia-smi` only when GPU mode is requested. This
keeps CPU smoke tests possible in restricted shells while making GPU failures
clear.

### Full MD E2E Script

Update `scripts/e2e_full_md_workstation.sh`.

Behavior changes:

- Default `GMX_BIN` to the native GROMACS 2026.2 install.
- Default `PROMUT_FULL_MD_MDRUN_MODE` to `gpu`.
- Remove automatic Docker/NGC fallback from the default path.
- Keep an explicit container fallback only if the user sets
  `PROMUT_USE_GROMACS_CONTAINER=1`.
- Print GROMACS version, CUDA/GPU runtime status, selected mode, and output
  paths at startup.
- Fail early if GPU mode is requested but `nvidia-smi` is unavailable or
  GROMACS cannot run.

The scientific E2E flow remains:

1. Create an isolated Python virtual environment under the work root.
2. Install Python dependencies and the editable package.
3. Run tests.
4. Download GB1 PDB input.
5. Build mutant structures.
6. Run short GROMACS minimization, NVT, and production MD for each mutant.
7. Generate trajectory-derived files:
   - `rmsd_backbone.dat`
   - `gyrate.xvg`
   - `rmsf_10ns.xvg`
   - `energy.xvg`
8. Extract dynamic features into a CSV.
9. Train and evaluate the model.
10. Generate feature importance, SHAP where available, prediction, and residual
    plots.

### Python Pipeline Integration

The existing `scripts/run_pipeline.py` can remain broad and lightweight. The
real full-MD workstation E2E should stay in the shell script because it must
drive external GROMACS commands, interactive group selections, and hardware
checks.

If the work exposes duplicated shell logic, only extract small helpers. Avoid a
large Python orchestration rewrite in this pass.

## Error Handling

- Missing native GROMACS: print the expected install prefix and the installer
  command.
- Missing CUDA toolkit during install: print the detected CUDA search paths.
- GPU mode with no `nvidia-smi`: fail before simulations start.
- GROMACS command failure: allow `set -euo pipefail` to stop the E2E at the
  failing command.
- Model/plot failures: leave generated MD and feature files in the work root
  for inspection.

## Testing

Add focused tests for repository logic, not for compiling GROMACS:

- Installer help or dry-run behavior if implemented.
- GROMACS discovery order with temporary fake binaries.
- Workstation E2E config generation or helper behavior.
- Existing MD CLI test remains valid.

Manual verification after implementation:

1. Run `scripts/install_gromacs_2026_2.sh`.
2. Source `$HOME/raid/tools/gromacs-2026.2/bin/GMXRC`.
3. Run `gmx --version` and confirm CUDA support.
4. Run the full workstation E2E with small defaults:
   `PROMUT_FULL_MD_MAX_MUTANTS=2 PROMUT_FULL_MD_STEPS=100 scripts/e2e_full_md_workstation.sh`.
5. Confirm outputs exist under the work root: trajectories, feature CSV, model
   pickle, evaluation JSON, and figures.

## Open Operational Note

The user's interactive shell confirms two RTX PRO 6000 Blackwell GPUs via
`nvidia-smi`. A non-interactive subprocess in the assistant environment reported
an NVIDIA driver communication failure. The scripts should trust runtime checks
from the invoking shell and provide clear diagnostics if a restricted execution
context cannot see the driver.
