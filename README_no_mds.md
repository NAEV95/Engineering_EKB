# Running the Pipeline Without MDS for new_df_66

This solution allows you to run the machine learning pipeline without having to perform Multidimensional Scaling (MDS) on the `new_df_66` dataset. Instead, it uses the existing `new_df_66.xlsx` file directly. The pipeline now includes advanced Optuna hyperparameter optimization for improved model performance and automatic feature subset comparison.

## Key Features

- **Multiple Feature Subset Analysis**: Automatically trains and evaluates models on 7 different feature subsets to identify the most predictive features.
- **Advanced Hyperparameter Optimization**: Uses Optuna with efficient TPE sampling and pruning for optimal model performance.
- **Comprehensive Visualizations**: Generates detailed comparative visualizations across feature subsets and model configurations.
- **High-Performance Models**: Implements multiple boosting strategies and advanced regularization techniques.

## Prerequisites

Make sure you have the following dependencies installed. We recommend using `uv` for faster and more reliable package installation:

```bash
# Install uv if you don't have it
pip install uv

# Create a virtual environment
uv venv .venv

# Activate the environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies with uv
uv pip install pandas numpy scikit-learn matplotlib seaborn lightgbm shap pyyaml openpyxl optuna
```

You can also install dependencies directly with pip:

```bash
pip install pandas numpy scikit-learn matplotlib seaborn lightgbm shap pyyaml openpyxl optuna
```

## Data Requirements

The script expects the following files to be present in the data directory:

1. `new_dataset_1.xlsx`
2. `new_dataset_3.xlsx`
3. `new_dataset_4.xlsx`
4. `new_dataset_5.xlsx`
5. `new_dataset_6.xlsx`
6. `new_df_66.xlsx` (the pre-computed file that we're using instead of running MDS)

## Running the Pipeline

### Option 1: Using the Batch File (Windows)

The simplest way to run the pipeline is to use the provided batch file:

1. Double-click on `run_pipeline_no_mds.bat`
2. The script will execute and display progress in the command window
3. Results will be saved in the `output` directory

### Option 2: Running the Python Script Directly

You can also run the Python script directly with custom arguments:

```bash
# Run with default settings (includes hyperparameter optimization on all feature subsets)
python run_pipeline_no_mds.py --data-dir "data" --output-dir "output"

# Skip hyperparameter optimization and use default parameters
python run_pipeline_no_mds.py --data-dir "data" --output-dir "output" --skip-optuna

# Run with more Optuna trials for better hyperparameter optimization
python run_pipeline_no_mds.py --data-dir "data" --output-dir "output" --optuna-trials 100

# Run a quick test with minimal trials
python run_pipeline_no_mds.py --data-dir "data" --output-dir "output" --optuna-trials 5
```

Command-line arguments:

- `--data-dir`: Directory containing the input data files (default: "data")
- `--output-dir`: Directory to save the output files (default: "output")
- `--config`: Path to a YAML configuration file (default: "config/default.yml")
- `--random-seed`: Random seed for reproducibility (default: 3031)
- `--optuna-trials`: Number of trials for Optuna hyperparameter optimization (default: 50)
- `--skip-optuna`: Skip hyperparameter optimization and use default parameters

## Output

The pipeline will generate the following outputs in the specified output directory:

1. **Models**: 
   - Trained LightGBM models for each feature subset saved in pickle format
   - Results of hyperparameter optimization for each subset
   - Detailed optimization trial history

2. **Results**: 
   - Feature subset comparison showing which feature combinations perform best
   - Evaluation metrics for each subset including:
     - MAE (Mean Absolute Error)
     - RMSE (Root Mean Square Error)
     - R² (Coefficient of Determination)
     - Explained Variance
   - Residuals analysis
   - Best hyperparameters for each feature subset

3. **Figures**: 
   - Feature importance plots for each subset
   - Prediction scatter plots comparing true vs predicted values
   - SHAP value plots for model interpretability and feature impact
   - Residuals distribution and analysis
   - Hyperparameter optimization history and parameter importance plots
   - Detailed SHAP plots for top features
   - Comparative visualizations showing performance across all feature subsets

4. **Logs**: Detailed logs are saved in `promut_md_pipeline_no_mds.log`

## Feature Subsets Analyzed

The pipeline automatically trains and evaluates models on the following feature subsets:

1. **All_Features**: The complete feature set
2. **MDpocket**: Features derived from MDpocket analysis (columns 0-80)
3. **MD**: Features related to Molecular Dynamics (columns 80-112)
4. **Seq**: Sequence-based features (columns 112+)
5. **Seq_MD**: Combined Sequence and MD features
6. **MD_MDpocket**: Combined MD and MDpocket features
7. **Seq_MDpocket**: Combined Sequence and MDpocket features

For each subset, a separate model is trained with optimized hyperparameters, and results are compared to identify the most predictive feature combinations.

## Hyperparameter Optimization

The pipeline uses an advanced Optuna configuration for hyperparameter optimization of the LightGBM model with the following improvements:

- **Multiple Boosting Types**: Tests GBDT, DART, and GOSS boosting algorithms
- **Adaptive Early Stopping**: Automatically calculates early stopping rounds based on model complexity
- **Tree Structure Optimization**: Fine-tunes tree depth, leaves, and node configurations
- **Regularization Control**: Optimizes L1/L2 regularization to prevent overfitting
- **Learning Rate Tuning**: Tests learning rates with logarithmic scaling for more efficient searching
- **Efficient TPE Sampling**: Uses Tree-structured Parzen Estimator (TPE) for intelligent parameter sampling
- **Model Pruning**: Implements median pruning to terminate unpromising trials early

The hyperparameters optimized include:

- `boosting_type`: The boosting algorithm to use (GBDT, DART, or GOSS)
- `learning_rate`: The rate at which the model learns (0.005 to 0.1)
- `n_estimators`: Number of trees in the model (50 to 500)
- `max_depth`: Maximum depth of each tree (3 to 12)
- `num_leaves`: Maximum number of leaves in each tree (20 to 150)
- `min_child_samples`: Minimum samples required for a leaf node (5 to 50)
- `min_child_weight`: Minimum sum of instance weight needed in a child (1e-5 to 1.0)
- `subsample`: Fraction of samples used for training trees (0.5 to 1.0)
- `colsample_bytree`: Fraction of features used for training trees (0.5 to 1.0)
- `reg_alpha`: L1 regularization term (1e-8 to 10.0)
- `reg_lambda`: L2 regularization term (1e-8 to 10.0)
- `max_bin`: Maximum number of discrete bins for bucketing continuous features (100 to 300)

Plus additional boosting-type specific parameters.

## Performance Improvements

The pipeline has been enhanced with several performance-improving features:

1. **R² Penalty**: Models with negative R² values are penalized to guide the search toward better solutions
2. **Error Handling**: Robust error handling for failed trials with graceful fallbacks
3. **Combined Training**: Final models are trained on combined training and validation data
4. **Advanced Visualization**: Detailed performance metrics and comparisons across feature subsets
5. **Feature Importance Analysis**: Comprehensive analysis of which features contribute most to predictions

## Troubleshooting

If you encounter any issues:

1. Check the log file for detailed error messages
2. Ensure all required data files are in the correct location
3. Verify that all dependencies are installed correctly, especially `openpyxl` for Excel file reading and `optuna` for hyperparameter optimization
4. If you get errors related to LightGBM parameters, check that the config file has the correct nesting of parameters
5. For visualization errors, ensure matplotlib and seaborn are properly installed
6. If hyperparameter optimization is taking too long, try reducing the number of trials with `--optuna-trials`
7. If memory issues occur, try running with `--skip-optuna` to use default parameters
8. For any feature subset-specific errors, check the respective logs in the output subdirectories 