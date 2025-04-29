#!/usr/bin/env python3
"""
Test script for lazypredict
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from lazypredict.Supervised import LazyRegressor
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Create output directory
os.makedirs("output/lazypredict_test", exist_ok=True)

# Load data
try:
    print("Loading data...")
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
    
    print(f"Data loaded. Shape of X: {X.shape}, Shape of Y: {Y.shape}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=42)
    print(f"Train shapes: X:{X_train.shape}, y:{y_train.shape}")
    print(f"Test shapes: X:{X_test.shape}, y:{y_test.shape}")
    
    # Run LazyPredict
    print("Running LazyPredict...")
    reg = LazyRegressor(verbose=1, ignore_warnings=True, custom_metric=None)
    models, predictions = reg.fit(X_train, X_test, y_train, y_test)
    
    # Show results
    print("\nLazyPredict Results:")
    print(models.head(5))
    
    # Save results
    results_file = os.path.join("output/lazypredict_test", "lazypredict_results.csv")
    models.to_csv(results_file)
    print(f"Results saved to {results_file}")
    
    # Generate visualization
    plt.figure(figsize=(12, 8))
    sns.set_style("whitegrid")
    ax = sns.barplot(x=models.index[:20], y="R-Squared", data=models.head(20))
    plt.title('LazyPredict Model Comparison')
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join("output/lazypredict_test", "lazypredict_comparison.png"), dpi=300)
    plt.close()
    
    # Generate visualization for RMSE
    plt.figure(figsize=(12, 8))
    sns.set_style("whitegrid")
    ax = sns.barplot(x=models.index[:20], y="RMSE", data=models.head(20))
    plt.title('LazyPredict Model Comparison (RMSE)')
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join("output/lazypredict_test", "lazypredict_rmse_comparison.png"), dpi=300)
    plt.close()
    
    print("Visualizations saved to output/lazypredict_test/")
    
except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc() 