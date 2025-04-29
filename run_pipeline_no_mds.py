#!/usr/bin/env python3
"""
Modified pipeline script that skips MDS calculation for new_df_66 dataset
"""

import os
import sys
import argparse
import yaml
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import optuna
from sklearn.metrics import mean_squared_error, r2_score
from Bio import PDB

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("promut_md_pipeline_no_mds.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run ML pipeline without MDS calculation')
    
    # Input and output directories
    parser.add_argument('--data-dir', type=str, default='data', 
                        help='Directory containing input data files')
    parser.add_argument('--output-dir', type=str, default='output', 
                        help='Directory to save output files')
    parser.add_argument('--config', type=str, default='config.json', 
                        help='Path to configuration file')
    
    # Randomization and optimization parameters
    parser.add_argument('--random-seed', type=int, default=42, 
                        help='Random seed for reproducibility')
    parser.add_argument('--optuna-trials', type=int, default=100, 
                        help='Number of Optuna hyperparameter optimization trials')
    parser.add_argument('--skip-optuna', action='store_true', 
                        help='Skip Optuna hyperparameter optimization')
    
    # New functionality parameters
    parser.add_argument('--skip-bootstrap', action='store_true',
                        help='Skip bootstrap analysis for statistical significance')
    parser.add_argument('--bootstrap-iterations', type=int, default=1000,
                        help='Number of bootstrap iterations for statistical analysis')
    parser.add_argument('--compare-with-ddmut', action='store_true',
                        help='Compare model predictions with DDMut predictions')
    
    return parser.parse_args()

def load_config(config_path):
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except FileNotFoundError:
        logger.warning(f"Configuration file {config_path} not found. Using default settings.")
        return {
            'paths': {
                'data': {
                    'raw': 'data/raw',
                    'processed': 'data/processed',
                    'results': 'data/results'
                },
                'figures': 'figures',
                'models': 'models'
            }
        }

def define_optuna_objective(X_train, y_train, X_val, y_val, random_seed):
    """Define the objective function for Optuna hyperparameter optimization"""
    from lightgbm import LGBMRegressor
    from sklearn.metrics import mean_squared_error, r2_score
    import numpy as np
    
    def objective(trial):
        """Objective function for Optuna optimization of LightGBM hyperparameters"""
        # Define the hyperparameters to optimize
        param = {
            'objective': 'regression',
            'metric': 'rmse',
            'verbosity': -1,
            'boosting_type': trial.suggest_categorical('boosting_type', ['gbdt', 'dart', 'goss']),
            'random_state': random_seed,
            
            # Learning parameters
            'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
            'n_estimators': trial.suggest_int('n_estimators', 50, 500),
            
            # Tree structure parameters
            'max_depth': trial.suggest_int('max_depth', 3, 12),
            'num_leaves': trial.suggest_int('num_leaves', 20, 150),
            'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),
            'min_child_weight': trial.suggest_float('min_child_weight', 1e-5, 1.0, log=True),
            
            # Sampling parameters
            'subsample': trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            
            # Regularization parameters
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
            
            # Leaf node parameters
            'max_bin': trial.suggest_int('max_bin', 100, 300),
        }
        
        # Adjust parameters based on boosting type
        if param['boosting_type'] == 'goss':
            # GOSS doesn't use subsample
            param.pop('subsample', None)
            param['top_rate'] = trial.suggest_float('top_rate', 0.1, 0.5)
            param['other_rate'] = trial.suggest_float('other_rate', 0.05, 0.5)
        elif param['boosting_type'] == 'dart':
            param['drop_rate'] = trial.suggest_float('drop_rate', 0.01, 0.5)
            param['skip_drop'] = trial.suggest_float('skip_drop', 0.01, 0.5)
        
        # Early stopping parameters
        early_stopping_rounds = int(param['n_estimators'] * 0.1)  # 10% of max iterations
        
        # Train the model with the suggested hyperparameters
        try:
            model = LGBMRegressor(**param)
            # Try with verbose parameter
            try:
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    eval_metric='rmse',
                    early_stopping_rounds=early_stopping_rounds,
                    verbose=False
                )
            except TypeError:
                # Try without verbose for compatibility with different LightGBM versions
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    eval_metric='rmse',
                    early_stopping_rounds=early_stopping_rounds
                )
            
            # Predict on validation set and calculate metrics
            preds = model.predict(X_val)
            rmse = np.sqrt(mean_squared_error(y_val, preds))
            r2 = r2_score(y_val, preds)
            
            # Penalize models with very poor R² to guide the search
            if r2 < 0:  # R² can be negative for very poor models
                penalty = 1 - r2  # Increase penalty for negative R²
                rmse = rmse * (1 + penalty)
            
            return rmse
        except Exception as e:
            # Return a high value if the model fails
            logger.warning(f"Trial failed with parameters: {param}. Error: {str(e)}")
            return float('inf')
    
    return objective

def load_and_preprocess_data(data_dir, random_seed):
    """Load and preprocess the data without performing MDS"""
    logger.info("Loading and preprocessing data (skipping MDS calculation)")
    
    # Create data paths
    os.makedirs(data_dir, exist_ok=True)
    
    try:
        # Load the datasets directly
        v1 = pd.read_excel(os.path.join(data_dir, "new_dataset_1.xlsx"))
        v3 = pd.read_excel(os.path.join(data_dir, "new_dataset_3.xlsx"))
        v4 = pd.read_excel(os.path.join(data_dir, "new_dataset_4.xlsx"))
        v5 = pd.read_excel(os.path.join(data_dir, "new_dataset_5.xlsx"))
        v6 = pd.read_excel(os.path.join(data_dir, "new_dataset_6.xlsx"))
        
        # Instead of running MDS, we directly use the existing new_df_66.xlsx file
        logger.info("Using existing new_df_66.xlsx file (skipping MDS calculation)")
        df = pd.read_excel(os.path.join(data_dir, "new_df_66.xlsx"), engine='openpyxl')
        
        # Merge the datasets
        vavg = pd.concat([v1, v3, v4, v5, v6]).groupby(level=0).mean()
        vavg = vavg.drop(['DELTA30'], axis=1)
        
        # Extract sequence information and targets from new_df_66
        seq_and_y = df.iloc[:, 126:]
        vavg = pd.concat([vavg, seq_and_y], axis=1)
        
        # Extract features and target
        X = vavg.drop(['DELTA30'], axis=1)
        Y = vavg['DELTA30']
        
        # Scale features
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(X)
        X = pd.DataFrame(X_scaled, index=X.index, columns=X.columns)
        
        # Fix column names (if needed)
        X.columns = [col.split('.1')[0] if col != 'h_3.10' else col for col in X.columns]
        
        # Split data into train, validation and test sets
        X_train_val, X_test, y_train_val, y_test = train_test_split(X, Y, test_size=0.2, random_state=random_seed)
        X_train, X_val, y_train, y_val = train_test_split(X_train_val, y_train_val, test_size=0.25, random_state=random_seed)
        
        # Create feature subsets
        MDpocket = X.iloc[:, :80]
        MD = X.iloc[:, 80:112]
        Seq = X.iloc[:, 112:]
        Seq_MD = X.iloc[:, 80:]
        MD_MDpocket = X.iloc[:, :112]
        Seq_MDpocket = pd.concat([MDpocket, Seq], axis=1)
        
        logger.info(f"Data preprocessing completed. Training set size: {X_train.shape}, Validation set size: {X_val.shape}, Test set size: {X_test.shape}")
        
        return {
            'X': X,
            'Y': Y,
            'X_train': X_train,
            'X_val': X_val,
            'X_test': X_test,
            'y_train': y_train,
            'y_val': y_val,
            'y_test': y_test,
            'feature_sets': {
                'MDpocket': MDpocket,
                'MD': MD,
                'Seq': Seq,
                'Seq_MD': Seq_MD,
                'MD_MDpocket': MD_MDpocket,
                'Seq_MDpocket': Seq_MDpocket
            }
        }
    except Exception as e:
        logger.error(f"Error in data preprocessing: {str(e)}")
        raise

def run_lazypredict(data, output_dir, random_seed):
    """Run lazypredict to evaluate multiple regression models"""
    try:
        from lazypredict.Supervised import LazyRegressor
        import matplotlib.pyplot as plt
        import seaborn as sns
        import numpy as np
        
        logger.info("Running LazyPredict to evaluate multiple regression models")
        
        # Create directory for results
        lazypredict_dir = os.path.join(output_dir, 'lazypredict')
        os.makedirs(lazypredict_dir, exist_ok=True)
        
        # Extract data
        X_train = data['X_train']
        y_train = data['y_train']
        X_test = data['X_test']
        y_test = data['y_test']
        subset_name = data.get('subset_name', 'all_features')
        
        # Initialize and run LazyRegressor
        reg = LazyRegressor(verbose=0, ignore_warnings=True, custom_metric=None)
        models, predictions = reg.fit(X_train, X_test, y_train, y_test)
        
        # Save results
        results_file = os.path.join(lazypredict_dir, f"lazypredict_results_{subset_name}.csv")
        models.to_csv(results_file)
        
        # Generate visualization
        plt.figure(figsize=(12, 8))
        sns.set_style("whitegrid")
        ax = sns.barplot(x=models.index, y="R-Squared", data=models)
        plt.title(f'LazyPredict Model Comparison - {subset_name}')
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.savefig(os.path.join(lazypredict_dir, f"lazypredict_comparison_{subset_name}.png"), dpi=300)
        plt.close()
        
        # Generate visualization for RMSE
        plt.figure(figsize=(12, 8))
        sns.set_style("whitegrid")
        ax = sns.barplot(x=models.index, y="RMSE", data=models)
        plt.title(f'LazyPredict Model Comparison (RMSE) - {subset_name}')
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.savefig(os.path.join(lazypredict_dir, f"lazypredict_rmse_comparison_{subset_name}.png"), dpi=300)
        plt.close()
        
        logger.info(f"LazyPredict completed for {subset_name}. Results saved to {results_file}")
        
        # Get top 3 models
        top_models = models.head(3).index.tolist()
        logger.info(f"Top 3 models for {subset_name}: {', '.join(top_models)}")
        
        return {
            'top_models': top_models,
            'results_file': results_file
        }
        
    except Exception as e:
        logger.error(f"Error in LazyPredict evaluation: {str(e)}")
        logger.info("Continuing pipeline without LazyPredict results")
        return None

def train_model(data, model_params, output_dir, random_seed, optuna_trials=50, skip_optuna=False):
    """Train a model using the preprocessed data with hyperparameter optimization"""
    try:
        # Import here to avoid dependency if training is skipped
        from lightgbm import LGBMRegressor
        from sklearn.metrics import mean_squared_error, r2_score
        import pickle
        import json
        import numpy as np
        
        # Create directory for model
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract data
        X_train = data['X_train']
        y_train = data['y_train']
        X_val = data['X_val']
        y_val = data['y_val']
        subset_name = data.get('subset_name', 'all_features')
        
        # Get feature count
        num_features = X_train.shape[1]
        logger.info(f"Training model for {subset_name} with {num_features} features")
        
        # Check if we have enough data for this subset
        if X_train.shape[0] < 20:  # Define a minimum number of samples
            logger.warning(f"Not enough training samples ({X_train.shape[0]}) for {subset_name}. Using default parameters.")
            skip_optuna = True
        
        # Track optimization results
        optimization_history = []
        
        if skip_optuna:
            logger.info("Skipping hyperparameter optimization and using default/config parameters")
            # Use default parameters if not specified
            params = model_params if model_params else {
                'objective': 'regression',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'learning_rate': 0.05,
                'max_depth': 5,
                'num_leaves': 31,
                'n_estimators': 100,
                'random_state': random_seed
            }
            
            logger.info(f"Training LightGBM model with parameters: {params}")
            
            # Initialize and train model
            model = LGBMRegressor(**params)
            # Fix: verbose parameter depends on LightGBM version
            try:
                model.fit(X_train, y_train, eval_set=[(X_val, y_val)], eval_metric='rmse', verbose=False)
            except TypeError:
                # Try without verbose for compatibility with different LightGBM versions
                logger.info("LightGBM version doesn't support verbose parameter, trying without it")
                model.fit(X_train, y_train, eval_set=[(X_val, y_val)], eval_metric='rmse')
            
            # Evaluate on validation set
            val_preds = model.predict(X_val)
            val_rmse = np.sqrt(mean_squared_error(y_val, val_preds))
            logger.info(f"Validation RMSE with default parameters: {val_rmse:.4f}")
            
            best_params = params
            best_score = val_rmse
        else:
            logger.info(f"Starting hyperparameter optimization with Optuna ({optuna_trials} trials)")
            
            # Configure Optuna for hyperparameter optimization
            import optuna
            from optuna.samplers import TPESampler
            
            # Use TPE sampler which performs well for hyperparameter optimization
            sampler = TPESampler(seed=random_seed)
            
            # Create Optuna study with pruning
            pruner = optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=10)
            study = optuna.create_study(direction='minimize', sampler=sampler, pruner=pruner)
            
            # Define the objective function
            objective = define_optuna_objective(X_train, y_train, X_val, y_val, random_seed)
            
            # Run the optimization
            study.optimize(objective, n_trials=optuna_trials)
            
            # Get best parameters and create model
            best_params = study.best_params
            best_score = study.best_value
            
            # Add fixed parameters
            best_params['random_state'] = random_seed
            best_params['objective'] = 'regression'
            best_params['metric'] = 'rmse'
            
            logger.info(f"Best hyperparameters found: {best_params}")
            logger.info(f"Best validation RMSE: {best_score:.4f}")
            
            # Record optimization history
            optimization_history = [
                {
                    'trial': trial.number,
                    'params': trial.params,
                    'value': trial.value,
                    'state': str(trial.state)
                }
                for trial in study.trials
            ]
            
            # Save optimization history
            optuna_results = {
                'best_params': best_params,
                'best_score': best_score,
                'num_features': num_features,
                'subset_name': subset_name,
                'trials': optimization_history
            }
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            optuna_file = os.path.join(output_dir, f"optuna_results_{timestamp}.json")
            
            with open(optuna_file, 'w') as f:
                json.dump(optuna_results, f, indent=2)
            
            logger.info(f"Optuna optimization results saved to {optuna_file}")
            
            # Train final model with best parameters
            logger.info("Training final model with best parameters")
            model = LGBMRegressor(**best_params)
            
            # Train on combined train + validation set for final model
            X_train_full = pd.concat([X_train, X_val])
            y_train_full = pd.concat([y_train, y_val])
            
            # Fix: verbose parameter depends on LightGBM version
            try:
                model.fit(X_train_full, y_train_full, verbose=False)
            except TypeError:
                # Try without verbose for compatibility with different LightGBM versions
                model.fit(X_train_full, y_train_full)
        
        # Feature importance calculation
        feature_importance = None
        if hasattr(model, 'feature_importances_'):
            feature_names = X_train.columns.tolist()
            feature_importance = dict(zip(feature_names, model.feature_importances_.tolist()))
        
        # Save model
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_file = os.path.join(output_dir, f"lightgbm_model_{timestamp}.pkl")
        with open(model_file, 'wb') as f:
            pickle.dump({
                'model': model, 
                'params': best_params,
                'validation_score': best_score,
                'optimization_history': optimization_history,
                'subset_name': subset_name,
                'num_features': num_features,
                'feature_importance': feature_importance
            }, f)
        
        logger.info(f"Model trained and saved to {model_file}")
        return model_file
    except Exception as e:
        logger.error(f"Error in model training: {str(e)}")
        raise

def evaluate_model(model_file, data, output_dir):
    """Evaluate the trained model"""
    try:
        # Import here to avoid dependency if evaluation is skipped
        import pickle
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, explained_variance_score
        import json
        import numpy as np
        
        logger.info("Evaluating model")
        
        # Create directory for results
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract data
        X_test = data['X_test']
        y_test = data['y_test']
        
        # Load model
        with open(model_file, 'rb') as f:
            model_data = pickle.load(f)
        model = model_data['model']
        params = model_data.get('params', {})
        validation_score = model_data.get('validation_score', None)
        
        # Make predictions
        y_pred = model.predict(X_test)
        
        # Calculate metrics
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_pred)
        explained_variance = explained_variance_score(y_test, y_pred)
        
        # Calculate residuals
        residuals = y_test - y_pred
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {
            'metrics': {
                'mae': mae,
                'mse': mse,
                'rmse': rmse,
                'r2': r2,
                'explained_variance': explained_variance
            },
            'validation_score': validation_score,
            'hyperparameters': params,
            'y_test': y_test.tolist(),
            'y_pred': y_pred.tolist(),
            'residuals': residuals.tolist()
        }
        
        # Add feature importance
        feature_importance = None
        if hasattr(model, 'feature_importances_'):
            feature_names = data['X'].columns.tolist()
            feature_importance = dict(zip(feature_names, model.feature_importances_.tolist()))
            results['feature_importance'] = feature_importance
        
        # Save model evaluation results
        results_file = os.path.join(output_dir, f"model_results_{timestamp}.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Model evaluation results:")
        logger.info(f"  MAE: {mae:.4f}")
        logger.info(f"  RMSE: {rmse:.4f}")
        logger.info(f"  R²: {r2:.4f}")
        logger.info(f"  Explained Variance: {explained_variance:.4f}")
        if validation_score is not None:
            logger.info(f"  Validation RMSE: {validation_score:.4f}")
        logger.info(f"Results saved to {results_file}")
        
        return results_file
    except Exception as e:
        logger.error(f"Error in model evaluation: {str(e)}")
        raise

def generate_visualizations(data, model_file, results_file, output_dir, random_seed):
    """Generate visualizations from the model and results"""
    try:
        # Import here to avoid dependency if visualization is skipped
        import matplotlib.pyplot as plt
        import seaborn as sns
        import pickle
        import json
        import shap
        
        logger.info("Generating visualizations")
        
        # Create directory for figures
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract data
        X = data['X']
        Y = data['Y']
        X_test = data['X_test']
        
        # Load model
        with open(model_file, 'rb') as f:
            model_data = pickle.load(f)
        model = model_data['model']
        optimization_history = model_data.get('optimization_history', [])
        
        # Load results
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        # 1. Plot feature importance
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        top_n = 20
        top_features = feature_importance.head(top_n)
        
        plt.figure(figsize=(12, 8))
        sns.barplot(x='importance', y='feature', data=top_features)
        plt.title(f'Top {top_n} Feature Importance')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'feature_importance.png'), dpi=300)
        plt.close()
        
        # 2. Plot scatter of predicted vs actual
        y_test = results['y_test']
        y_pred = results['y_pred']
        df = pd.DataFrame({'True': y_test, 'Predicted': y_pred})
        
        plt.figure(figsize=(10, 8))
        sns.scatterplot(x='True', y='Predicted', data=df, alpha=0.6)
        
        min_val = min(min(y_test), min(y_pred))
        max_val = max(max(y_test), max(y_pred))
        plt.plot([min_val, max_val], [min_val, max_val], 'r--')
        
        r2 = results['metrics']['r2']
        plt.text(0.05, 0.95, f'R² = {r2:.4f}', transform=plt.gca().transAxes,
                fontsize=12, verticalalignment='top')
        
        plt.title('Predicted vs True Values')
        plt.xlabel('True Values')
        plt.ylabel('Predicted Values')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'prediction_scatter.png'), dpi=300)
        plt.close()
        
        # 3. Plot residuals
        if 'residuals' in results:
            residuals = results['residuals']
            plt.figure(figsize=(10, 6))
            sns.histplot(residuals, kde=True)
            plt.axvline(x=0, color='r', linestyle='--')
            plt.title('Residuals Distribution')
            plt.xlabel('Residual (True - Predicted)')
            plt.ylabel('Frequency')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'residuals_distribution.png'), dpi=300)
            plt.close()
            
            # Residuals vs Predicted
            plt.figure(figsize=(10, 6))
            sns.scatterplot(x=y_pred, y=residuals, alpha=0.6)
            plt.axhline(y=0, color='r', linestyle='--')
            plt.title('Residuals vs Predicted Values')
            plt.xlabel('Predicted Values')
            plt.ylabel('Residuals')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'residuals_vs_predicted.png'), dpi=300)
            plt.close()
        
        # 4. Optimization history plots (if available)
        if optimization_history:
            # Convert history to DataFrame
            optuna_df = pd.DataFrame([
                {
                    'trial': trial['trial'],
                    'value': trial['value'],
                    **trial['params']
                }
                for trial in optimization_history
                if trial['state'] == 'COMPLETE'
            ])
            
            if not optuna_df.empty:
                # Plot optimization history
                plt.figure(figsize=(10, 6))
                plt.plot(optuna_df['trial'], optuna_df['value'], '-o')
                plt.title('Hyperparameter Optimization History')
                plt.xlabel('Trial')
                plt.ylabel('RMSE')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, 'optimization_history.png'), dpi=300)
                plt.close()
                
                # Parameter importance - scatter plots for most important parameters
                params_to_plot = ['learning_rate', 'n_estimators', 'max_depth', 'num_leaves']
                
                for param in params_to_plot:
                    if param in optuna_df.columns:
                        plt.figure(figsize=(8, 6))
                        sns.scatterplot(x=param, y='value', data=optuna_df)
                        plt.title(f'RMSE vs {param}')
                        plt.xlabel(param)
                        plt.ylabel('RMSE')
                        plt.grid(True, alpha=0.3)
                        plt.tight_layout()
                        plt.savefig(os.path.join(output_dir, f'param_importance_{param}.png'), dpi=300)
                        plt.close()
        
        # 5. SHAP values for model explanation
        try:
            # Calculate SHAP values (sample for faster calculation)
            sample_size = min(100, X.shape[0])
            X_sample = X.sample(sample_size, random_state=random_seed)
            explainer = shap.Explainer(model)
            shap_values = explainer(X_sample)
            
            # SHAP summary plot
            plt.figure(figsize=(12, 8))
            shap.summary_plot(shap_values, X_sample, show=False)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'shap_summary.png'), dpi=300, bbox_inches='tight')
            plt.close()
            
            # SHAP bar plot
            plt.figure(figsize=(12, 8))
            shap.summary_plot(shap_values, X_sample, plot_type='bar', show=False)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'shap_bar.png'), dpi=300, bbox_inches='tight')
            plt.close()
            
            # Detailed SHAP plots for top features
            top_5_features = feature_importance.head(5)['feature'].values
            for feature in top_5_features:
                if feature in X_sample.columns:
                    plt.figure(figsize=(10, 6))
                    shap.plots.scatter(shap_values[:, feature], show=False)
                    plt.tight_layout()
                    plt.savefig(os.path.join(output_dir, f'shap_scatter_{feature}.png'), dpi=300, bbox_inches='tight')
                    plt.close()
        except Exception as shap_error:
            logger.warning(f"Error generating SHAP plots: {str(shap_error)}")
        
        logger.info(f"Visualizations saved to {output_dir}")
    except Exception as e:
        logger.error(f"Error in visualization generation: {str(e)}")
        raise

def prepare_subset_data(data, X_subset, subset_name, random_seed):
    """Prepare data dictionary for a specific feature subset"""
    logger.info(f"Preparing data for feature subset: {subset_name} with {X_subset.shape[1]} features")
    
    # Get the original target variable
    Y = data['Y']
    
    # Split into train, validation, and test sets
    X_train_val, X_test, y_train_val, y_test = train_test_split(X_subset, Y, test_size=0.2, random_state=random_seed)
    X_train, X_val, y_train, y_val = train_test_split(X_train_val, y_train_val, test_size=0.25, random_state=random_seed)
    
    # Create a new data dictionary for this subset
    subset_data = {
        'X': X_subset,
        'Y': Y,
        'X_train': X_train,
        'X_val': X_val,
        'X_test': X_test,
        'y_train': y_train,
        'y_val': y_val,
        'y_test': y_test,
        'subset_name': subset_name
    }
    
    logger.info(f"Subset {subset_name}: Training set size: {X_train.shape}, Validation set size: {X_val.shape}, Test set size: {X_test.shape}")
    
    return subset_data

def compare_feature_subsets(results_files, output_file):
    """Compare results across different feature subsets"""
    try:
        import json
        import pandas as pd
        
        logger.info("Comparing performance across feature subsets")
        
        # Load results for each subset
        comparison_data = {}
        metrics_summary = []
        
        for subset_name, results_file in results_files.items():
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            # Store metrics for this subset
            metrics = results['metrics']
            metrics['subset'] = subset_name
            metrics['num_features'] = len(results.get('feature_importance', {}))
            metrics['validation_score'] = results.get('validation_score')
            metrics_summary.append(metrics)
            
            # Store detailed results
            comparison_data[subset_name] = {
                'metrics': metrics,
                'hyperparameters': results.get('hyperparameters', {}),
                'num_features': len(results.get('feature_importance', {}))
            }
        
        # Convert metrics to DataFrame for easier comparison
        metrics_df = pd.DataFrame(metrics_summary)
        
        # Rank subsets by performance (lower RMSE is better)
        ranked_subsets = metrics_df.sort_values('rmse').reset_index(drop=True)
        
        # Format for output
        comparison_results = {
            'ranked_subsets': ranked_subsets.to_dict(orient='records'),
            'detailed_comparison': comparison_data,
            'best_subset': ranked_subsets.iloc[0]['subset'],
            'best_rmse': ranked_subsets.iloc[0]['rmse'],
            'best_r2': ranked_subsets.iloc[0]['r2']
        }
        
        # Save comparison results
        with open(output_file, 'w') as f:
            json.dump(comparison_results, f, indent=2)
        
        logger.info(f"Comparison results saved to {output_file}")
        logger.info(f"Best performing subset: {comparison_results['best_subset']} with RMSE: {comparison_results['best_rmse']:.4f}")
        
        # Display ranking
        for i, row in ranked_subsets.iterrows():
            logger.info(f"Rank {i+1}: {row['subset']} - RMSE: {row['rmse']:.4f}, R²: {row['r2']:.4f}")
        
        return output_file
    except Exception as e:
        logger.error(f"Error in feature subset comparison: {str(e)}")
        raise

def generate_comparison_visualizations(comparison_file, output_dir):
    """Generate visualizations comparing feature subset performance"""
    try:
        import json
        import matplotlib.pyplot as plt
        import seaborn as sns
        import pandas as pd
        
        logger.info("Generating comparison visualizations across feature subsets")
        
        # Load comparison data
        with open(comparison_file, 'r') as f:
            comparison_data = json.load(f)
        
        # Convert to DataFrame
        metrics_df = pd.DataFrame(comparison_data['ranked_subsets'])
        
        # Create comparison directory
        comparison_dir = os.path.join(output_dir, 'comparison')
        os.makedirs(comparison_dir, exist_ok=True)
        
        # 1. RMSE comparison bar chart
        plt.figure(figsize=(12, 6))
        sns.barplot(x='subset', y='rmse', data=metrics_df)
        plt.title('RMSE Comparison Across Feature Subsets')
        plt.xlabel('Feature Subset')
        plt.ylabel('RMSE (lower is better)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(comparison_dir, 'rmse_comparison.png'), dpi=300)
        plt.close()
        
        # 2. R² comparison bar chart
        plt.figure(figsize=(12, 6))
        sns.barplot(x='subset', y='r2', data=metrics_df)
        plt.title('R² Comparison Across Feature Subsets')
        plt.xlabel('Feature Subset')
        plt.ylabel('R² (higher is better)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(comparison_dir, 'r2_comparison.png'), dpi=300)
        plt.close()
        
        # 3. Metrics heatmap
        plt.figure(figsize=(12, 8))
        metrics_for_heatmap = metrics_df[['subset', 'mae', 'rmse', 'r2', 'explained_variance']]
        metrics_pivot = metrics_for_heatmap.set_index('subset')
        sns.heatmap(metrics_pivot, annot=True, cmap='YlGnBu', fmt='.4f')
        plt.title('Performance Metrics Across Feature Subsets')
        plt.tight_layout()
        plt.savefig(os.path.join(comparison_dir, 'metrics_heatmap.png'), dpi=300)
        plt.close()
        
        # 4. Feature count vs performance
        plt.figure(figsize=(10, 6))
        sns.scatterplot(x='num_features', y='rmse', data=metrics_df, s=100)
        
        # Add subset names as labels
        for i, row in metrics_df.iterrows():
            plt.text(row['num_features'], row['rmse'], row['subset'], 
                     fontsize=9, ha='right', va='bottom')
            
        plt.title('Number of Features vs RMSE')
        plt.xlabel('Number of Features')
        plt.ylabel('RMSE')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(comparison_dir, 'features_vs_rmse.png'), dpi=300)
        plt.close()
        
        logger.info(f"Comparison visualizations saved to {comparison_dir}")
    except Exception as e:
        logger.error(f"Error generating comparison visualizations: {str(e)}")
        raise

def bootstrap_comparison(results_files, output_dir, n_iterations=1000):
    """
    Perform bootstrap analysis to compare feature subsets
    
    Args:
        results_files: Dictionary with subset names as keys and paths to result files as values
        output_dir: Directory to save the bootstrap results
        n_iterations: Number of bootstrap iterations
    
    Returns:
        Path to the bootstrap results file
    """
    try:
        import json
        import pandas as pd
        import numpy as np
        import matplotlib.pyplot as plt
        import seaborn as sns
        from sklearn.metrics import mean_squared_error, r2_score
        
        logger.info(f"Performing bootstrap analysis with {n_iterations} iterations")
        
        # Create the output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Load results for each subset
        subset_data = {}
        for subset_name, results_file in results_files.items():
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            # Store true and predicted values
            subset_data[subset_name] = {
                'y_true': results['y_test'],
                'y_pred': results['y_pred']
            }
        
        # Set up bootstrap analysis
        subset_names = list(subset_data.keys())
        n_subsets = len(subset_names)
        
        # Prepare for bootstrap results
        bootstrap_rmse = {name: [] for name in subset_names}
        bootstrap_r2 = {name: [] for name in subset_names}
        
        # Pairwise comparison p-values
        pairwise_rmse_p_values = np.zeros((n_subsets, n_subsets))
        pairwise_r2_p_values = np.zeros((n_subsets, n_subsets))
        
        # Run bootstrap iterations
        logger.info("Starting bootstrap iterations...")
        for i in range(n_iterations):
            if i % 100 == 0:
                logger.info(f"Bootstrap iteration {i}/{n_iterations}")
            
            # For each subset, create a bootstrap sample and calculate metrics
            bootstrap_metrics = {}
            for name in subset_names:
                y_true = subset_data[name]['y_true']
                y_pred = subset_data[name]['y_pred']
                
                # Create bootstrap sample
                n_samples = len(y_true)
                indices = np.random.choice(n_samples, n_samples, replace=True)
                
                y_true_bootstrap = [y_true[i] for i in indices]
                y_pred_bootstrap = [y_pred[i] for i in indices]
                
                # Calculate metrics
                rmse = np.sqrt(mean_squared_error(y_true_bootstrap, y_pred_bootstrap))
                r2 = r2_score(y_true_bootstrap, y_pred_bootstrap)
                
                bootstrap_rmse[name].append(rmse)
                bootstrap_r2[name].append(r2)
                
                bootstrap_metrics[name] = {'rmse': rmse, 'r2': r2}
            
            # Calculate pairwise differences for this bootstrap iteration
            for i, name1 in enumerate(subset_names):
                for j, name2 in enumerate(subset_names):
                    if i < j:  # Only calculate for unique pairs
                        # For RMSE, lower is better
                        if bootstrap_metrics[name1]['rmse'] < bootstrap_metrics[name2]['rmse']:
                            pairwise_rmse_p_values[i, j] += 1
                        # For R², higher is better
                        if bootstrap_metrics[name1]['r2'] > bootstrap_metrics[name2]['r2']:
                            pairwise_r2_p_values[i, j] += 1
        
        # Normalize p-values
        pairwise_rmse_p_values /= n_iterations
        pairwise_r2_p_values /= n_iterations
        
        # Calculate 95% confidence intervals
        bootstrap_stats = {}
        for name in subset_names:
            rmse_mean = np.mean(bootstrap_rmse[name])
            rmse_std = np.std(bootstrap_rmse[name])
            rmse_ci_lower = np.percentile(bootstrap_rmse[name], 2.5)
            rmse_ci_upper = np.percentile(bootstrap_rmse[name], 97.5)
            
            r2_mean = np.mean(bootstrap_r2[name])
            r2_std = np.std(bootstrap_r2[name])
            r2_ci_lower = np.percentile(bootstrap_r2[name], 2.5)
            r2_ci_upper = np.percentile(bootstrap_r2[name], 97.5)
            
            bootstrap_stats[name] = {
                'rmse_mean': rmse_mean,
                'rmse_std': rmse_std,
                'rmse_ci': [rmse_ci_lower, rmse_ci_upper],
                'r2_mean': r2_mean,
                'r2_std': r2_std,
                'r2_ci': [r2_ci_lower, r2_ci_upper]
            }
        
        # Create a dataframe for visualization
        stats_df = []
        for name in subset_names:
            stats_df.append({
                'subset': name,
                'rmse_mean': bootstrap_stats[name]['rmse_mean'],
                'rmse_std': bootstrap_stats[name]['rmse_std'],
                'rmse_ci_lower': bootstrap_stats[name]['rmse_ci'][0],
                'rmse_ci_upper': bootstrap_stats[name]['rmse_ci'][1],
                'r2_mean': bootstrap_stats[name]['r2_mean'],
                'r2_std': bootstrap_stats[name]['r2_std'],
                'r2_ci_lower': bootstrap_stats[name]['r2_ci'][0],
                'r2_ci_upper': bootstrap_stats[name]['r2_ci'][1]
            })
        stats_df = pd.DataFrame(stats_df)
        
        # Create pairwise p-value dataframes
        rmse_p_df = pd.DataFrame(data=pairwise_rmse_p_values, index=subset_names, columns=subset_names)
        r2_p_df = pd.DataFrame(data=pairwise_r2_p_values, index=subset_names, columns=subset_names)
        
        # Save bootstrap results
        bootstrap_results = {
            'bootstrap_stats': bootstrap_stats,
            'pairwise_rmse_p_values': rmse_p_df.to_dict(),
            'pairwise_r2_p_values': r2_p_df.to_dict(),
            'n_iterations': n_iterations
        }
        
        results_file = os.path.join(output_dir, f"bootstrap_results.json")
        with open(results_file, 'w') as f:
            json.dump(bootstrap_results, f, indent=2)
        
        # Generate visualizations
        # 1. RMSE comparison with confidence intervals
        plt.figure(figsize=(12, 8))
        stats_df_sorted = stats_df.sort_values('rmse_mean')
        
        # Create a bar plot with error bars
        ax = sns.barplot(x='subset', y='rmse_mean', data=stats_df_sorted, capsize=0.2)
        
        # Add error bars for confidence intervals
        for i, row in stats_df_sorted.iterrows():
            ax.errorbar(
                i, row['rmse_mean'],
                yerr=[[row['rmse_mean'] - row['rmse_ci_lower']], [row['rmse_ci_upper'] - row['rmse_mean']]],
                fmt='none', color='black', capsize=5
            )
        
        plt.title('RMSE with 95% Confidence Intervals')
        plt.xlabel('Feature Subset')
        plt.ylabel('RMSE (lower is better)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'bootstrap_rmse_ci.png'), dpi=300)
        plt.close()
        
        # 2. R² comparison with confidence intervals
        plt.figure(figsize=(12, 8))
        stats_df_sorted = stats_df.sort_values('r2_mean', ascending=False)
        
        # Create a bar plot with error bars
        ax = sns.barplot(x='subset', y='r2_mean', data=stats_df_sorted, capsize=0.2)
        
        # Add error bars for confidence intervals
        for i, row in stats_df_sorted.iterrows():
            ax.errorbar(
                i, row['r2_mean'],
                yerr=[[row['r2_mean'] - row['r2_ci_lower']], [row['r2_ci_upper'] - row['r2_mean']]],
                fmt='none', color='black', capsize=5
            )
        
        plt.title('R² with 95% Confidence Intervals')
        plt.xlabel('Feature Subset')
        plt.ylabel('R² (higher is better)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'bootstrap_r2_ci.png'), dpi=300)
        plt.close()
        
        # 3. Heatmap of pairwise RMSE p-values
        plt.figure(figsize=(10, 8))
        sns.heatmap(rmse_p_df, annot=True, cmap='YlGnBu', fmt='.3f', vmin=0, vmax=1)
        plt.title('Pairwise RMSE Comparison (p-values)')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'bootstrap_rmse_pairwise.png'), dpi=300)
        plt.close()
        
        # 4. Heatmap of pairwise R² p-values
        plt.figure(figsize=(10, 8))
        sns.heatmap(r2_p_df, annot=True, cmap='YlGnBu', fmt='.3f', vmin=0, vmax=1)
        plt.title('Pairwise R² Comparison (p-values)')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'bootstrap_r2_pairwise.png'), dpi=300)
        plt.close()
        
        # 5. Distribution plots of RMSE for each subset
        plt.figure(figsize=(15, 10))
        for name in subset_names:
            sns.kdeplot(bootstrap_rmse[name], label=name)
        plt.title('RMSE Distribution Across Bootstrap Samples')
        plt.xlabel('RMSE')
        plt.ylabel('Density')
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'bootstrap_rmse_distribution.png'), dpi=300)
        plt.close()
        
        # Log results
        logger.info("Bootstrap analysis completed")
        logger.info(f"Results saved to {results_file}")
        
        # Print key findings
        logger.info("\nKey bootstrap findings:")
        for i, row in stats_df.sort_values('rmse_mean').iterrows():
            logger.info(f"{row['subset']}: RMSE = {row['rmse_mean']:.4f} ({row['rmse_ci_lower']:.4f}-{row['rmse_ci_upper']:.4f}), R² = {row['r2_mean']:.4f} ({row['r2_ci_lower']:.4f}-{row['r2_ci_upper']:.4f})")
        
        return results_file
            
    except Exception as e:
        logger.error(f"Error in bootstrap analysis: {str(e)}")
        raise

def compare_with_ddmut(best_model_file, results_dir):
    """
    Compare our model predictions with DDMut predictions
    
    Args:
        best_model_file: Path to the best model file
        results_dir: Directory to save the comparison results
    
    Returns:
        Path to the comparison results file
    """
    try:
        import pandas as pd
        import numpy as np
        import matplotlib.pyplot as plt
        import seaborn as sns
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
        import pickle
        import json
        
        logger.info("Comparing model predictions with DDMut predictions")
        
        # Load DDMut data
        ddmut_file = os.path.join('data', 'DDMut.csv')
        if not os.path.exists(ddmut_file):
            ddmut_file = os.path.join('data', 'DDMut.xlsx')
        
        if os.path.exists(ddmut_file):
            # Load the DDMut data
            if ddmut_file.endswith('.csv'):
                ddmut_df = pd.read_csv(ddmut_file)
            else:
                ddmut_df = pd.read_excel(ddmut_file)
                
            logger.info(f"Loaded DDMut data with {len(ddmut_df)} entries")
            
            # Load our best model predictions
            with open(best_model_file, 'rb') as f:
                model_data = pickle.load(f)
                
            # Get predictions
            with open(os.path.join(results_dir, os.path.basename(best_model_file).replace('.pkl', '.json')), 'r') as f:
                results = json.load(f)
                
            # Prepare comparison dataframe
            delta_30 = ddmut_df['delta_30'] if 'delta_30' in ddmut_df.columns else ddmut_df['delta heat 30']
            ddmut_prediction = ddmut_df['ddmut_prediction']
            
            # Calculate DDMut metrics
            ddmut_r2 = r2_score(delta_30, ddmut_prediction)
            ddmut_rmse = np.sqrt(mean_squared_error(delta_30, ddmut_prediction))
            ddmut_mae = mean_absolute_error(delta_30, ddmut_prediction)
            
            # Get our model metrics
            our_r2 = results['metrics']['r2']
            our_rmse = results['metrics']['rmse']
            our_mae = results['metrics']['mae']
            
            # Create comparison table
            comparison = {
                'Model': ['DDMut', 'Our Model'],
                'R²': [ddmut_r2, our_r2],
                'RMSE': [ddmut_rmse, our_rmse],
                'MAE': [ddmut_mae, our_mae]
            }
            comparison_df = pd.DataFrame(comparison)
            
            # Calculate absolute error stats for DDMut
            absolute_error_ddmut = np.abs(delta_30 - ddmut_prediction)
            absolute_error_std_ddmut = np.std(absolute_error_ddmut)
            standard_error_std_ddmut = absolute_error_std_ddmut / np.sqrt(len(delta_30))
            
            # Save comparison results
            comparison_file = os.path.join(results_dir, "ddmut_comparison.json")
            with open(comparison_file, 'w') as f:
                json.dump({
                    'ddmut': {
                        'r2': ddmut_r2,
                        'rmse': ddmut_rmse,
                        'mae': ddmut_mae,
                        'absolute_error_std': float(absolute_error_std_ddmut),
                        'standard_error': float(standard_error_std_ddmut)
                    },
                    'our_model': {
                        'r2': our_r2,
                        'rmse': our_rmse,
                        'mae': our_mae
                    }
                }, f, indent=2)
            
            # Create visualizations
            
            # 1. Bar chart comparing metrics
            plt.figure(figsize=(10, 6))
            sns.barplot(x='Model', y='R²', data=comparison_df)
            plt.title('R² Comparison: DDMut vs Our Model')
            plt.savefig(os.path.join(results_dir, 'ddmut_r2_comparison.png'), dpi=300)
            plt.close()
            
            plt.figure(figsize=(10, 6))
            sns.barplot(x='Model', y='RMSE', data=comparison_df)
            plt.title('RMSE Comparison: DDMut vs Our Model')
            plt.savefig(os.path.join(results_dir, 'ddmut_rmse_comparison.png'), dpi=300)
            plt.close()
            
            # 2. Scatter plots
            plt.figure(figsize=(12, 10))
            
            # DDMut scatter plot
            plt.subplot(2, 1, 1)
            plt.scatter(delta_30, ddmut_prediction, alpha=0.6)
            plt.plot([-5, 5], [-5, 5], 'r--')  # Perfect prediction line
            plt.title('DDMut Predictions vs True Values')
            plt.xlabel('True Values (delta_30)')
            plt.ylabel('DDMut Predictions')
            plt.text(0.05, 0.95, f'R² = {ddmut_r2:.4f}', transform=plt.gca().transAxes,
                    fontsize=12, verticalalignment='top')
            
            # Our model scatter plot
            plt.subplot(2, 1, 2)
            y_true = results['y_test']
            y_pred = results['y_pred']
            plt.scatter(y_true, y_pred, alpha=0.6)
            plt.plot([-5, 5], [-5, 5], 'r--')  # Perfect prediction line
            plt.title('Our Model Predictions vs True Values')
            plt.xlabel('True Values')
            plt.ylabel('Model Predictions')
            plt.text(0.05, 0.95, f'R² = {our_r2:.4f}', transform=plt.gca().transAxes,
                    fontsize=12, verticalalignment='top')
            
            plt.tight_layout()
            plt.savefig(os.path.join(results_dir, 'ddmut_scatter_comparison.png'), dpi=300)
            plt.close()
            
            logger.info("DDMut comparison completed")
            logger.info(f"DDMut - R²: {ddmut_r2:.4f}, RMSE: {ddmut_rmse:.4f}, MAE: {ddmut_mae:.4f}")
            logger.info(f"Our Model - R²: {our_r2:.4f}, RMSE: {our_rmse:.4f}, MAE: {our_mae:.4f}")
            
            return comparison_file
        else:
            logger.warning(f"DDMut data file not found at {ddmut_file}")
            return None
            
    except Exception as e:
        logger.error(f"Error in DDMut comparison: {str(e)}")
        raise

def analyze_mutation_counts(data_dir, output_dir):
    """
    Analyze mutation counts in the PDB files, similar to number_of_mutations.ipynb
    
    Args:
        data_dir: Directory containing the PDB files
        output_dir: Directory to save the analysis results
    
    Returns:
        Path to the mutation counts file
    """
    try:
        import pandas as pd
        import numpy as np
        import matplotlib.pyplot as plt
        import seaborn as sns
        from Bio import PDB
        import os
        import glob
        
        logger.info("Analyzing mutation counts from PDB files")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Function to compare sequences and count mutations
        def compare_sequences(pdb_file, wild_type_pdb_file):
            parser = PDB.PDBParser(QUIET=True)
            
            # Parse the current structure
            structure = parser.get_structure("structure", pdb_file)
            
            # Parse the wild-type structure
            wild_type_structure = parser.get_structure("wild_type_structure", wild_type_pdb_file)
            
            # Get the chains from the structures
            chains = structure[0]
            wild_type_chains = wild_type_structure[0]
            
            # Initialize the mutation count
            mutation_count = 0
            mutations = []
            
            # Compare the residues in each chain with the wild-type structure
            for chain, wild_type_chain in zip(chains, wild_type_chains):
                for residue, wild_type_residue in zip(chain, wild_type_chain):
                    # Skip non-standard residues
                    if residue.get_resname() not in PDB.Polypeptide.standard_aa_names or \
                       wild_type_residue.get_resname() not in PDB.Polypeptide.standard_aa_names:
                        continue
                    
                    # Get one-letter code
                    residue_name = PDB.Polypeptide.three_to_one(residue.get_resname())
                    wild_type_residue_name = PDB.Polypeptide.three_to_one(wild_type_residue.get_resname())
                    
                    residue_id = residue.get_id()[1]
                    
                    if residue_name != wild_type_residue_name:
                        mutation = f"{wild_type_residue_name}{residue_id}{residue_name}"
                        mutations.append(mutation)
                        mutation_count += 1
            
            return mutation_count, mutations
        
        # Look for PDB files
        pdb_dirs = [
            os.path.join(data_dir, 'PDBs'),  # Check for a PDBs subdirectory
            data_dir  # Otherwise use the data directory itself
        ]
        
        wild_type_pdb_file = os.path.join(data_dir, "wt.pdb")
        if not os.path.exists(wild_type_pdb_file):
            wild_type_pdb_file = os.path.join(data_dir, "wild_type.pdb")
        
        if not os.path.exists(wild_type_pdb_file):
            logger.warning("Wild-type PDB file not found. Cannot analyze mutations.")
            return None
        
        # Find PDB files
        pdb_files = []
        for pdb_dir in pdb_dirs:
            if os.path.exists(pdb_dir):
                for root, dirs, files in os.walk(pdb_dir):
                    for file in files:
                        if file.endswith('.pdb'):
                            pdb_files.append(os.path.join(root, file))
        
        if not pdb_files:
            # Try to find any PDB files in the data dir
            for file in os.listdir(data_dir):
                if file.endswith('.pdb') and file != "wt.pdb" and file != "wild_type.pdb":
                    pdb_files.append(os.path.join(data_dir, file))
        
        if not pdb_files:
            logger.warning("No PDB files found to analyze mutations.")
            return None
        
        logger.info(f"Found {len(pdb_files)} PDB files to analyze")
        
        # Analyze mutations in PDB files
        mutations = {}
        for pdb_file in pdb_files:
            folder_name = os.path.basename(os.path.dirname(pdb_file))
            file_name = os.path.basename(pdb_file)
            key = f"{folder_name}_{file_name}"
            
            try:
                mutation_count, mutation_list = compare_sequences(pdb_file, wild_type_pdb_file)
                mutations[key] = {
                    'count': mutation_count,
                    'mutations': mutation_list
                }
                logger.debug(f"Analyzed {key}: {mutation_count} mutations")
            except Exception as e:
                logger.warning(f"Error analyzing {key}: {str(e)}")
        
        # Create a DataFrame from the mutations dictionary
        mutation_data = []
        for key, value in mutations.items():
            mutation_data.append({
                'file': key,
                'mutation_count': value['count'],
                'mutations': ','.join(value['mutations'])
            })
        
        df = pd.DataFrame(mutation_data)
        
        # Save results
        results_file = os.path.join(output_dir, "mutation_counts.csv")
        df.to_csv(results_file, index=False)
        
        # Generate visualizations
        
        # 1. Distribution of mutation counts
        plt.figure(figsize=(12, 8))
        sns.histplot(df['mutation_count'], kde=False, bins=20)
        plt.title('Distribution of Mutation Counts')
        plt.xlabel('Number of Mutations')
        plt.ylabel('Frequency')
        plt.savefig(os.path.join(output_dir, 'mutation_count_distribution.png'), dpi=300)
        plt.close()
        
        # 2. Calculate statistics
        mutation_stats = {
            'min': df['mutation_count'].min(),
            'max': df['mutation_count'].max(),
            'mean': df['mutation_count'].mean(),
            'median': df['mutation_count'].median(),
            'std': df['mutation_count'].std(),
            'count': len(df),
            'percent_above_5': (df['mutation_count'] >= 5).mean() * 100
        }
        
        # Save statistics
        stats_file = os.path.join(output_dir, "mutation_statistics.json")
        with open(stats_file, 'w') as f:
            import json
            json.dump(mutation_stats, f, indent=2)
        
        logger.info("Mutation analysis completed")
        logger.info(f"Results saved to {results_file}")
        logger.info(f"Analyzed {len(df)} PDB files")
        logger.info(f"Mutation counts - Min: {mutation_stats['min']}, Max: {mutation_stats['max']}, Mean: {mutation_stats['mean']:.2f}")
        logger.info(f"Percentage of mutations >= 5: {mutation_stats['percent_above_5']:.2f}%")
        
        return results_file
            
    except Exception as e:
        logger.error(f"Error in mutation count analysis: {str(e)}")
        return None

def main(args):
    """Main pipeline function that skips MDS calculation"""
    # Load config
    config = load_config(args.config)
    
    # Set random seed for reproducibility
    np.random.seed(args.random_seed)
    
    # Set up directories
    output_dir = args.output_dir
    data_dir = args.data_dir
    models_dir = os.path.join(output_dir, 'models')
    results_dir = os.path.join(output_dir, 'results')
    figures_dir = os.path.join(output_dir, 'figures')
    analysis_dir = os.path.join(output_dir, 'analysis')
    
    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)
    os.makedirs(analysis_dir, exist_ok=True)
    
    logger.info("Starting pipeline without MDS calculation for new_df_66")
    
    try:
        # Step 1: Load and preprocess data (skipping MDS)
        logger.info("Step 1: Loading and preprocessing data (skipping MDS)")
        data = load_and_preprocess_data(data_dir, args.random_seed)
        
        # Step 1.5: Run LazyPredict to evaluate multiple models
        logger.info("Step 1.5: Running LazyPredict to evaluate multiple regression models")
        feature_subsets = {
            'All_Features': data['X'],
            'MDpocket': data['feature_sets']['MDpocket'],
            'MD': data['feature_sets']['MD'],
            'Seq': data['feature_sets']['Seq'],
            'Seq_MD': data['feature_sets']['Seq_MD'],
            'MD_MDpocket': data['feature_sets']['MD_MDpocket'],
            'Seq_MDpocket': data['feature_sets']['Seq_MDpocket']
        }
        
        lazypredict_results = {}
        for subset_name, X in feature_subsets.items():
            logger.info(f"Running LazyPredict for feature subset: {subset_name}")
            subset_data = prepare_subset_data(data, X, subset_name, args.random_seed)
            lazy_result = run_lazypredict(subset_data, output_dir, args.random_seed)
            if lazy_result:
                lazypredict_results[subset_name] = lazy_result
        
        # Step 2: Train models for each feature subset
        logger.info("Step 2: Training models for each feature subset with hyperparameter optimization")
        model_params = config.get('model', {}).get('lightgbm', {}) if hasattr(config, 'get') else None
        
        # Store model files and results for each subset
        model_files = {}
        results_files = {}
        
        # Train a model for each feature subset
        for subset_name, X in feature_subsets.items():
            logger.info(f"Training model for feature subset: {subset_name}")
            
            # Create subset-specific directories
            subset_models_dir = os.path.join(models_dir, subset_name)
            subset_results_dir = os.path.join(results_dir, subset_name)
            subset_figures_dir = os.path.join(figures_dir, subset_name)
            
            os.makedirs(subset_models_dir, exist_ok=True)
            os.makedirs(subset_results_dir, exist_ok=True)
            os.makedirs(subset_figures_dir, exist_ok=True)
            
            # Create a subset-specific data dictionary for training
            subset_data = prepare_subset_data(data, X, subset_name, args.random_seed)
            
            # Train model for this subset
            model_file = train_model(
                subset_data,
                model_params,
                subset_models_dir,
                args.random_seed,
                optuna_trials=args.optuna_trials,
                skip_optuna=args.skip_optuna
            )
            model_files[subset_name] = model_file
            
            # Evaluate model for this subset
            logger.info(f"Evaluating model for feature subset: {subset_name}")
            results_file = evaluate_model(model_file, subset_data, subset_results_dir)
            results_files[subset_name] = results_file
            
            # Generate visualizations for this subset
            logger.info(f"Generating visualizations for feature subset: {subset_name}")
            generate_visualizations(subset_data, model_file, results_file, subset_figures_dir, args.random_seed)
        
        # Step 3: Compare results across feature subsets
        logger.info("Step 3: Comparing results across feature subsets")
        comparison_file = compare_feature_subsets(results_files, os.path.join(results_dir, "feature_subset_comparison.json"))
        
        # Step 4: Generate comparison visualizations
        logger.info("Step 4: Generating comparison visualizations")
        generate_comparison_visualizations(comparison_file, figures_dir)
        
        # Step 5: Perform bootstrap analysis for statistical significance
        if not args.skip_bootstrap:
            logger.info("Step 5: Performing bootstrap analysis for statistical significance")
            bootstrap_file = bootstrap_comparison(
                results_files, 
                os.path.join(analysis_dir, 'bootstrap'),
                n_iterations=args.bootstrap_iterations
            )
        
        # Step 6: Compare with DDMut if requested
        if args.compare_with_ddmut:
            logger.info("Step 6: Comparing with DDMut predictions")
            # Find the best model based on the comparison results
            with open(comparison_file, 'r') as f:
                import json
                comparison_data = json.load(f)
            
            best_subset = comparison_data['best_subset']
            best_model_file = model_files[best_subset]
            
            ddmut_comparison_file = compare_with_ddmut(
                best_model_file, 
                os.path.join(analysis_dir, 'ddmut_comparison')
            )
        
        # Step 7: Analyze mutation counts if PDB files are available
        logger.info("Step 7: Analyzing mutation counts from PDB files")
        mutation_file = analyze_mutation_counts(
            data_dir,
            os.path.join(analysis_dir, 'mutations')
        )
        
        logger.info("Pipeline completed successfully")
        
        # Final summary report
        logger.info("\n" + "="*50)
        logger.info("PIPELINE EXECUTION SUMMARY")
        logger.info("="*50)
        
        # Load the comparison results to get the best model
        with open(comparison_file, 'r') as f:
            import json
            comparison_data = json.load(f)
        
        best_subset = comparison_data['best_subset']
        best_rmse = comparison_data['best_rmse']
        best_r2 = comparison_data['best_r2']
        
        logger.info(f"Best performing feature subset: {best_subset}")
        logger.info(f"Best model metrics - RMSE: {best_rmse:.4f}, R²: {best_r2:.4f}")
        
        logger.info("\nFeature subset performance ranking:")
        for i, subset in enumerate(comparison_data['ranked_subsets']):
            logger.info(f"{i+1}. {subset['subset']} - RMSE: {subset['rmse']:.4f}, R²: {subset['r2']:.4f}")
        
        logger.info("\nOutput files:")
        logger.info(f"- Models directory: {models_dir}")
        logger.info(f"- Results directory: {results_dir}")
        logger.info(f"- Figures directory: {figures_dir}")
        logger.info(f"- Analysis directory: {analysis_dir}")
        
        logger.info("\nAnalysis reports:")
        if not args.skip_bootstrap:
            logger.info(f"- Bootstrap analysis: {os.path.join(analysis_dir, 'bootstrap/bootstrap_results.json')}")
        if args.compare_with_ddmut and ddmut_comparison_file:
            logger.info(f"- DDMut comparison: {ddmut_comparison_file}")
        if mutation_file:
            logger.info(f"- Mutation analysis: {mutation_file}")
            
        # Add lazypredict summary if available
        if lazypredict_results:
            logger.info("\nLazyPredict summary:")
            for subset_name, result in lazypredict_results.items():
                logger.info(f"- {subset_name}: Top models - {', '.join(result['top_models'])}")
            logger.info(f"- LazyPredict results directory: {os.path.join(output_dir, 'lazypredict')}")
        
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    args = parse_args()
    main(args) 