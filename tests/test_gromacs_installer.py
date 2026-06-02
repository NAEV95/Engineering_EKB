import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_gromacs_2026_2.sh"


def test_installer_help_mentions_prefix_and_version():
    result = subprocess.run(
        ["bash", str(INSTALLER), "--help"],
        text=True,
        capture_output=True,
        cwd=ROOT,
        check=False,
    )

    assert result.returncode == 0
    assert "GROMACS 2026.2" in result.stdout
    assert "GROMACS_INSTALL_PREFIX" in result.stdout


def test_installer_dry_run_prints_cmake_cuda_flags(tmp_path):
    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--dry-run",
        ],
        text=True,
        capture_output=True,
        cwd=ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
            "CUDA_HOME": "/usr/local/cuda",
            "GROMACS_INSTALL_PREFIX": str(tmp_path / "tools" / "gromacs-2026.2"),
            "GROMACS_BUILD_ROOT": str(tmp_path / "tools" / "src" / "gromacs-build"),
        },
        check=False,
    )

    assert result.returncode == 0
    assert "-DGMX_GPU=CUDA" in result.stdout
    assert "-DGMX_BUILD_OWN_FFTW=ON" in result.stdout
    assert "-DREGRESSIONTEST_DOWNLOAD=ON" in result.stdout
