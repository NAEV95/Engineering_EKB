import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "gromacs_env.sh"


def run_bash(script, env=None):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["bash", "-c", script],
        text=True,
        capture_output=True,
        cwd=ROOT,
        env=merged_env,
        check=False,
    )


def test_resolve_gromacs_bin_prefers_explicit_gmx_bin(tmp_path):
    fake = tmp_path / "explicit-gmx"
    fake.write_text("#!/usr/bin/env bash\necho fake gmx\n", encoding="utf-8")
    fake.chmod(0o755)

    result = run_bash(
        f"source {HELPER}; resolve_gromacs_bin",
        env={
            "GMX_BIN": str(fake),
            "GROMACS_INSTALL_PREFIX": str(tmp_path / "missing-prefix"),
            "PATH": "/usr/bin:/bin",
        },
    )

    assert result.returncode == 0
    assert result.stdout.strip() == str(fake)


def test_resolve_gromacs_bin_prefers_install_prefix_before_path(tmp_path):
    prefix_gmx = tmp_path / "prefix" / "bin" / "gmx"
    path_gmx_dir = tmp_path / "path-bin"
    path_gmx = path_gmx_dir / "gmx"
    prefix_gmx.parent.mkdir(parents=True)
    path_gmx_dir.mkdir()
    prefix_gmx.write_text("#!/usr/bin/env bash\necho prefix\n", encoding="utf-8")
    path_gmx.write_text("#!/usr/bin/env bash\necho path\n", encoding="utf-8")
    prefix_gmx.chmod(0o755)
    path_gmx.chmod(0o755)

    result = run_bash(
        f"source {HELPER}; resolve_gromacs_bin",
        env={
            "GMX_BIN": "",
            "GROMACS_INSTALL_PREFIX": str(tmp_path / "prefix"),
            "PATH": f"{path_gmx_dir}:/usr/bin:/bin",
        },
    )

    assert result.returncode == 0
    assert result.stdout.strip() == str(prefix_gmx)


def test_check_gpu_runtime_allows_cpu_mode_without_nvidia_smi(tmp_path):
    result = run_bash(
        f"source {HELPER}; check_gpu_runtime cpu",
        env={"PATH": "/usr/bin:/bin"},
    )

    assert result.returncode == 0
