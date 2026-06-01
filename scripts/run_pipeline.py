#!/usr/bin/env python3
"""
Full pipeline script for ProMut-MD that orchestrates the entire workflow from
MD simulations to model training and evaluation.
"""

import os
import sys
import argparse
import yaml
import logging
from datetime import datetime
from pathlib import Path

# Add src to path for importing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("promut_md_pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run the ProMut-MD pipeline')
    parser.add_argument('--config', type=str, default='config/default.yml',
                      help='Path to configuration file')
    parser.add_argument('--skip-md', action='store_true',
                      help='Skip MD simulation step (use existing data)')
    parser.add_argument('--skip-features', action='store_true',
                      help='Skip feature extraction step (use existing features)')
    parser.add_argument('--skip-training', action='store_true',
                      help='Skip model training step')
    parser.add_argument('--skip-evaluation', action='store_true',
                      help='Skip model evaluation step')
    parser.add_argument('--skip-visualization', action='store_true',
                      help='Skip visualization generation')
    parser.add_argument('--output-dir', type=str,
                      help='Override output directory from config')
    return parser.parse_args()

def load_config(config_path):
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def run_md_simulations(config):
    """Run molecular dynamics simulations"""
    logger.info("Starting MD simulations")
    # Import here to avoid dependencies for users who skip this step
    from scripts.md_simulations.run_md import run_simulations

    # Create timestamp for output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(config['paths']['data']['processed'], f"md_results_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    # Run simulations
    run_simulations(
        input_dir=config['paths']['data']['raw'],
        output_dir=output_dir,
        params=config['md_simulation']
    )

    logger.info(f"MD simulations completed. Results saved to {output_dir}")
    return output_dir

def run_feature_extraction(config, md_results_dir):
    """Extract features from MD simulation results"""
    logger.info("Starting feature extraction")
    # Import here to avoid dependencies for users who skip this step
    from scripts.feature_extraction.extract_features import extract_all_features

    # Create timestamp for output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(config['paths']['data']['processed'], f"features_{timestamp}.csv")

    # Extract features
    extract_all_features(
        md_dir=md_results_dir,
        output_file=output_file,
        params=config['feature_extraction']
    )

    logger.info(f"Feature extraction completed. Results saved to {output_file}")
    return output_file

def main():
    """Main pipeline function"""
    # Parse arguments and load config
    args = parse_arguments()
    config = load_config(args.config)

    # Override output directory if specified
    if args.output_dir:
        for key in config['paths']['data']:
            config['paths']['data'][key] = os.path.join(args.output_dir, key)
        config['paths']['figures'] = os.path.join(args.output_dir, 'figures')
        config['paths']['models'] = os.path.join(args.output_dir, 'models')

    # Create output directories
    for path in config['paths']['data'].values():
        os.makedirs(path, exist_ok=True)
    os.makedirs(config['paths']['figures'], exist_ok=True)
    os.makedirs(config['paths']['models'], exist_ok=True)

    md_results_dir = None
    features_file = None
    model_file = None
    results_file = None

    # Step 1: Run MD simulations, only when feature extraction needs MD output.
    if not args.skip_md:
        md_results_dir = run_md_simulations(config)
    elif not args.skip_features:
        logger.info("Skipping MD simulations")
        # Use most recent directory in processed data
        md_dirs = [d for d in os.listdir(config['paths']['data']['processed'])
                 if d.startswith('md_results_') and os.path.isdir(
                     os.path.join(config['paths']['data']['processed'], d))]
        if not md_dirs:
            logger.error("No MD simulation results found. Cannot proceed.")
            sys.exit(1)
        md_results_dir = os.path.join(config['paths']['data']['processed'],
                                     sorted(md_dirs)[-1])  # Most recent
    else:
        logger.info("Skipping MD simulations")

    # Step 2: Extract features
    if not args.skip_features:
        features_file = run_feature_extraction(config, md_results_dir)
    else:
        logger.info("Skipping feature extraction")
        if not (args.skip_training and args.skip_evaluation and args.skip_visualization):
            # Use most recent features file in processed data
            feature_files = [f for f in os.listdir(config['paths']['data']['processed'])
                           if f.startswith('features_') and f.endswith('.csv')]
            if not feature_files:
                logger.error("No feature files found. Cannot proceed.")
                sys.exit(1)
            features_file = os.path.join(config['paths']['data']['processed'],
                                       sorted(feature_files)[-1])  # Most recent

    # Step 3: Train model
    if not args.skip_training:
        from src.models.train_model import train_model

        logger.info("Starting model training")
        model_file = train_model(
            features_file=features_file,
            output_dir=config['paths']['models'],
            params=config['model']
        )
    else:
        logger.info("Skipping model training")
        if not (args.skip_evaluation and args.skip_visualization):
            # Use most recent model file in models directory
            model_files = [f for f in os.listdir(config['paths']['models'])
                         if f.endswith('.pkl')]
            if not model_files:
                logger.error("No model files found. Cannot proceed with evaluation or visualization.")
                model_file = None
            else:
                model_file = os.path.join(config['paths']['models'],
                                        sorted(model_files)[-1])  # Most recent

    # Step 4: Evaluate model
    if not args.skip_evaluation and model_file:
        from src.models.evaluate_model import evaluate_model

        logger.info("Starting model evaluation")
        results_file = evaluate_model(
            model_file=model_file,
            features_file=features_file,
            output_dir=config['paths']['data']['results'],
            params=config['model']
        )
    else:
        logger.info("Skipping model evaluation")

    # Step 5: Generate visualizations
    if not args.skip_visualization:
        from src.visualization.visualize import generate_visualizations

        logger.info("Generating visualizations")
        generate_visualizations(
            features_file=features_file,
            model_file=model_file if not args.skip_training else None,
            results_file=results_file if not args.skip_evaluation else None,
            output_dir=config['paths']['figures'],
            params=config['visualization']
        )
    else:
        logger.info("Skipping visualization generation")

    logger.info("Pipeline completed successfully")

if __name__ == "__main__":
    main()
