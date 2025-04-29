#!/usr/bin/env python3
"""
Model evaluation module for ProMut-MD.
This module handles the evaluation of trained models on test data.
"""

import os
import json
import pickle
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score, 
    explained_variance_score, max_error
)

logger = logging.getLogger(__name__)

def load_model(model_file):
    """Load a trained model from pickle file"""
    logger.info(f"Loading model from {model_file}")
    with open(model_file, 'rb') as f:
        model_data = pickle.load(f)
    
    # Extract model and metadata
    model = model_data['model']
    explanations = model_data.get('explanations', None)
    results = model_data.get('results', None)
    
    return model, explanations, results

def load_features(features_file):
    """Load features from CSV file"""
    logger.info(f"Loading features from {features_file}")
    df = pd.read_csv(features_file, index_col=0)
    return df

def get_test_data(df, params):
    """Get test data for evaluation"""
    logger.info("Preparing test data for evaluation")
    
    # Assume the target column is 'DELTA30' - adapt as needed
    target_column = params.get('target_column', 'DELTA30')
    
    # Split features and target
    X = df.drop(target_column, axis=1)
    y = df[target_column]
    
    # If test indices were saved during training, use those
    # Otherwise, create a new train-test split
    from sklearn.model_selection import train_test_split
    test_size = 1.0 - params.get('train_test_split', 0.8)
    random_seed = params.get('random_seed', 42)
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_seed
    )
    
    return X_test, y_test

def evaluate_predictions(y_true, y_pred):
    """Evaluate model predictions with multiple metrics"""
    logger.info("Calculating evaluation metrics")
    
    # Calculate main regression metrics
    metrics = {
        'mse': mean_squared_error(y_true, y_pred),
        'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
        'mae': mean_absolute_error(y_true, y_pred),
        'r2': r2_score(y_true, y_pred),
        'explained_variance': explained_variance_score(y_true, y_pred),
        'max_error': max_error(y_true, y_pred)
    }
    
    # Add correlation coefficient
    metrics['pearson_r'] = np.corrcoef(y_true, y_pred)[0, 1]
    
    # Calculate errors by percentile
    errors = np.abs(y_true - y_pred)
    percentiles = [25, 50, 75, 90, 95, 99]
    for p in percentiles:
        metrics[f'percentile_{p}'] = np.percentile(errors, p)
    
    # Log metrics
    logger.info("Model performance metrics:")
    logger.info(f"  MSE: {metrics['mse']:.4f}")
    logger.info(f"  RMSE: {metrics['rmse']:.4f}")
    logger.info(f"  MAE: {metrics['mae']:.4f}")
    logger.info(f"  R²: {metrics['r2']:.4f}")
    logger.info(f"  Pearson r: {metrics['pearson_r']:.4f}")
    logger.info(f"  Explained variance: {metrics['explained_variance']:.4f}")
    logger.info(f"  Max error: {metrics['max_error']:.4f}")
    
    return metrics

def analyze_residuals(y_true, y_pred):
    """Analyze prediction residuals"""
    logger.info("Analyzing prediction residuals")
    
    # Calculate residuals
    residuals = y_true - y_pred
    
    # Calculate residual statistics
    residual_stats = {
        'mean': np.mean(residuals),
        'std': np.std(residuals),
        'min': np.min(residuals),
        'max': np.max(residuals),
        'median': np.median(residuals),
        'skewness': float(pd.Series(residuals).skew()),
        'kurtosis': float(pd.Series(residuals).kurtosis())
    }
    
    # Log residual statistics
    logger.info("Residual statistics:")
    logger.info(f"  Mean: {residual_stats['mean']:.4f}")
    logger.info(f"  Std Dev: {residual_stats['std']:.4f}")
    logger.info(f"  Min: {residual_stats['min']:.4f}")
    logger.info(f"  Max: {residual_stats['max']:.4f}")
    logger.info(f"  Median: {residual_stats['median']:.4f}")
    
    return residuals, residual_stats

def analyze_by_range(y_true, y_pred):
    """Analyze performance across different ranges of the target variable"""
    logger.info("Analyzing performance by target value range")
    
    # Create a dataframe with true and predicted values
    df = pd.DataFrame({'true': y_true, 'pred': y_pred})
    
    # Create bins for the true values
    bins = pd.qcut(df['true'], q=4, duplicates='drop')
    df['bin'] = bins
    
    # Calculate metrics for each bin
    range_analysis = df.groupby('bin').apply(
        lambda x: pd.Series({
            'count': len(x),
            'mae': mean_absolute_error(x['true'], x['pred']),
            'mse': mean_squared_error(x['true'], x['pred']),
            'r2': r2_score(x['true'], x['pred']) if len(x) > 1 else np.nan,
            'mean_true': x['true'].mean(),
            'mean_pred': x['pred'].mean(),
            'min_true': x['true'].min(),
            'max_true': x['true'].max()
        })
    ).reset_index()
    
    # Convert bin ranges to strings for JSON serialization
    range_analysis['bin'] = range_analysis['bin'].apply(
        lambda x: f"{x.left:.2f} to {x.right:.2f}"
    )
    
    return range_analysis.to_dict(orient='records')

def save_evaluation(metrics, residual_stats, range_analysis, output_dir):
    """Save evaluation results to file"""
    logger.info("Saving evaluation results")
    
    # Create timestamp for output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create output dictionary with all evaluation results
    evaluation = {
        'timestamp': timestamp,
        'metrics': metrics,
        'residual_stats': residual_stats,
        'range_analysis': range_analysis
    }
    
    # Save as JSON file
    results_file = os.path.join(output_dir, f"evaluation_{timestamp}.json")
    with open(results_file, 'w') as f:
        json.dump(evaluation, f, indent=2)
    
    logger.info(f"Evaluation results saved to {results_file}")
    return results_file

def evaluate_model(model_file, features_file, output_dir, params):
    """Evaluate a trained model on test data"""
    # Load model
    model, explanations, training_results = load_model(model_file)
    
    # Load features
    df = load_features(features_file)
    
    # Get test data
    X_test, y_test = get_test_data(df, params)
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate evaluation metrics
    metrics = evaluate_predictions(y_test, y_pred)
    
    # Analyze residuals
    residuals, residual_stats = analyze_residuals(y_test, y_pred)
    
    # Analyze performance by range
    range_analysis = analyze_by_range(y_test, y_pred)
    
    # Save evaluation results
    results_file = save_evaluation(metrics, residual_stats, range_analysis, output_dir)
    
    return results_file

if __name__ == "__main__":
    # This allows the module to be run directly
    import argparse
    import yaml
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='Evaluate a trained model')
    parser.add_argument('--model', type=str, required=True,
                      help='Path to trained model file (.pkl)')
    parser.add_argument('--features', type=str, required=True,
                      help='Path to features CSV file')
    parser.add_argument('--config', type=str, default='config/default.yml',
                      help='Path to configuration file')
    parser.add_argument('--output-dir', type=str, default='results',
                      help='Directory to save evaluation results')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Evaluate model
    evaluate_model(args.model, args.features, args.output_dir, config['model']) 