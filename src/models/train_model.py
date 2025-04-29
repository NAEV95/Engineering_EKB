#!/usr/bin/env python3
"""
Model training module for ProMut-MD.
This module handles the training of predictive models for mutation effect prediction.
"""

import os
import pickle
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import lightgbm as lgb
import shap

logger = logging.getLogger(__name__)

def load_features(features_file):
    """Load features from CSV file"""
    logger.info(f"Loading features from {features_file}")
    df = pd.read_csv(features_file, index_col=0)
    return df

def preprocess_data(df, params):
    """Preprocess data for model training"""
    logger.info("Preprocessing data for model training")
    
    # Assume the target column is 'DELTA30' - adapt as needed
    target_column = params.get('target_column', 'DELTA30')
    
    # Split features and target
    X = df.drop(target_column, axis=1)
    y = df[target_column]
    
    # Handle missing data if any
    X = X.fillna(X.mean())
    
    # Apply feature scaling if specified
    if params.get('feature_scaling', True):
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X = pd.DataFrame(scaler.fit_transform(X), columns=X.columns, index=X.index)
    
    # Train-test split
    test_size = 1.0 - params.get('train_test_split', 0.8)
    random_seed = params.get('random_seed', 42)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_seed
    )
    
    return X_train, X_test, y_train, y_test

def train_lightgbm_model(X_train, y_train, params):
    """Train a LightGBM model"""
    logger.info("Training LightGBM model")
    
    # Get model parameters from config
    lgb_params = params.get('lightgbm', {})
    
    # Create model with parameters from config
    model = lgb.LGBMRegressor(
        learning_rate=lgb_params.get('learning_rate', 0.05),
        max_depth=lgb_params.get('max_depth', 5),
        n_estimators=lgb_params.get('n_estimators', 200),
        reg_alpha=lgb_params.get('reg_alpha', 0.1),
        reg_lambda=lgb_params.get('reg_lambda', 1.0),
        subsample=lgb_params.get('subsample', 0.8),
        colsample_bytree=lgb_params.get('colsample_bytree', 0.8),
        random_state=params.get('random_seed', 42)
    )
    
    # Train model
    model.fit(X_train, y_train)
    
    # Optionally perform cross-validation
    if params.get('cross_validation', 0) > 0:
        cv = params.get('cross_validation')
        cv_scores = cross_val_score(
            model, X_train, y_train, 
            cv=cv, scoring='neg_mean_squared_error'
        )
        logger.info(f"Cross-validation MSE: {-np.mean(cv_scores):.4f} ± {np.std(cv_scores):.4f}")
    
    return model

def evaluate_model(model, X_test, y_test):
    """Evaluate model performance on test set"""
    logger.info("Evaluating model on test set")
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate metrics
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    logger.info(f"Model performance:")
    logger.info(f"  MSE: {mse:.4f}")
    logger.info(f"  RMSE: {rmse:.4f}")
    logger.info(f"  MAE: {mae:.4f}")
    logger.info(f"  R²: {r2:.4f}")
    
    results = {
        'mse': mse,
        'rmse': rmse,
        'mae': mae,
        'r2': r2,
        'y_test': y_test,
        'y_pred': y_pred
    }
    
    return results

def explain_model(model, X_train, feature_names):
    """Generate model explanations using SHAP"""
    logger.info("Generating model explanations with SHAP")
    
    # Create SHAP explainer for LightGBM model
    explainer = shap.TreeExplainer(model)
    
    # Calculate SHAP values
    shap_values = explainer.shap_values(X_train)
    
    # Get feature importance
    importance = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    logger.info("Top 10 most important features:")
    for i, row in importance.head(10).iterrows():
        logger.info(f"  {row['feature']}: {row['importance']:.4f}")
    
    return {
        'shap_values': shap_values,
        'shap_explainer': explainer,
        'feature_importance': importance
    }

def save_model(model, explanations, results, output_dir):
    """Save trained model and results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save model
    model_file = os.path.join(output_dir, f"model_{timestamp}.pkl")
    with open(model_file, 'wb') as f:
        pickle.dump({
            'model': model,
            'explanations': explanations,
            'results': results
        }, f)
    
    logger.info(f"Model saved to {model_file}")
    
    return model_file

def train_model(features_file, output_dir, params):
    """Train a model from extracted features"""
    # Load features
    df = load_features(features_file)
    
    # Preprocess data
    X_train, X_test, y_train, y_test = preprocess_data(df, params)
    
    # Train model based on type specified in params
    model_type = params.get('type', 'lightgbm')
    if model_type == 'lightgbm':
        model = train_lightgbm_model(X_train, y_train, params)
    else:
        logger.error(f"Unsupported model type: {model_type}")
        raise ValueError(f"Unsupported model type: {model_type}")
    
    # Evaluate model
    results = evaluate_model(model, X_test, y_test)
    
    # Generate explanations
    explanations = explain_model(model, X_train, X_train.columns)
    
    # Save model and results
    model_file = save_model(model, explanations, results, output_dir)
    
    return model_file

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
    parser = argparse.ArgumentParser(description='Train a model for mutation effect prediction')
    parser.add_argument('--features', type=str, required=True,
                      help='Path to features CSV file')
    parser.add_argument('--config', type=str, default='config/default.yml',
                      help='Path to configuration file')
    parser.add_argument('--output-dir', type=str, default='models',
                      help='Directory to save model')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Train model
    train_model(args.features, args.output_dir, config['model']) 