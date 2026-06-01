# Mutant Structure Generation

`promut-md build-mutants` creates one PDB per point mutation from a wild-type PDB and a CSV mutation table.

## Default Backend

By default, `promut-md build-mutants` uses the open-source PDBFixer/OpenMM backend:

```bash
python -m pip install openmm pdbfixer
promut-md build-mutants \
  --wild-type-pdb wt.pdb \
  --mutations mutations.csv \
  --output-dir mutants
```

This applies mutations with PDBFixer templates, rebuilds missing atoms, adds hydrogens at pH 7.0, and validates the requested residue.

## FoldX Backend

Use the FoldX backend for production-oriented mutant structures:

```bash
promut-md build-mutants \
  --wild-type-pdb wt.pdb \
  --mutations mutations.csv \
  --output-dir mutants \
  --backend foldx \
  --foldx-bin /path/to/foldx
```

The FoldX backend runs `RepairPDB` followed by `BuildModel`, validates that the requested residue was introduced, and writes `mutant_manifest.json` with FoldX run directories and mutation codes.

## Installing FoldX

FoldX requires registration/license acceptance, so the repo installer cannot fetch it from `apt`. By default, the installer uses:

```bash
~/raid/tools/foldx
```

If you already downloaded the licensed Linux archive, copy it there and run:

```bash
bash scripts/install_foldx.sh
```

Or pass an explicit archive/download location:

```bash
FOLDX_ARCHIVE=/path/to/foldx.zip bash scripts/install_foldx.sh
FOLDX_DOWNLOAD_URL='https://licensed-download-url' bash scripts/install_foldx.sh
```

The workstation E2E script automatically checks `~/raid/tools/foldx/foldx` and passes it to `promut-md build-mutants` when present.

## Mutation CSV

Use either explicit columns:

```csv
mutation_id,chain,wild_type,position,mutant
A23V,A,A,23,V
```

or a `mutation` column containing one-letter substitutions like `A23V`.

## Smoke-Test Backend

`--backend simple` is retained for CI and workflow plumbing tests only. It changes residue names in the PDB and validates the requested residue identity, but it does not rebuild side-chain coordinates, optimize rotamers, minimize, or relax the structure. Do not use it for production MD.

## Full MD Workstation E2E

For a real end-to-end MD smoke on the workstation, run:

```bash
bash scripts/e2e_full_md_workstation.sh
```

The script uses native `gmx`/`gmx_mpi` when available. If native GROMACS is not installed, it pulls and runs the NGC GROMACS container by default:

```bash
GROMACS_CONTAINER=nvcr.io/hpc/gromacs:2023.2 bash scripts/e2e_full_md_workstation.sh
```

This requires Docker with NVIDIA Container Toolkit and a recent host NVIDIA driver. The RTX PRO 6000 Blackwell workstation is expected to work with the container when `docker run --gpus all ... nvidia-smi` can see the GPUs.

The default full-MD E2E uses CPU `mdrun` inside the container for broad compatibility with Blackwell GPUs and older GROMACS container builds. To opt into GPU `mdrun` with a compatible image:

```bash
PROMUT_FULL_MD_MDRUN_MODE=gpu GROMACS_CONTAINER=<compatible-image> bash scripts/e2e_full_md_workstation.sh
```
