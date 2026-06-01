import pandas as pd

from run_pipeline_no_mds import analyze_mutation_counts, load_and_preprocess_data, train_model


def test_no_mds_data_preprocessing_loads_bundled_data():
    data = load_and_preprocess_data("data", 42)

    assert data["X"].shape == (312, 192)
    assert data["Y"].shape == (312,)
    assert data["X_train"].shape[0] == 186
    assert set(data["feature_sets"]) == {
        "MDpocket",
        "MD",
        "Seq",
        "Seq_MD",
        "MD_MDpocket",
        "Seq_MDpocket",
    }


def test_no_mds_training_has_sklearn_fallback_when_lightgbm_unavailable(monkeypatch, tmp_path):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "lightgbm":
            raise OSError("libomp unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    data = {
        "X_train": pd.DataFrame({"a": [0.0, 1.0, 2.0, 3.0], "b": [1.0, 1.5, 2.0, 2.5]}),
        "y_train": pd.Series([0.0, 1.0, 2.0, 3.0]),
        "X_val": pd.DataFrame({"a": [4.0, 5.0], "b": [3.0, 3.5]}),
        "y_val": pd.Series([4.0, 5.0]),
        "subset_name": "unit",
    }

    model_file = train_model(data, {}, str(tmp_path), 42, skip_optuna=True)

    assert model_file.endswith(".pkl")


def test_mutation_count_analysis_handles_current_biopython(tmp_path):
    result = analyze_mutation_counts("data", str(tmp_path))

    assert result is not None
    assert (tmp_path / "mutation_counts.csv").exists()
    assert (tmp_path / "mutation_statistics.json").exists()
