from pathlib import Path

import pandas as pd

import json
import stat
import sys

import pytest

from scripts.structure_generation.build_mutants import build_mutant_structures


PDB_TEXT = """\
ATOM      1  N   ALA A   1      11.104  13.207   8.678  1.00 20.00           N
ATOM      2  CA  ALA A   1      12.560  13.207   8.678  1.00 20.00           C
ATOM      3  C   ALA A   1      13.000  14.600   8.200  1.00 20.00           C
ATOM      4  O   ALA A   1      12.300  15.500   8.300  1.00 20.00           O
ATOM      5  CB  ALA A   1      13.000  12.100   7.700  1.00 20.00           C
ATOM      6  N   GLY A   2      14.200  14.800   7.700  1.00 20.00           N
ATOM      7  CA  GLY A   2      14.800  16.100   7.200  1.00 20.00           C
ATOM      8  C   GLY A   2      16.300  16.000   7.000  1.00 20.00           C
ATOM      9  O   GLY A   2      16.900  17.000   6.800  1.00 20.00           O
TER
END
"""


def test_build_mutant_structures_from_mutation_table(tmp_path):
    wt = tmp_path / "wt.pdb"
    wt.write_text(PDB_TEXT)
    mutations = tmp_path / "mutations.csv"
    pd.DataFrame(
        {
            "mutation_id": ["A1V"],
            "chain": ["A"],
            "wild_type": ["A"],
            "position": [1],
            "mutant": ["V"],
        }
    ).to_csv(mutations, index=False)

    manifest_file = build_mutant_structures(
        str(wt),
        str(mutations),
        str(tmp_path / "mutants"),
        backend="simple",
    )

    mutant_pdb = tmp_path / "mutants" / "A1V.pdb"
    assert Path(manifest_file).exists()
    assert mutant_pdb.exists()
    assert "VAL A   1" in mutant_pdb.read_text()


def test_production_backend_requires_foldx_binary(tmp_path):
    wt = tmp_path / "wt.pdb"
    wt.write_text(PDB_TEXT)
    mutations = tmp_path / "mutations.csv"
    pd.DataFrame({"mutation_id": ["A1V"], "chain": ["A"], "wild_type": ["A"], "position": [1], "mutant": ["V"]}).to_csv(
        mutations, index=False
    )

    with pytest.raises(FileNotFoundError, match="FoldX executable"):
        build_mutant_structures(str(wt), str(mutations), str(tmp_path / "mutants"), backend="foldx", foldx_bin="missing-foldx")


def test_pdbfixer_backend_reports_missing_optional_dependency(tmp_path, monkeypatch):
    wt = tmp_path / "wt.pdb"
    wt.write_text(PDB_TEXT)
    mutations = tmp_path / "mutations.csv"
    pd.DataFrame({"mutation_id": ["A1V"], "chain": ["A"], "wild_type": ["A"], "position": [1], "mutant": ["V"]}).to_csv(
        mutations, index=False
    )
    monkeypatch.setitem(sys.modules, "pdbfixer", None)

    with pytest.raises(ImportError, match="PDBFixer backend requires optional dependencies"):
        build_mutant_structures(str(wt), str(mutations), str(tmp_path / "mutants"), backend="pdbfixer")


def test_foldx_backend_invokes_repair_and_buildmodel(tmp_path):
    wt = tmp_path / "wt.pdb"
    wt.write_text(PDB_TEXT)
    mutations = tmp_path / "mutations.csv"
    pd.DataFrame({"mutation_id": ["A1V"], "chain": ["A"], "wild_type": ["A"], "position": [1], "mutant": ["V"]}).to_csv(
        mutations, index=False
    )
    foldx = tmp_path / "foldx"
    foldx.write_text(
        """#!/usr/bin/env python3
import shutil
import sys
from pathlib import Path
args = sys.argv[1:]
pdb = args[args.index('--pdb') + 1]
command = args[args.index('--command') + 1]
out = Path('.')
source = Path(pdb)
if command == 'RepairPDB':
    shutil.copy(source, out / f"{source.stem}_Repair.pdb")
elif command == 'BuildModel':
    text = source.read_text().replace('ALA A   1', 'VAL A   1')
    (out / f"{source.stem}_1.pdb").write_text(text)
else:
    raise SystemExit(2)
"""
    )
    foldx.chmod(foldx.stat().st_mode | stat.S_IXUSR)

    manifest_file = build_mutant_structures(
        str(wt),
        str(mutations),
        str(tmp_path / "mutants"),
        backend="foldx",
        foldx_bin=str(foldx),
    )

    manifest = json.loads(Path(manifest_file).read_text())
    mutant_pdb = tmp_path / "mutants" / "A1V.pdb"
    assert manifest["backend"] == "foldx"
    assert mutant_pdb.exists()
    assert "VAL A   1" in mutant_pdb.read_text()
    assert (tmp_path / "mutants" / "foldx_runs" / "A1V" / "individual_list.txt").read_text() == "AA1V;\n"
