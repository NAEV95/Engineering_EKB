#!/usr/bin/env python3
"""
Feature building module for ProMut-MD.
This module handles the creation and transformation of features for model training.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression

logger = logging.getLogger(__name__)

def scale_features(df, method='standard', target_column=None):
    """
    Scale features in the dataset.
    
    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing features
    method : str, optional
        Scaling method ('standard', 'minmax', 'robust'), by default 'standard'
    target_column : str, optional
        Name of target column to exclude from scaling, by default None
    
    Returns
    -------
    pandas.DataFrame
        DataFrame with scaled features
    """
    logger.info(f"Scaling features using {method} method")
    
    # Make a copy to avoid modifying the original
    scaled_df = df.copy()
    
    # Separate features and target if specified
    if target_column and target_column in scaled_df.columns:
        y = scaled_df[target_column].copy()
        X = scaled_df.drop(target_column, axis=1)
    else:
        X = scaled_df
        y = None
    
    # Select scaler based on method
    if method == 'minmax':
        scaler = MinMaxScaler()
    elif method == 'robust':
        scaler = RobustScaler()
    else:  # default to standard
        scaler = StandardScaler()
    
    # Scale features
    X_scaled = pd.DataFrame(
        scaler.fit_transform(X),
        columns=X.columns,
        index=X.index
    )
    
    # Combine with target if provided
    if y is not None:
        scaled_df = pd.concat([X_scaled, y.to_frame()], axis=1)
    else:
        scaled_df = X_scaled
    
    logger.info(f"Features scaled: {scaled_df.shape}")
    return scaled_df

def reduce_dimensions(df, method='pca', n_components=10, target_column=None):
    """
    Reduce dimensionality of the dataset.
    
    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing features
    method : str, optional
        Dimension reduction method ('pca'), by default 'pca'
    n_components : int, optional
        Number of components to keep, by default 10
    target_column : str, optional
        Name of target column to exclude from reduction, by default None
    
    Returns
    -------
    pandas.DataFrame
        DataFrame with reduced dimensions
    tuple
        (DataFrame with reduced dimensions, transformer object)
    """
    logger.info(f"Reducing dimensions using {method} to {n_components} components")
    
    # Make a copy to avoid modifying the original
    df_copy = df.copy()
    
    # Separate features and target if specified
    if target_column and target_column in df_copy.columns:
        y = df_copy[target_column].copy()
        X = df_copy.drop(target_column, axis=1)
    else:
        X = df_copy
        y = None
    
    # Limit components to number of features
    n_components = min(n_components, X.shape[1])
    
    # Select dimensionality reduction method
    if method == 'pca':
        transformer = PCA(n_components=n_components)
    else:
        logger.warning(f"Unknown dimensionality reduction method: {method}. Using PCA.")
        transformer = PCA(n_components=n_components)
    
    # Transform features
    X_transformed = transformer.fit_transform(X)
    
    # Create DataFrame with transformed features
    cols = [f"{method}{i+1}" for i in range(n_components)]
    X_transformed_df = pd.DataFrame(
        X_transformed,
        columns=cols,
        index=X.index
    )
    
    # Combine with target if provided
    if y is not None:
        result_df = pd.concat([X_transformed_df, y.to_frame()], axis=1)
    else:
        result_df = X_transformed_df
    
    logger.info(f"Dimensions reduced: {result_df.shape}")
    return result_df, transformer

def select_features(df, method='k_best', k=20, target_column=None):
    """
    Select most important features from the dataset.
    
    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing features
    method : str, optional
        Feature selection method ('k_best', 'mutual_info'), by default 'k_best'
    k : int, optional
        Number of features to select, by default 20
    target_column : str, optional
        Name of target column, by default None
    
    Returns
    -------
    pandas.DataFrame
        DataFrame with selected features
    dict
        Feature importance scores
    """
    logger.info(f"Selecting {k} best features using {method}")
    
    if target_column is None or target_column not in df.columns:
        logger.error("Target column must be specified for feature selection")
        return df, {}
    
    # Make a copy to avoid modifying the original
    df_copy = df.copy()
    
    # Separate features and target
    y = df_copy[target_column].copy()
    X = df_copy.drop(target_column, axis=1)
    
    # Limit k to number of features
    k = min(k, X.shape[1])
    
    # Select feature selection method
    if method == 'mutual_info':
        selector = SelectKBest(mutual_info_regression, k=k)
    else:  # default to f_regression
        selector = SelectKBest(f_regression, k=k)
    
    # Transform features
    X_selected = selector.fit_transform(X, y)
    
    # Get selected feature names
    selected_features = X.columns[selector.get_support()]
    
    # Create DataFrame with selected features
    X_selected_df = pd.DataFrame(
        X_selected,
        columns=selected_features,
        index=X.index
    )
    
    # Combine with target
    result_df = pd.concat([X_selected_df, y.to_frame()], axis=1)
    
    # Get feature importance scores
    scores = selector.scores_
    feature_scores = dict(zip(X.columns, scores))
    
    logger.info(f"Features selected: {result_df.shape}")
    return result_df, feature_scores

def create_polynomial_features(df, degree=2, target_column=None):
    """
    Create polynomial features from the dataset.
    
    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing features
    degree : int, optional
        Polynomial degree, by default 2
    target_column : str, optional
        Name of target column to exclude, by default None
    
    Returns
    -------
    pandas.DataFrame
        DataFrame with polynomial features
    """
    logger.info(f"Creating polynomial features with degree {degree}")
    
    from sklearn.preprocessing import PolynomialFeatures
    
    # Make a copy to avoid modifying the original
    df_copy = df.copy()
    
    # Separate features and target if specified
    if target_column and target_column in df_copy.columns:
        y = df_copy[target_column].copy()
        X = df_copy.drop(target_column, axis=1)
    else:
        X = df_copy
        y = None
    
    # Create polynomial features
    poly = PolynomialFeatures(degree=degree, include_bias=False)
    X_poly = poly.fit_transform(X)
    
    # Get feature names
    feature_names = poly.get_feature_names_out(X.columns)
    
    # Create DataFrame with polynomial features
    X_poly_df = pd.DataFrame(
        X_poly,
        columns=feature_names,
        index=X.index
    )
    
    # Combine with target if provided
    if y is not None:
        result_df = pd.concat([X_poly_df, y.to_frame()], axis=1)
    else:
        result_df = X_poly_df
    
    logger.info(f"Polynomial features created: {result_df.shape}")
    return result_df

def extract_features(df, params=None):
    """
    Extract and transform features from the dataset.
    
    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing raw data
    params : dict, optional
        Parameters for feature extraction, by default None
    
    Returns
    -------
    pandas.DataFrame
        DataFrame with extracted features
    """
    logger.info("Extracting and transforming features")
    
    if params is None:
        params = {}
    
    # Make a copy to avoid modifying the original
    result_df = df.copy()
    
    # Target column
    target_column = params.get('target_column', 'DELTA30')
    
    # Apply scaling if specified
    if params.get('scale_features', False):
        scale_method = params.get('scale_method', 'standard')
        result_df = scale_features(result_df, scale_method, target_column)
    
    # Apply dimensionality reduction if specified
    if params.get('reduce_dimensions', False):
        n_components = params.get('n_components', 10)
        result_df, _ = reduce_dimensions(result_df, 'pca', n_components, target_column)
    
    # Apply feature selection if specified
    if params.get('select_features', False):
        k = params.get('k_best', 20)
        selection_method = params.get('selection_method', 'k_best')
        result_df, _ = select_features(result_df, selection_method, k, target_column)
    
    # Apply polynomial features if specified
    if params.get('polynomial_features', False):
        degree = params.get('polynomial_degree', 2)
        result_df = create_polynomial_features(result_df, degree, target_column)
    
    logger.info(f"Feature extraction complete: {result_df.shape}")
    return result_df

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
    parser = argparse.ArgumentParser(description='Extract and transform features')
    parser.add_argument('--input', type=str, required=True,
                      help='Path to input data file')
    parser.add_argument('--output', type=str, required=True,
                      help='Path to output file')
    parser.add_argument('--config', type=str, default='config/default.yml',
                      help='Path to configuration file')
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Load data
    df = pd.read_csv(args.input, index_col=0)
    
    # Extract features
    result_df = extract_features(df, config.get('feature_extraction', {}))
    
    # Save results
    result_df.to_csv(args.output)
    logger.info(f"Results saved to {args.output}") 