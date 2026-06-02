#!/usr/bin/env python3
"""
Visualization module for ProMut-MD.
This module handles the generation of plots and visualizations from model training and evaluation.
"""

import os
import json
import pickle
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import shap

# Try to import plotly for interactive visualizations
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

logger = logging.getLogger(__name__)

def load_data(features_file, model_file=None, results_file=None):
    """Load data for visualization"""
    logger.info("Loading data for visualization")
    
    # Load features
    features_df = pd.read_csv(features_file, index_col=0)
    
    # Load model if available
    model_data = None
    if model_file and os.path.exists(model_file):
        logger.info(f"Loading model from {model_file}")
        with open(model_file, 'rb') as f:
            model_data = pickle.load(f)
    
    # Load evaluation results if available
    results_data = None
    if results_file and os.path.exists(results_file):
        logger.info(f"Loading evaluation results from {results_file}")
        with open(results_file, 'r') as f:
            results_data = json.load(f)
    
    return features_df, model_data, results_data

def plot_feature_importance(model_data, output_dir, params):
    """Create feature importance plots"""
    logger.info("Generating feature importance plots")
    
    # Extract feature importance from model data
    if 'explanations' not in model_data or 'feature_importance' not in model_data['explanations']:
        logger.warning("Feature importance data not found in model")
        return
    
    importance_df = model_data['explanations']['feature_importance']
    
    # Convert to DataFrame if it's a dictionary
    if isinstance(importance_df, dict):
        importance_df = pd.DataFrame(importance_df)
    
    # Sort by importance
    importance_df = importance_df.sort_values('importance', ascending=False)
    
    # Get top N features
    top_n = params.get('top_n_features', 20)
    top_features = importance_df.head(top_n)
    
    # Create plot
    plt.figure(figsize=(12, 8))
    sns.barplot(x='importance', y='feature', data=top_features)
    plt.title(f'Top {top_n} Feature Importance')
    plt.tight_layout()
    
    # Save plot
    output_file = os.path.join(output_dir, 'feature_importance.png')
    plt.savefig(output_file, dpi=params.get('figures', {}).get('dpi', 300))
    plt.close()
    
    logger.info(f"Feature importance plot saved to {output_file}")
    
    # Create interactive plot if plotly is available
    if PLOTLY_AVAILABLE and params.get('interactive', {}).get('enabled', False):
        fig = px.bar(top_features, x='importance', y='feature', 
                     title=f'Top {top_n} Feature Importance',
                     orientation='h')
        
        interactive_file = os.path.join(output_dir, 'feature_importance_interactive.html')
        fig.write_html(interactive_file)
        logger.info(f"Interactive feature importance plot saved to {interactive_file}")

def plot_shap_summary(model_data, features_df, output_dir, params):
    """Create SHAP summary plots"""
    logger.info("Generating SHAP summary plots")
    
    # Extract SHAP data from model
    if ('explanations' not in model_data or 
        'shap_values' not in model_data['explanations'] or 
        'shap_explainer' not in model_data['explanations']):
        logger.warning("SHAP data not found in model")
        return
    
    # Get SHAP values and explainer
    shap_values = model_data['explanations']['shap_values']
    explainer = model_data['explanations']['shap_explainer']
    
    # Assume target column is 'DELTA30'
    target_column = params.get('target_column', 'DELTA30')
    X = features_df.drop(target_column, axis=1)
    if shap_values is not None and hasattr(shap_values, "shape") and len(shap_values.shape) >= 2:
        shap_rows = shap_values.shape[0]
        if shap_rows != len(X):
            logger.warning(
                "SHAP values contain %d rows but feature data contains %d rows; "
                "using the first %d feature rows for the summary plot.",
                shap_rows,
                len(X),
                min(shap_rows, len(X)),
            )
            X = X.iloc[:shap_rows]

    # Create SHAP summary plot
    plt.figure(figsize=(12, 8))
    shap.summary_plot(shap_values, X, show=False)
    plt.tight_layout()
    
    # Save plot
    output_file = os.path.join(output_dir, 'shap_summary.png')
    plt.savefig(output_file, dpi=params.get('figures', {}).get('dpi', 300), bbox_inches='tight')
    plt.close()
    
    logger.info(f"SHAP summary plot saved to {output_file}")
    
    # Create SHAP bar plot
    plt.figure(figsize=(12, 8))
    shap.summary_plot(shap_values, X, plot_type='bar', show=False)
    plt.tight_layout()
    
    # Save plot
    output_file = os.path.join(output_dir, 'shap_bar.png')
    plt.savefig(output_file, dpi=params.get('figures', {}).get('dpi', 300), bbox_inches='tight')
    plt.close()
    
    logger.info(f"SHAP bar plot saved to {output_file}")

def plot_prediction_scatter(results_data, output_dir, params):
    """Create scatter plot of predicted vs actual values"""
    logger.info("Generating prediction scatter plot")
    
    if not results_data or 'metrics' not in results_data:
        logger.warning("Results data not found or incomplete")
        return
    
    # Check if y_test and y_pred are in results
    if 'y_test' not in results_data or 'y_pred' not in results_data:
        logger.warning("Prediction data not found in results")
        return
    
    # Extract prediction data
    y_test = results_data['y_test']
    y_pred = results_data['y_pred']
    
    # Create DataFrame
    df = pd.DataFrame({'True': y_test, 'Predicted': y_pred})
    
    # Create scatter plot
    plt.figure(figsize=(10, 8))
    sns.scatterplot(x='True', y='Predicted', data=df, alpha=0.6)
    
    # Add perfect prediction line
    min_val = min(df['True'].min(), df['Predicted'].min())
    max_val = max(df['True'].max(), df['Predicted'].max())
    plt.plot([min_val, max_val], [min_val, max_val], 'r--')
    
    # Add R² value to plot
    r2 = results_data['metrics']['r2']
    plt.text(0.05, 0.95, f'R² = {r2:.4f}', transform=plt.gca().transAxes,
             fontsize=12, verticalalignment='top')
    
    plt.title('Predicted vs True Values')
    plt.xlabel('True Values')
    plt.ylabel('Predicted Values')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save plot
    output_file = os.path.join(output_dir, 'prediction_scatter.png')
    plt.savefig(output_file, dpi=params.get('figures', {}).get('dpi', 300))
    plt.close()
    
    logger.info(f"Prediction scatter plot saved to {output_file}")
    
    # Create interactive plot if plotly is available
    if PLOTLY_AVAILABLE and params.get('interactive', {}).get('enabled', False):
        fig = px.scatter(df, x='True', y='Predicted', 
                        title='Predicted vs True Values')
        
        # Add perfect prediction line
        fig.add_trace(go.Scatter(x=[min_val, max_val], y=[min_val, max_val],
                                mode='lines', name='Perfect Prediction',
                                line=dict(color='red', dash='dash')))
        
        # Add R² annotation
        fig.add_annotation(x=0.05, y=0.95, xref='paper', yref='paper',
                          text=f'R² = {r2:.4f}', showarrow=False,
                          font=dict(size=14))
        
        interactive_file = os.path.join(output_dir, 'prediction_scatter_interactive.html')
        fig.write_html(interactive_file)
        logger.info(f"Interactive prediction scatter plot saved to {interactive_file}")

def plot_residuals(results_data, output_dir, params):
    """Create residual plots"""
    logger.info("Generating residual plots")
    
    if not results_data or 'residual_stats' not in results_data:
        logger.warning("Residual data not found in results")
        return
    
    # Extract prediction data
    if 'y_test' not in results_data or 'y_pred' not in results_data:
        logger.warning("Prediction data not found in results")
        return
    
    y_test = results_data['y_test']
    y_pred = results_data['y_pred']
    
    # Calculate residuals
    residuals = np.array(y_test) - np.array(y_pred)
    
    # Create DataFrame
    df = pd.DataFrame({
        'True': y_test,
        'Predicted': y_pred,
        'Residuals': residuals
    })
    
    # Create residual vs fitted plot
    plt.figure(figsize=(10, 8))
    sns.scatterplot(x='Predicted', y='Residuals', data=df, alpha=0.6)
    plt.axhline(y=0, color='r', linestyle='--')
    plt.title('Residuals vs Predicted Values')
    plt.xlabel('Predicted Values')
    plt.ylabel('Residuals')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save plot
    output_file = os.path.join(output_dir, 'residuals_vs_predicted.png')
    plt.savefig(output_file, dpi=params.get('figures', {}).get('dpi', 300))
    plt.close()
    
    logger.info(f"Residuals vs predicted plot saved to {output_file}")
    
    # Create residual histogram
    plt.figure(figsize=(10, 8))
    sns.histplot(residuals, kde=True)
    plt.title('Residual Distribution')
    plt.xlabel('Residual Value')
    plt.ylabel('Frequency')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save plot
    output_file = os.path.join(output_dir, 'residual_histogram.png')
    plt.savefig(output_file, dpi=params.get('figures', {}).get('dpi', 300))
    plt.close()
    
    logger.info(f"Residual histogram saved to {output_file}")

def plot_performance_by_range(results_data, output_dir, params):
    """Create plots showing model performance across different ranges of the target variable"""
    logger.info("Generating performance by range plots")
    
    if not results_data or 'range_analysis' not in results_data:
        logger.warning("Range analysis data not found in results")
        return
    
    # Extract range analysis data
    range_analysis = results_data['range_analysis']
    
    # Convert to DataFrame if needed
    if isinstance(range_analysis, list):
        range_df = pd.DataFrame(range_analysis)
    else:
        range_df = pd.DataFrame([range_analysis])

    required_columns = {'bin', 'mae', 'r2'}
    if range_df.empty or not required_columns.issubset(range_df.columns):
        logger.warning("Range analysis data is empty or incomplete; skipping performance by range plots")
        return
    
    # Create bar plot for MAE by range
    plt.figure(figsize=(12, 6))
    sns.barplot(x='bin', y='mae', data=range_df)
    plt.title('MAE by Target Value Range')
    plt.xlabel('Target Value Range')
    plt.ylabel('Mean Absolute Error')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Save plot
    output_file = os.path.join(output_dir, 'mae_by_range.png')
    plt.savefig(output_file, dpi=params.get('figures', {}).get('dpi', 300))
    plt.close()
    
    logger.info(f"MAE by range plot saved to {output_file}")
    
    # Create bar plot for R² by range
    plt.figure(figsize=(12, 6))
    sns.barplot(x='bin', y='r2', data=range_df)
    plt.title('R² by Target Value Range')
    plt.xlabel('Target Value Range')
    plt.ylabel('R² Score')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Save plot
    output_file = os.path.join(output_dir, 'r2_by_range.png')
    plt.savefig(output_file, dpi=params.get('figures', {}).get('dpi', 300))
    plt.close()
    
    logger.info(f"R² by range plot saved to {output_file}")

def plot_feature_distributions(features_df, output_dir, params):
    """Create plots showing the distribution of key features"""
    logger.info("Generating feature distribution plots")
    
    # Assume target column is 'DELTA30'
    target_column = params.get('target_column', 'DELTA30')
    
    # Plot target distribution
    plt.figure(figsize=(10, 6))
    sns.histplot(features_df[target_column], kde=True)
    plt.title(f'Distribution of {target_column} (Target Variable)')
    plt.xlabel(target_column)
    plt.ylabel('Frequency')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save plot
    output_file = os.path.join(output_dir, 'target_distribution.png')
    plt.savefig(output_file, dpi=params.get('figures', {}).get('dpi', 300))
    plt.close()
    
    logger.info(f"Target distribution plot saved to {output_file}")
    
    # Get top N features if feature importance is available
    if params.get('top_n_features_to_plot', 0) > 0:
        n_features = params.get('top_n_features_to_plot')
        X = features_df.drop(target_column, axis=1)
        
        # Select features to plot (either from importance or first N)
        if 'feature_importance' in params:
            important_features = params['feature_importance'][:n_features]
        else:
            important_features = X.columns[:n_features]
        
        # Create directory for feature distributions
        feature_dir = os.path.join(output_dir, 'feature_distributions')
        os.makedirs(feature_dir, exist_ok=True)
        
        # Plot each feature
        for feature in important_features:
            plt.figure(figsize=(10, 6))
            sns.histplot(X[feature], kde=True)
            plt.title(f'Distribution of {feature}')
            plt.xlabel(feature)
            plt.ylabel('Frequency')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Save plot
            output_file = os.path.join(feature_dir, f'{feature}_distribution.png')
            plt.savefig(output_file, dpi=params.get('figures', {}).get('dpi', 300))
            plt.close()
        
        logger.info(f"Feature distribution plots saved to {feature_dir}")

def generate_visualizations(features_file, model_file=None, results_file=None, output_dir='figures', params=None):
    """Generate all visualizations from the provided data"""
    # Set default parameters if none provided
    if not params:
        params = {
            'figures': {'format': 'png', 'dpi': 300},
            'interactive': {'enabled': True},
            'top_n_features': 20,
            'top_n_features_to_plot': 5,
            'target_column': 'DELTA30'
        }
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    features_df, model_data, results_data = load_data(
        features_file, model_file, results_file
    )
    
    # Generate visualizations
    
    # Feature distributions (always available with features)
    plot_feature_distributions(features_df, output_dir, params)
    
    # Model-specific visualizations
    if model_data:
        plot_feature_importance(model_data, output_dir, params)
        plot_shap_summary(model_data, features_df, output_dir, params)
    
    # Results-specific visualizations
    if results_data:
        plot_prediction_scatter(results_data, output_dir, params)
        plot_residuals(results_data, output_dir, params)
        plot_performance_by_range(results_data, output_dir, params)
    
    logger.info("All visualizations generated successfully")

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
    parser = argparse.ArgumentParser(description='Generate visualizations from model results')
    parser.add_argument('--features', type=str, required=True,
                      help='Path to features CSV file')
    parser.add_argument('--model', type=str,
                      help='Path to trained model file (.pkl)')
    parser.add_argument('--results', type=str,
                      help='Path to evaluation results file (.json)')
    parser.add_argument('--config', type=str, default='config/default.yml',
                      help='Path to configuration file')
    parser.add_argument('--output-dir', type=str, default='figures',
                      help='Directory to save visualizations')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Generate visualizations
    generate_visualizations(
        args.features,
        args.model,
        args.results,
        args.output_dir,
        config.get('visualization', {})
    )
