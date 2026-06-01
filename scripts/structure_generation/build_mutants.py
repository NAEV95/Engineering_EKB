#!/usr/bin/env python3
"""Build point-mutant PDB structures from a wild-type PDB and mutation table."""

import argparse
import json
import logging
import re
import shutil
import subprocess
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pandas as pd
from Bio import PDB

logger = logging.getLogger(__name__)

AA_1_TO_3 = {
    "A": "ALA",
    "C": "CYS",
    "D": "ASP",
    "E": "GLU",
    "F": "PHE",
    "G": "GLY",
    "H": "HIS",
    "I": "ILE",
    "K": "LYS",
    "L": "LEU",
    "M": "MET",
    "N": "ASN",
    "P": "PRO",
    "Q": "GLN",
    "R": "ARG",
    "S": "SER",
    "T": "THR",
    "V": "VAL",
    "W": "TRP",
    "Y": "TYR",
}

AA_3_TO_1 = {value: key for key, value in AA_1_TO_3.items()}
MUTATION_RE = re.compile(r"^(?P<wt>[A-Z])(?P<position>\d+)(?P<mutant>[A-Z])$")


def _normalise_mutations(table):
    rows = []
    for _, row in table.iterrows():
        mutation_id = str(row.get("mutation_id", "")).strip()
        chain = str(row.get("chain", "A")).strip() or "A"

        if {"wild_type", "position", "mutant"}.issubset(table.columns):
            wild_type = str(row["wild_type"]).strip().upper()
            position = int(row["position"])
            mutant = str(row["mutant"]).strip().upper()
            if not mutation_id:
                mutation_id = f"{wild_type}{position}{mutant}"
        else:
            mutation = str(row.get("mutation", mutation_id)).strip().upper()
            match = MUTATION_RE.match(mutation)
            if not match:
                raise ValueError(
                    "Mutation table must contain wild_type/position/mutant columns "
                    "or a mutation string like A23V."
                )
            wild_type = match.group("wt")
            position = int(match.group("position"))
            mutant = match.group("mutant")
            mutation_id = mutation

        if wild_type not in AA_1_TO_3 or mutant not in AA_1_TO_3:
            raise ValueError(f"Unsupported amino-acid mutation: {mutation_id}")

        rows.append(
            {
                "mutation_id": mutation_id,
                "chain": chain,
                "wild_type": wild_type,
                "position": position,
                "mutant": mutant,
            }
        )
    return rows


def _find_residue(structure, chain_id, position):
    model = next(structure.get_models())
    chain = model[chain_id]
    for residue in chain:
        hetflag, resseq, _icode = residue.id
        if hetflag == " " and int(resseq) == int(position):
            return residue
    raise KeyError(f"Residue {chain_id}:{position} not found in wild-type structure")


def _mutate_structure(structure, mutation):
    mutant_structure = deepcopy(structure)
    residue = _find_residue(mutant_structure, mutation["chain"], mutation["position"])
    observed = AA_3_TO_1.get(residue.get_resname().upper())
    if observed and observed != mutation["wild_type"]:
        raise ValueError(
            f"{mutation['mutation_id']} expected wild type {mutation['wild_type']} "
            f"at {mutation['chain']}:{mutation['position']}, found {observed}."
        )
    residue.resname = AA_1_TO_3[mutation["mutant"]]
    return mutant_structure


def _validate_mutant_pdb(pdb_file, mutation):
    parser = PDB.PDBParser(QUIET=True)
    structure = parser.get_structure(mutation["mutation_id"], pdb_file)
    residue = _find_residue(structure, mutation["chain"], mutation["position"])
    observed = AA_3_TO_1.get(residue.get_resname().upper())
    if observed != mutation["mutant"]:
        raise ValueError(
            f"{pdb_file} validation failed for {mutation['mutation_id']}: "
            f"expected {mutation['mutant']}, found {observed}."
        )


def _foldx_mutation_code(mutation):
    return f"{mutation['wild_type']}{mutation['chain']}{mutation['position']}{mutation['mutant']};"


def _run_foldx(foldx_bin, command, pdb_file, cwd, extra_args=None):
    args = [foldx_bin, "--command", command, "--pdb", str(pdb_file)]
    if extra_args:
        args.extend(extra_args)
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"FoldX {command} failed with exit code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def _build_with_simple_backend(wild_type_structure, mutations, output_path):
    io = PDB.PDBIO()
    records = []
    for mutation in mutations:
        mutant_structure = _mutate_structure(wild_type_structure, mutation)
        output_file = output_path / f"{mutation['mutation_id']}.pdb"
        io.set_structure(mutant_structure)
        io.save(str(output_file))
        _validate_mutant_pdb(output_file, mutation)
        records.append({**mutation, "pdb": str(output_file), "backend_status": "residue_name_substitution"})
    return records


def _build_with_foldx_backend(wild_type_pdb, mutations, output_path, foldx_bin):
    resolved_foldx = shutil.which(foldx_bin) if foldx_bin else shutil.which("foldx")
    if not resolved_foldx:
        raise FileNotFoundError(
            "FoldX executable not found. Install FoldX and pass --foldx-bin, "
            "or explicitly use --backend simple for non-production plumbing tests."
        )

    foldx_root = output_path / "foldx_runs"
    foldx_root.mkdir(parents=True, exist_ok=True)
    records = []

    for mutation in mutations:
        run_dir = foldx_root / mutation["mutation_id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        input_pdb = run_dir / Path(wild_type_pdb).name
        shutil.copy2(wild_type_pdb, input_pdb)

        _run_foldx(resolved_foldx, "RepairPDB", input_pdb.name, run_dir)
        repaired_pdb = run_dir / f"{input_pdb.stem}_Repair.pdb"
        if not repaired_pdb.exists():
            repaired_pdb = input_pdb

        individual_list = run_dir / "individual_list.txt"
        individual_list.write_text(_foldx_mutation_code(mutation) + "\n", encoding="utf-8")
        _run_foldx(
            resolved_foldx,
            "BuildModel",
            repaired_pdb.name,
            run_dir,
            ["--mutant-file", individual_list.name],
        )

        candidates = sorted(run_dir.glob(f"{repaired_pdb.stem}_*.pdb"))
        if not candidates:
            candidates = sorted(run_dir.glob("*.pdb"))
        candidates = [candidate for candidate in candidates if candidate.name != repaired_pdb.name and candidate.name != input_pdb.name]
        if not candidates:
            raise FileNotFoundError(f"FoldX did not produce a mutant PDB for {mutation['mutation_id']}")

        output_file = output_path / f"{mutation['mutation_id']}.pdb"
        shutil.copy2(candidates[0], output_file)
        _validate_mutant_pdb(output_file, mutation)
        records.append(
            {
                **mutation,
                "pdb": str(output_file),
                "backend_status": "foldx_buildmodel",
                "foldx_run_dir": str(run_dir),
                "foldx_source_pdb": str(candidates[0]),
                "foldx_mutation_code": _foldx_mutation_code(mutation),
            }
        )

    return records


def build_mutant_structures(wild_type_pdb, mutations_file, output_dir, backend="foldx", foldx_bin=None):
    """Create one modelled PDB per mutation row and return the manifest path.

    The default ``foldx`` backend runs RepairPDB and BuildModel, validates the
    expected mutant residue, and records FoldX provenance. The ``simple`` backend
    is retained for plumbing tests only; it does not rebuild side chains.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    table = pd.read_csv(mutations_file)
    mutations = _normalise_mutations(table)
    parser = PDB.PDBParser(QUIET=True)
    wild_type_structure = parser.get_structure("wild_type", wild_type_pdb)

    for mutation in mutations:
        residue = _find_residue(wild_type_structure, mutation["chain"], mutation["position"])
        observed = AA_3_TO_1.get(residue.get_resname().upper())
        if observed and observed != mutation["wild_type"]:
            raise ValueError(
                f"{mutation['mutation_id']} expected wild type {mutation['wild_type']} "
                f"at {mutation['chain']}:{mutation['position']}, found {observed}."
            )

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "wild_type_pdb": str(wild_type_pdb),
        "mutations_file": str(mutations_file),
        "backend": backend,
        "structures": [],
    }

    if backend == "foldx":
        manifest["note"] = "FoldX RepairPDB + BuildModel backend; inspect FoldX output before production MD."
        manifest["foldx_bin"] = foldx_bin or "foldx"
        manifest["structures"] = _build_with_foldx_backend(wild_type_pdb, mutations, output_path, foldx_bin)
    elif backend == "simple":
        manifest["note"] = "Residue-name substitution only; no side-chain rebuild or relaxation performed."
        manifest["structures"] = _build_with_simple_backend(wild_type_structure, mutations, output_path)
    else:
        raise ValueError(f"Unsupported mutant structure backend: {backend}")

    manifest_file = output_path / "mutant_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Built %d mutant structures in %s", len(mutations), output_path)
    return str(manifest_file)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build point-mutant PDB structures")
    parser.add_argument("--wild-type-pdb", required=True)
    parser.add_argument("--mutations", required=True, help="CSV mutation table")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--backend", choices=["foldx", "simple"], default="foldx")
    parser.add_argument("--foldx-bin", default=None, help="Path/name of FoldX executable for --backend foldx")
    args = parser.parse_args(argv)
    build_mutant_structures(args.wild_type_pdb, args.mutations, args.output_dir, args.backend, args.foldx_bin)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
