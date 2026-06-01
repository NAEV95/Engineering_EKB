#!/usr/bin/env python3
"""Smoke tests for the optional LazyPredict workflow."""

import pytest


def test_lazypredict_smoke_workflow(tmp_path):
    try:
        from lazypredict.Supervised import LazyRegressor
    except (ImportError, OSError) as exc:
        pytest.skip(f"LazyPredict runtime unavailable: {exc}")

    import os

    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import MinMaxScaler

    output_dir = tmp_path / "lazypredict_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    v1 = pd.read_excel("data/new_dataset_1.xlsx")
    v3 = pd.read_excel("data/new_dataset_3.xlsx")
    v4 = pd.read_excel("data/new_dataset_4.xlsx")
    v5 = pd.read_excel("data/new_dataset_5.xlsx")
    v6 = pd.read_excel("data/new_dataset_6.xlsx")

    # Merge datasets
    vavg = pd.concat([v1, v3, v4, v5, v6]).groupby(level=0).mean()
    vavg = vavg.drop(['DELTA30'], axis=1)
    df = pd.read_excel('data/new_df_66.xlsx', engine='openpyxl')
    seq_and_y = df.iloc[:, 126:]
    vavg = pd.concat([vavg, seq_and_y], axis=1)

    # Extract features and target
    X = vavg.drop(['DELTA30'], axis=1)
    Y = vavg['DELTA30']

    # Scale features
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    X = pd.DataFrame(X_scaled, index=X.index, columns=X.columns)
    X.columns = [col.split('.1')[0] if col != 'h_3.10' else col for col in X.columns]

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

    # Run LazyPredict
    reg = LazyRegressor(verbose=0, ignore_warnings=True, custom_metric=None)
    models, predictions = reg.fit(X_train, X_test, y_train, y_test)

    assert not models.empty

    # Save results
    results_file = os.path.join(output_dir, "lazypredict_results.csv")
    models.to_csv(results_file)

    # Generate visualization
    plt.figure(figsize=(12, 8))
    sns.set_style("whitegrid")
    ax = sns.barplot(x=models.index[:20], y="R-Squared", data=models.head(20))
    plt.title('LazyPredict Model Comparison')
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "lazypredict_comparison.png"), dpi=300)
    plt.close()

    # Generate visualization for RMSE
    plt.figure(figsize=(12, 8))
    sns.set_style("whitegrid")
    ax = sns.barplot(x=models.index[:20], y="RMSE", data=models.head(20))
    plt.title('LazyPredict Model Comparison (RMSE)')
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "lazypredict_rmse_comparison.png"), dpi=300)
    plt.close()

    assert (output_dir / "lazypredict_results.csv").exists()
    assert (output_dir / "lazypredict_comparison.png").exists()
