# Mutant Structure Generation

`promut-md build-mutants` creates one PDB per point mutation from a wild-type PDB and a CSV mutation table.

## Production Backend

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

## Mutation CSV

Use either explicit columns:

```csv
mutation_id,chain,wild_type,position,mutant
A23V,A,A,23,V
```

or a `mutation` column containing one-letter substitutions like `A23V`.

## Smoke-Test Backend

`--backend simple` is retained for CI and workflow plumbing tests only. It changes residue names in the PDB and validates the requested residue identity, but it does not rebuild side-chain coordinates, optimize rotamers, minimize, or relax the structure. Do not use it for production MD.
