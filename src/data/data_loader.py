#!/usr/bin/env python3
"""
Data loading module for ProMut-MD.
This module handles loading and preprocessing data from simulation output files.
"""

import os
import logging
import numpy as np
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

def load_md_data(data_dir, file_pattern='*.dat'):
    """
    Load molecular dynamics data from files matching the pattern in data_dir.
    
    Parameters
    ----------
    data_dir : str
        Directory containing MD data files
    file_pattern : str, optional
        Glob pattern to match files, by default '*.dat'
    
    Returns
    -------
    dict
        Dictionary of pandas DataFrames with file names as keys
    """
    logger.info(f"Loading MD data from {data_dir}")
    
    # Initialize dictionary to store data
    data_dict = {}
    
    # Get list of data files
    data_files = list(Path(data_dir).glob(file_pattern))
    logger.info(f"Found {len(data_files)} files matching pattern '{file_pattern}'")
    
    # Load each file
    for file_path in data_files:
        file_name = file_path.stem
        try:
            # Try different delimiters and headers
            try:
                df = pd.read_csv(file_path, sep=r'\s+', header=None)
            except:
                try:
                    df = pd.read_csv(file_path, sep=',', header=None)
                except:
                    df = pd.read_csv(file_path, sep='\t', header=None)
            
            data_dict[file_name] = df
            logger.debug(f"Loaded {file_path} with shape {df.shape}")
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {str(e)}")
    
    return data_dict

def load_pocket_data(pocket_dir, descriptor_file='mdpout_descriptors.txt'):
    """
    Load pocket descriptor data from MDpocket output.
    
    Parameters
    ----------
    pocket_dir : str
        Directory containing MDpocket output
    descriptor_file : str, optional
        Name of the descriptor file, by default 'mdpout_descriptors.txt'
    
    Returns
    -------
    pandas.DataFrame
        DataFrame containing pocket descriptors
    """
    logger.info(f"Loading pocket data from {pocket_dir}")
    
    # Path to descriptor file
    file_path = os.path.join(pocket_dir, descriptor_file)
    
    try:
        # Load descriptor file
        df = pd.read_csv(file_path, sep=r'\s+', header=None)
        logger.info(f"Loaded pocket descriptors with shape {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Failed to load pocket descriptors from {file_path}: {str(e)}")
        return None

def load_sequence_data(sequence_file):
    """
    Load protein sequence data and derived features.
    
    Parameters
    ----------
    sequence_file : str
        Path to file containing sequence data
    
    Returns
    -------
    pandas.DataFrame
        DataFrame containing sequence features
    """
    logger.info(f"Loading sequence data from {sequence_file}")
    
    try:
        # Determine file format based on extension
        ext = Path(sequence_file).suffix.lower()
        
        if ext == '.csv':
            df = pd.read_csv(sequence_file)
        elif ext == '.xlsx' or ext == '.xls':
            df = pd.read_excel(sequence_file)
        elif ext == '.dat' or ext == '.txt':
            df = pd.read_csv(sequence_file, sep=r'\s+')
        else:
            logger.warning(f"Unknown file extension {ext}, trying generic CSV loader")
            df = pd.read_csv(sequence_file)
        
        logger.info(f"Loaded sequence data with shape {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Failed to load sequence data from {sequence_file}: {str(e)}")
        return None

def merge_datasets(md_data, pocket_data, sequence_data):
    """
    Merge different types of data into a single dataset.
    
    Parameters
    ----------
    md_data : dict or pandas.DataFrame
        MD simulation data
    pocket_data : pandas.DataFrame
        Pocket descriptor data
    sequence_data : pandas.DataFrame
        Sequence feature data
    
    Returns
    -------
    pandas.DataFrame
        Merged dataset
    """
    logger.info("Merging datasets")
    
    # Convert md_data dict to DataFrame if necessary
    if isinstance(md_data, dict):
        md_df = pd.concat(md_data.values(), axis=1)
    else:
        md_df = md_data
    
    # Ensure all dataframes have the same index length
    min_length = min(len(md_df), len(pocket_data), len(sequence_data))
    md_df = md_df.iloc[:min_length]
    pocket_data = pocket_data.iloc[:min_length]
    sequence_data = sequence_data.iloc[:min_length]
    
    # Merge dataframes
    merged_df = pd.concat([md_df, pocket_data, sequence_data], axis=1)
    
    logger.info(f"Created merged dataset with shape {merged_df.shape}")
    return merged_df

def load_features_file(features_file):
    """
    Load features from a CSV file.
    
    Parameters
    ----------
    features_file : str
        Path to features CSV file
    
    Returns
    -------
    pandas.DataFrame
        DataFrame containing features
    """
    logger.info(f"Loading features from {features_file}")
    
    try:
        df = pd.read_csv(features_file, index_col=0)
        logger.info(f"Loaded features with shape {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Failed to load features from {features_file}: {str(e)}")
        return None

def load_results(results_dir, pattern='*.csv'):
    """
    Load simulation results from multiple files.
    
    Parameters
    ----------
    results_dir : str
        Directory containing result files
    pattern : str, optional
        File pattern to match, by default '*.csv'
    
    Returns
    -------
    pandas.DataFrame
        DataFrame containing combined results
    """
    logger.info(f"Loading simulation results from {results_dir}")
    
    # Get list of result files
    result_files = list(Path(results_dir).glob(pattern))
    
    if not result_files:
        logger.warning(f"No files matching pattern '{pattern}' found in {results_dir}")
        return None
    
    # Initialize empty list to store dataframes
    dfs = []
    
    # Load each file
    for file_path in result_files:
        try:
            df = pd.read_csv(file_path)
            dfs.append(df)
            logger.debug(f"Loaded {file_path} with shape {df.shape}")
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {str(e)}")
    
    # Combine dataframes
    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)
        logger.info(f"Combined {len(dfs)} result files into dataset with shape {combined_df.shape}")
        return combined_df
    else:
        logger.warning("No results could be loaded")
        return None

def preprocess_data(df, params=None):
    """
    Preprocess data for analysis and modeling.
    
    Parameters
    ----------
    df : pandas.DataFrame
        Raw data to preprocess
    params : dict, optional
        Preprocessing parameters, by default None
    
    Returns
    -------
    pandas.DataFrame
        Preprocessed data
    """
    logger.info("Preprocessing data")
    
    if params is None:
        params = {}
    
    # Make a copy to avoid modifying the original
    processed_df = df.copy()
    
    # Handle missing values
    if params.get('handle_missing', True):
        missing_strategy = params.get('missing_strategy', 'mean')
        
        if missing_strategy == 'mean':
            processed_df = processed_df.fillna(processed_df.mean())
        elif missing_strategy == 'median':
            processed_df = processed_df.fillna(processed_df.median())
        elif missing_strategy == 'drop':
            processed_df = processed_df.dropna()
        else:
            processed_df = processed_df.fillna(0)
    
    # Remove outliers if specified
    if params.get('remove_outliers', False):
        z_threshold = params.get('outlier_threshold', 3)
        
        # Calculate z-scores
        z_scores = np.abs((processed_df - processed_df.mean()) / processed_df.std())
        
        # Filter rows with high z-scores
        processed_df = processed_df[(z_scores < z_threshold).all(axis=1)]
    
    # Scale features if specified
    if params.get('scale_features', False):
        scale_method = params.get('scale_method', 'standard')
        
        if scale_method == 'standard':
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
        elif scale_method == 'minmax':
            from sklearn.preprocessing import MinMaxScaler
            scaler = MinMaxScaler()
        elif scale_method == 'robust':
            from sklearn.preprocessing import RobustScaler
            scaler = RobustScaler()
        else:
            logger.warning(f"Unknown scaling method '{scale_method}', using StandardScaler")
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
        
        # Get column names for later
        columns = processed_df.columns
        
        # Apply scaling
        processed_data = scaler.fit_transform(processed_df)
        
        # Convert back to DataFrame
        processed_df = pd.DataFrame(processed_data, columns=columns)
    
    logger.info(f"Preprocessed data shape: {processed_df.shape}")
    return processed_df

def load_data(data_config):
    """
    Main function to load data based on configuration.
    
    Parameters
    ----------
    data_config : dict
        Data loading configuration
    
    Returns
    -------
    pandas.DataFrame
        Loaded and processed data
    """
    data_type = data_config.get('type', 'features')
    
    if data_type == 'features':
        # Load pre-computed features
        features_file = data_config.get('features_file')
        if not features_file:
            logger.error("No features file specified in configuration")
            return None
        
        df = load_features_file(features_file)
    
    elif data_type == 'raw':
        # Load raw data from various sources
        md_dir = data_config.get('md_dir')
        pocket_dir = data_config.get('pocket_dir')
        sequence_file = data_config.get('sequence_file')
        
        if not (md_dir and pocket_dir and sequence_file):
            logger.error("Missing required data directories/files in configuration")
            return None
        
        # Load different data types
        md_data = load_md_data(md_dir)
        pocket_data = load_pocket_data(pocket_dir)
        sequence_data = load_sequence_data(sequence_file)
        
        # Merge datasets
        df = merge_datasets(md_data, pocket_data, sequence_data)
    
    elif data_type == 'results':
        # Load simulation results
        results_dir = data_config.get('results_dir')
        if not results_dir:
            logger.error("No results directory specified in configuration")
            return None
        
        df = load_results(results_dir)
    
    else:
        logger.error(f"Unknown data type: {data_type}")
        return None
    
    # Preprocess data if specified
    if data_config.get('preprocess', True):
        df = preprocess_data(df, data_config.get('preprocess_params', {}))
    
    return df

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
    parser = argparse.ArgumentParser(description='Load data for ProMut-MD')
    parser.add_argument('--config', type=str, required=True,
                      help='Path to data configuration file')
    parser.add_argument('--output', type=str, default='data/processed/features.csv',
                      help='Path to output file')
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Load data
    df = load_data(config['data'])
    
    # Save processed data
    if df is not None:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        df.to_csv(args.output)
        logger.info(f"Data saved to {args.output}")
    else:
        logger.error("Failed to load and process data") 