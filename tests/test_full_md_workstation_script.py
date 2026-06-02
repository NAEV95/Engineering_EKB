from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "e2e_full_md_workstation.sh"


def test_full_md_script_sources_gromacs_helper():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'source "$ROOT_DIR/scripts/gromacs_env.sh"' in text


def test_full_md_script_defaults_to_gpu_mode():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'MDRUN_MODE="${PROMUT_FULL_MD_MDRUN_MODE:-gpu}"' in text


def test_full_md_script_uses_resolve_gromacs_bin():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'GMX_BIN="$(resolve_gromacs_bin)"' in text
