import json

from src.models.evaluate_model import save_evaluation


def test_save_evaluation_includes_prediction_values(tmp_path):
    results_file = save_evaluation(
        metrics={"mae": 0.1},
        residual_stats={"mean": 0.0},
        range_analysis=[],
        output_dir=str(tmp_path),
        y_test=[0.0, 1.0],
        y_pred=[0.1, 0.9],
    )

    with open(results_file, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    assert data["y_test"] == [0.0, 1.0]
    assert data["y_pred"] == [0.1, 0.9]
