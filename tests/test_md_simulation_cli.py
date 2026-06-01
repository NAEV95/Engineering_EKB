import subprocess
import sys


def test_md_simulation_cli_help():
    result = subprocess.run(
        [sys.executable, "scripts/md_simulations/run_md.py", "--help"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Stage or run MD simulation inputs" in result.stdout
