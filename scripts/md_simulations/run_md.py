#!/usr/bin/env python3
"""Run or stage molecular dynamics simulations for ProMut-MD."""

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _find_gromacs():
    return shutil.which("gmx") or shutil.which("gmx_mpi")


def run_simulations(input_dir, output_dir, params=None):
    """Run available GROMACS simulations or stage inputs with an execution manifest.

    The repository cannot synthesize scientific MD trajectories without GROMACS and
    the user's force-field inputs. When GROMACS is unavailable this function still
    creates a deterministic output directory and manifest that records exactly what
    would be required to run the external step.
    """
    params = params or {}
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pdb_files = sorted(input_path.glob("*.pdb")) if input_path.exists() else []
    gromacs_bin = _find_gromacs()

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_dir": str(input_path),
        "output_dir": str(output_path),
        "gromacs_binary": gromacs_bin,
        "parameters": params,
        "simulations": [],
    }

    if not pdb_files:
        raise FileNotFoundError(
            f"No PDB inputs found in {input_path}. Add input structures or run with --skip-md."
        )

    for pdb_file in pdb_files:
        sim_dir = output_path / pdb_file.stem
        sim_dir.mkdir(parents=True, exist_ok=True)
        staged_pdb = sim_dir / pdb_file.name
        shutil.copy2(pdb_file, staged_pdb)

        record = {
            "name": pdb_file.stem,
            "input_pdb": str(pdb_file),
            "staged_pdb": str(staged_pdb),
            "status": "staged",
        }

        if gromacs_bin:
            version = subprocess.run(
                [gromacs_bin, "--version"],
                text=True,
                capture_output=True,
                check=False,
            )
            record["gromacs_version"] = version.stdout.splitlines()[0] if version.stdout else ""
            record["status"] = "ready_for_gromacs_execution"
        else:
            record["message"] = "GROMACS executable not found; install gmx/gmx_mpi to run MD."

        manifest["simulations"].append(record)

    manifest_file = output_path / "md_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("MD simulation inputs staged in %s", output_path)

    return str(output_path)
