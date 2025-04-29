#!/usr/bin/env python3
"""
Feature extraction script for ProMut-MD.
Extracts features from molecular dynamics simulation results for use in machine learning models.
"""

import os
import sys
import argparse
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add root directory to path
script_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(script_dir))

from src.data.data_loader import load_md_data, load_pocket_data, load_sequence_data, merge_datasets, preprocess_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("feature_extraction.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def extract_pocket_features(md_dir, params):
    """
    Extract pocket-related features using MDpocket/Fpocket.
    
    Parameters
    ----------
    md_dir : str
        Directory containing MD simulation results
    params : dict
        Parameters for feature extraction
    
    Returns
    -------
    pandas.DataFrame
        DataFrame containing pocket features
    """
    logger.info("Extracting pocket features")
    
    # Get list of subdirectories with simulation data
    sim_dirs = [d for d in Path(md_dir).iterdir() if d.is_dir()]
    logger.info(f"Found {len(sim_dirs)} simulation directories")
    
    # Initialize list to store data
    feature_dfs = []
    
    # Default MDpocket descriptor file
    descriptor_file = params.get('descriptor_file', 'mdpout_descriptors.txt')
    
    # Process each simulation directory
    for sim_dir in sim_dirs:
        logger.debug(f"Processing {sim_dir}")
        
        try:
            # Load pocket descriptors
            pocket_data = load_pocket_data(sim_dir, descriptor_file)
            
            if pocket_data is None:
                logger.warning(f"No pocket data found in {sim_dir}")
                continue
            
            # Calculate average descriptors across frames
            avg_descriptors = pocket_data.mean(axis=0)
            
            # Create a DataFrame with simulation name and descriptors
            df = pd.DataFrame([avg_descriptors], index=[sim_dir.name])
            
            # Add to list
            feature_dfs.append(df)
        
        except Exception as e:
            logger.error(f"Error processing {sim_dir}: {str(e)}")
    
    # Combine all simulation data
    if feature_dfs:
        pocket_features = pd.concat(feature_dfs)
        
        # Add proper column names
        descriptor_names = params.get('descriptor_names', [f'pocket_desc_{i}' for i in range(pocket_features.shape[1])])
        pocket_features.columns = descriptor_names[:pocket_features.shape[1]]
        
        logger.info(f"Extracted pocket features with shape {pocket_features.shape}")
        return pocket_features
    else:
        logger.warning("No pocket features could be extracted")
        return None

def extract_md_features(md_dir, params):
    """
    Extract molecular dynamics-related features.
    
    Parameters
    ----------
    md_dir : str
        Directory containing MD simulation results
    params : dict
        Parameters for feature extraction
    
    Returns
    -------
    pandas.DataFrame
        DataFrame containing MD features
    """
    logger.info("Extracting MD features")
    
    # Get list of subdirectories with simulation data
    sim_dirs = [d for d in Path(md_dir).iterdir() if d.is_dir()]
    
    # Initialize list to store data
    feature_dfs = []
    
    # Files to look for dynamic properties
    md_files = params.get('md_files', {
        'rmsf': 'rmsf_*.xvg',
        'rmsd': 'rmsd_*.dat',
        'rg': 'gyrate.xvg',
        'energy': 'energy.xvg'
    })
    
    # Process each simulation directory
    for sim_dir in sim_dirs:
        logger.debug(f"Processing {sim_dir}")
        
        try:
            # Initialize features for this simulation
            sim_features = {}
            
            # Process RMSD data
            rmsd_files = list(sim_dir.glob(md_files['rmsd']))
            if rmsd_files:
                rmsd_data = load_md_data(sim_dir, md_files['rmsd'])
                
                # Calculate RMSD statistics
                for name, df in rmsd_data.items():
                    if df.shape[1] >= 2:  # Make sure we have time and value columns
                        # Usually column 0 is time, column 1 is RMSD value
                        rmsd_values = df.iloc[:, 1].values
                        sim_features[f'{name}_mean'] = np.mean(rmsd_values)
                        sim_features[f'{name}_std'] = np.std(rmsd_values)
                        sim_features[f'{name}_max'] = np.max(rmsd_values)
            
            # Process Radius of Gyration data
            rg_files = list(sim_dir.glob(md_files['rg']))
            if rg_files:
                rg_data = load_md_data(sim_dir, md_files['rg'])
                
                # Calculate Rg statistics
                for name, df in rg_data.items():
                    if df.shape[1] >= 2:  # Make sure we have time and value columns
                        # Usually column 0 is time, column 1 is Rg value
                        rg_values = df.iloc[:, 1].values
                        sim_features[f'{name}_mean'] = np.mean(rg_values)
                        sim_features[f'{name}_std'] = np.std(rg_values)
                        sim_features[f'{name}_min'] = np.min(rg_values)
                        sim_features[f'{name}_max'] = np.max(rg_values)
            
            # Process RMSF data
            rmsf_files = list(sim_dir.glob(md_files['rmsf']))
            if rmsf_files:
                rmsf_data = load_md_data(sim_dir, md_files['rmsf'])
                
                # Calculate RMSF statistics
                for name, df in rmsf_data.items():
                    if df.shape[1] >= 2:  # Make sure we have residue and value columns
                        # Usually column 0 is residue number, column 1 is RMSF value
                        rmsf_values = df.iloc[:, 1].values
                        sim_features[f'{name}_mean'] = np.mean(rmsf_values)
                        sim_features[f'{name}_std'] = np.std(rmsf_values)
                        sim_features[f'{name}_max'] = np.max(rmsf_values)
                        
                        # Add features for specific regions if defined
                        regions = params.get('regions', {})
                        for region_name, region_range in regions.items():
                            start, end = region_range
                            if start < df.shape[0] and end <= df.shape[0]:
                                region_values = df.iloc[start:end, 1].values
                                sim_features[f'{name}_{region_name}_mean'] = np.mean(region_values)
                                sim_features[f'{name}_{region_name}_std'] = np.std(region_values)
                                sim_features[f'{name}_{region_name}_max'] = np.max(region_values)
            
            # Create DataFrame for this simulation
            if sim_features:
                df = pd.DataFrame([sim_features], index=[sim_dir.name])
                feature_dfs.append(df)
            else:
                logger.warning(f"No MD features extracted for {sim_dir}")
        
        except Exception as e:
            logger.error(f"Error processing {sim_dir}: {str(e)}")
    
    # Combine all simulation data
    if feature_dfs:
        md_features = pd.concat(feature_dfs)
        logger.info(f"Extracted MD features with shape {md_features.shape}")
        return md_features
    else:
        logger.warning("No MD features could be extracted")
        return None

def extract_sequence_features(md_dir, params):
    """
    Extract sequence-based features.
    
    Parameters
    ----------
    md_dir : str
        Directory containing MD simulation results
    params : dict
        Parameters for feature extraction
    
    Returns
    -------
    pandas.DataFrame
        DataFrame containing sequence features
    """
    logger.info("Extracting sequence features")
    
    # Get list of subdirectories with simulation data
    sim_dirs = [d for d in Path(md_dir).iterdir() if d.is_dir()]
    
    # Initialize list to store data
    feature_dfs = []
    
    # Files to look for sequence data
    seq_file = params.get('sequence_file', 'seq_features*.dat')
    
    # Process each simulation directory
    for sim_dir in sim_dirs:
        logger.debug(f"Processing {sim_dir}")
        
        try:
            # Look for sequence file
            seq_files = list(sim_dir.glob(seq_file))
            
            if not seq_files:
                logger.warning(f"No sequence file found in {sim_dir}")
                continue
            
            # Use the first matching file
            seq_data = load_sequence_data(seq_files[0])
            
            if seq_data is None:
                logger.warning(f"Failed to load sequence data from {seq_files[0]}")
                continue
            
            # Add simulation identifier
            seq_data['simulation'] = sim_dir.name
            
            # Set index to simulation name
            seq_data = seq_data.set_index('simulation')
            
            # Add to list
            feature_dfs.append(seq_data)
        
        except Exception as e:
            logger.error(f"Error processing {sim_dir}: {str(e)}")
    
    # Combine all simulation data
    if feature_dfs:
        seq_features = pd.concat(feature_dfs)
        logger.info(f"Extracted sequence features with shape {seq_features.shape}")
        return seq_features
    else:
        logger.warning("No sequence features could be extracted")
        return None

def extract_secondary_structure(md_dir, params):
    """
    Extract secondary structure features.
    
    Parameters
    ----------
    md_dir : str
        Directory containing MD simulation results
    params : dict
        Parameters for feature extraction
    
    Returns
    -------
    pandas.DataFrame
        DataFrame containing secondary structure features
    """
    logger.info("Extracting secondary structure features")
    
    # Get list of subdirectories with simulation data
    sim_dirs = [d for d in Path(md_dir).iterdir() if d.is_dir()]
    
    # Initialize list to store data
    feature_dfs = []
    
    # Files to look for secondary structure data
    ss_file = params.get('ss_file', 'Summary_*.dat')
    
    # Process each simulation directory
    for sim_dir in sim_dirs:
        logger.debug(f"Processing {sim_dir}")
        
        try:
            # Look for secondary structure file
            ss_files = list(sim_dir.glob(ss_file))
            
            if not ss_files:
                logger.warning(f"No secondary structure file found in {sim_dir}")
                continue
            
            # Use the first matching file
            ss_file_path = ss_files[0]
            
            # Read specific lines from the summary file
            ss_features = {}
            
            with open(ss_file_path, 'r') as f:
                lines = f.readlines()
                
                # Process specific lines containing secondary structure info
                # Adapt these line numbers based on your specific format
                if len(lines) >= 30:
                    # Example: line 30 contains percentages of different SS types
                    ss_line = lines[29].strip().split()
                    if len(ss_line) >= 8:
                        ss_features['helix_percent'] = float(ss_line[0])
                        ss_features['sheet_percent'] = float(ss_line[1])
                        ss_features['coil_percent'] = float(ss_line[2])
                        ss_features['turn_percent'] = float(ss_line[3])
                        ss_features['bridge_percent'] = float(ss_line[4])
                        ss_features['bend_percent'] = float(ss_line[5])
                        ss_features['other_percent'] = float(ss_line[6])
                
                # Get isoelectric point if available
                if len(lines) >= 40:
                    ip_line = lines[39].strip().split()
                    if len(ip_line) >= 18:
                        ss_features['isoelectric_point'] = float(ip_line[17])
            
            # Create DataFrame for this simulation
            if ss_features:
                df = pd.DataFrame([ss_features], index=[sim_dir.name])
                feature_dfs.append(df)
            else:
                logger.warning(f"No secondary structure features extracted for {sim_dir}")
        
        except Exception as e:
            logger.error(f"Error processing {sim_dir}: {str(e)}")
    
    # Combine all simulation data
    if feature_dfs:
        ss_features = pd.concat(feature_dfs)
        logger.info(f"Extracted secondary structure features with shape {ss_features.shape}")
        return ss_features
    else:
        logger.warning("No secondary structure features could be extracted")
        return None

def load_target_values(target_file):
    """
    Load target values (e.g., DELTA30) from a file.
    
    Parameters
    ----------
    target_file : str
        Path to file containing target values
    
    Returns
    -------
    pandas.DataFrame
        DataFrame containing target values
    """
    logger.info(f"Loading target values from {target_file}")
    
    try:
        # Try to load the file
        df = pd.read_csv(target_file, index_col=0)
        logger.info(f"Loaded target values with shape {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Failed to load target values from {target_file}: {str(e)}")
        return None

def extract_all_features(md_dir, output_file, params):
    """
    Extract all features from MD simulation results.
    
    Parameters
    ----------
    md_dir : str
        Directory containing MD simulation results
    output_file : str
        Path to output file for saving features
    params : dict
        Parameters for feature extraction
    
    Returns
    -------
    str
        Path to output file
    """
    logger.info(f"Extracting all features from {md_dir}")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Extract different types of features
    feature_sets = {}
    
    # Extract pocket features if enabled
    if params.get('pocket_analysis', {}).get('enabled', True):
        pocket_features = extract_pocket_features(md_dir, params.get('pocket_analysis', {}))
        if pocket_features is not None:
            feature_sets['pocket'] = pocket_features
    
    # Extract MD features if enabled
    if params.get('dynamic_features', {}).get('enabled', True):
        md_features = extract_md_features(md_dir, params.get('dynamic_features', {}))
        if md_features is not None:
            feature_sets['md'] = md_features
    
    # Extract sequence features if enabled
    if params.get('sequence_features', {}).get('enabled', True):
        seq_features = extract_sequence_features(md_dir, params.get('sequence_features', {}))
        if seq_features is not None:
            feature_sets['sequence'] = seq_features
    
    # Extract secondary structure features if enabled
    if params.get('secondary_structure', {}).get('enabled', True):
        ss_features = extract_secondary_structure(md_dir, params.get('secondary_structure', {}))
        if ss_features is not None:
            feature_sets['ss'] = ss_features
    
    # Merge all feature sets
    all_features = None
    simulations = set()
    
    # Collect all simulation ids
    for feature_type, features in feature_sets.items():
        simulations.update(features.index)
    
    # Create a DataFrame with all simulations as index
    all_features = pd.DataFrame(index=sorted(simulations))
    
    # Add features from each feature set
    for feature_type, features in feature_sets.items():
        # Merge on index (simulation id)
        all_features = all_features.join(features, how='left')
    
    # Load target values if specified
    target_file = params.get('target_file')
    if target_file:
        target_values = load_target_values(target_file)
        if target_values is not None:
            # Merge target values
            all_features = all_features.join(target_values, how='left')
    
    # Fill missing values if any
    if params.get('fill_missing', True):
        all_features = all_features.fillna(all_features.mean())
    
    # Save features to file
    all_features.to_csv(output_file)
    logger.info(f"Saved all features to {output_file}")
    
    return output_file

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract features from MD simulation results')
    parser.add_argument('--md-dir', type=str, required=True,
                      help='Directory containing MD simulation results')
    parser.add_argument('--output', type=str, default='data/processed/features.csv',
                      help='Output file for saving features')
    parser.add_argument('--config', type=str, default='config/default.yml',
                      help='Configuration file')
    args = parser.parse_args()
    
    # Load configuration
    import yaml
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        params = config.get('feature_extraction', {})
    except Exception as e:
        logger.warning(f"Failed to load configuration from {args.config}: {str(e)}")
        logger.warning("Using default parameters")
        params = {}
    
    # Extract features
    extract_all_features(args.md_dir, args.output, params)

if __name__ == "__main__":
    main() 