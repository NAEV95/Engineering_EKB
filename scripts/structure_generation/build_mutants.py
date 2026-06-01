#!/usr/bin/env python3
"""Build simple point-mutant PDB structures from a wild-type PDB and mutation table."""

import argparse
import json
import logging
import re
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


def build_mutant_structures(wild_type_pdb, mutations_file, output_dir):
    """Create one mutated PDB per mutation row and return the manifest path.

    This performs residue-name substitution for point-mutant workflow testing. It
    does not rebuild side-chain coordinates or relax structures; use FoldX,
    MODELLER, PyRosetta, or another modelling tool before production MD.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    table = pd.read_csv(mutations_file)
    mutations = _normalise_mutations(table)
    parser = PDB.PDBParser(QUIET=True)
    wild_type_structure = parser.get_structure("wild_type", wild_type_pdb)
    io = PDB.PDBIO()

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "wild_type_pdb": str(wild_type_pdb),
        "mutations_file": str(mutations_file),
        "note": "Residue-name substitution only; no side-chain rebuild or relaxation performed.",
        "structures": [],
    }

    for mutation in mutations:
        mutant_structure = _mutate_structure(wild_type_structure, mutation)
        output_file = output_path / f"{mutation['mutation_id']}.pdb"
        io.set_structure(mutant_structure)
        io.save(str(output_file))
        manifest["structures"].append({**mutation, "pdb": str(output_file)})

    manifest_file = output_path / "mutant_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Built %d mutant structures in %s", len(mutations), output_path)
    return str(manifest_file)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build point-mutant PDB structures")
    parser.add_argument("--wild-type-pdb", required=True)
    parser.add_argument("--mutations", required=True, help="CSV mutation table")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    build_mutant_structures(args.wild_type_pdb, args.mutations, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
