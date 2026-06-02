from src.visualization.visualize import plot_performance_by_range


def test_plot_performance_by_range_skips_empty_range_analysis(tmp_path):
    results_data = {"range_analysis": []}

    plot_performance_by_range(
        results_data=results_data,
        output_dir=str(tmp_path),
        params={"figures": {"dpi": 80}},
    )

    assert not (tmp_path / "mae_by_range.png").exists()
    assert not (tmp_path / "r2_by_range.png").exists()
