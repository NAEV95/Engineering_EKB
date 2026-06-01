from pathlib import Path

import pandas as pd

from scripts.excel_workflow import generate_figures, process_data, validate_excel_file


def test_excel_validation_accepts_numeric_sheet_string(tmp_path):
    path = tmp_path / "input.xlsx"
    pd.DataFrame(
        {
            "mutation_id": ["m1"],
            "protein": ["EKB"],
            "sequence": ["AAAA"],
            "position": [1],
        }
    ).to_excel(path, index=False)

    df = validate_excel_file(str(path), "0")

    assert df is not None
    assert len(df) == 1


def test_excel_workflow_predictions_are_data_derived(tmp_path):
    df = pd.DataFrame(
        {
            "mutation_id": ["m1", "m2"],
            "protein": ["EKB", "EKB"],
            "sequence": ["AAAA", "AAAAAA"],
            "position": [1, 5],
        }
    )

    output_file, results_file = process_data(
        df,
        str(tmp_path / "processed"),
        results_dir=str(tmp_path / "results"),
    )

    processed = pd.read_csv(output_file)
    results = pd.read_csv(results_file)

    assert processed["sequence_length"].tolist() == [4, 6]
    assert processed["relative_position"].tolist() == [0.25, 5 / 6]
    assert results["prediction"].nunique() > 1
    assert results["confidence"].between(0, 1).all()


def test_excel_workflow_generates_real_png_files(tmp_path):
    df = pd.DataFrame(
        {
            "mutation_id": ["m1", "m2", "m3"],
            "protein": ["A", "A", "B"],
            "sequence": ["AAAA", "AAAAAA", "AAA"],
            "position": [1, 5, 2],
            "prediction": [0.2, 0.7, 0.4],
        }
    )

    files = generate_figures(
        df,
        str(tmp_path / "results.csv"),
        figures_dir=str(tmp_path / "figures"),
    )

    assert len(files) == 2
    for file_name in files:
        data = Path(file_name).read_bytes()
        assert data.startswith(b"\x89PNG")
