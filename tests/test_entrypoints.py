import subprocess
import sys


def run_cmd(*args):
    return subprocess.run(args, text=True, capture_output=True, check=False)


def test_main_pipeline_help_does_not_import_training_stack():
    result = run_cmd(sys.executable, "scripts/run_pipeline.py", "--help")

    assert result.returncode == 0, result.stderr
    assert "Run the ProMut-MD pipeline" in result.stdout


def test_no_mds_default_config_exists():
    from run_pipeline_no_mds import parse_args

    args = parse_args([])

    assert args.config == "config/default.yml"


def test_console_cli_help_works_after_install():
    result = run_cmd(sys.executable, "-m", "src.cli", "--help")

    assert result.returncode == 0, result.stderr
    assert "ProMut-MD" in result.stdout


def test_build_mutants_default_backend_is_pdbfixer():
    from src.cli import build_parser

    args = build_parser().parse_args(
        [
            "build-mutants",
            "--wild-type-pdb",
            "wt.pdb",
            "--mutations",
            "mutations.csv",
            "--output-dir",
            "mutants",
        ]
    )

    assert args.backend == "pdbfixer"


def test_full_pipeline_all_stages_skipped_completes(tmp_path):
    result = run_cmd(
        sys.executable,
        "scripts/run_pipeline.py",
        "--skip-md",
        "--skip-features",
        "--skip-training",
        "--skip-evaluation",
        "--skip-visualization",
        "--output-dir",
        str(tmp_path),
    )

    assert result.returncode == 0, result.stderr
    assert "Pipeline completed successfully" in result.stderr
