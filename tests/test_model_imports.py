def test_training_module_imports_without_native_lightgbm_runtime():
    import src.models.train_model as train_model

    assert hasattr(train_model, "train_model")


def test_md_runner_module_exists():
    from scripts.md_simulations.run_md import run_simulations

    assert callable(run_simulations)
