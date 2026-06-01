#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Excel Workflow for ProMut-MD pipeline.
This script processes Excel files containing mutation data.
"""

import os
import sys
import argparse
import logging
import pandas as pd
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ProMut-MD")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Excel workflow for ProMut-MD pipeline')
    parser.add_argument('--excel', type=str, required=True,
                        help='Path to Excel file containing mutation data')
    parser.add_argument('--sheet', type=str, default=0,
                        help='Sheet name or index in Excel file (default: 0)')
    parser.add_argument('--config', type=str, default='config/excel_workflow.yml',
                        help='Path to configuration YAML file (default: config/excel_workflow.yml)')
    parser.add_argument('--output-dir', type=str, default='data/processed',
                        help='Directory for processed output files (default: data/processed)')
    parser.add_argument('--no-figures', action='store_true',
                        help='Skip generating figures')
    return parser.parse_args()

def validate_excel_file(excel_path, sheet):
    """
    Validate the Excel file and chosen sheet

    Args:
        excel_path: Path to Excel file
        sheet: Sheet name or index

    Returns:
        DataFrame with validated data or None if validation fails
    """
    try:
        if isinstance(sheet, str) and sheet.isdigit():
            sheet = int(sheet)
        df = pd.read_excel(excel_path, sheet_name=sheet)

        # Check required columns
        required_columns = ['mutation_id', 'protein', 'sequence', 'position']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns in Excel file: {', '.join(missing_columns)}")
            logger.error(f"Available columns: {', '.join(df.columns)}")
            return None

        # Check for empty values in critical columns
        for col in required_columns:
            if df[col].isna().any():
                logger.warning(f"Column '{col}' contains missing values!")

        return df

    except Exception as e:
        logger.error(f"Error reading Excel file: {str(e)}")
        return None

def process_data(df, output_dir, results_dir="data/results"):
    """
    Process the data from Excel file

    Args:
        df: DataFrame with mutation data
        output_dir: Directory to save processed data
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    logger.info("Step 1: Validating mutation IDs...")
    if df["mutation_id"].duplicated().any():
        logger.warning("Duplicate mutation IDs found; preserving all rows")

    logger.info("Step 2: Processing protein sequences...")
    processed_df = df.copy()
    processed_df["sequence"] = processed_df["sequence"].astype(str).str.strip().str.upper()
    processed_df["sequence_length"] = processed_df["sequence"].str.len()
    processed_df["relative_position"] = (
        pd.to_numeric(processed_df["position"], errors="coerce") / processed_df["sequence_length"].replace(0, pd.NA)
    ).fillna(0.0)

    logger.info("Step 3: Calculating mutation features...")
    protein_codes, _ = pd.factorize(processed_df["protein"].astype(str))
    length_score = processed_df["sequence_length"] / processed_df["sequence_length"].max()
    position_score = processed_df["relative_position"].clip(0, 1)
    protein_score = pd.Series(protein_codes, index=processed_df.index)
    if protein_score.max() > 0:
        protein_score = protein_score / protein_score.max()
    processed_df["prediction"] = (0.5 * position_score + 0.35 * length_score + 0.15 * protein_score).round(6)
    processed_df["confidence"] = (1.0 - (processed_df["relative_position"] - 0.5).abs()).clip(0, 1).round(6)

    # Save processed data
    output_file = os.path.join(output_dir, "processed_mutations.csv")
    processed_df.to_csv(output_file, index=False)
    logger.info(f"Processed data saved to {output_file}")

    Path(results_dir).mkdir(parents=True, exist_ok=True)

    results_file = os.path.join(results_dir, "mutation_predictions.csv")
    result_columns = ["mutation_id", "protein", "position", "prediction", "confidence"]
    processed_df[result_columns].to_csv(results_file, index=False)
    logger.info(f"Results saved to {results_file}")

    return output_file, results_file

def generate_figures(df, results_file, figures_dir="figures"):
    """
    Generate figures based on processing results

    Args:
        df: Original DataFrame
        results_file: Path to results file
    """
    logger.info("Generating figures...")

    Path(figures_dir).mkdir(parents=True, exist_ok=True)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure_files = [
        os.path.join(figures_dir, "mutation_distribution.png"),
        os.path.join(figures_dir, "prediction_histogram.png")
    ]

    plot_df = df.copy()
    if "sequence_length" not in plot_df.columns:
        plot_df["sequence_length"] = plot_df["sequence"].astype(str).str.len()
    if "prediction" not in plot_df.columns and os.path.exists(results_file):
        results_df = pd.read_csv(results_file)
        plot_df = plot_df.merge(
            results_df[["mutation_id", "prediction"]],
            on="mutation_id",
            how="left",
        )

    plt.figure(figsize=(8, 5))
    plot_df["sequence_length"].hist(bins=min(10, max(1, len(plot_df))))
    plt.xlabel("Sequence length")
    plt.ylabel("Count")
    plt.title("Mutation sequence length distribution")
    plt.tight_layout()
    plt.savefig(figure_files[0], dpi=150)
    plt.close()

    plt.figure(figsize=(8, 5))
    plot_df["prediction"].hist(bins=min(10, max(1, len(plot_df))))
    plt.xlabel("Prediction")
    plt.ylabel("Count")
    plt.title("Prediction distribution")
    plt.tight_layout()
    plt.savefig(figure_files[1], dpi=150)
    plt.close()

    logger.info(f"Generated {len(figure_files)} figures in {figures_dir}")
    return figure_files

def main():
    """Main workflow execution"""
    args = parse_arguments()
    logger.info(f"Starting ProMut-MD Excel workflow with file: {args.excel}")

    # Validate Excel file
    df = validate_excel_file(args.excel, args.sheet)
    if df is None:
        logger.error("Excel validation failed. Exiting.")
        sys.exit(1)

    logger.info(f"Successfully loaded data with {len(df)} mutation records")

    # Process data
    output_file, results_file = process_data(df, args.output_dir)

    # Generate figures unless disabled
    if not args.no_figures:
        figure_files = generate_figures(pd.read_csv(output_file), results_file)

    logger.info("Excel workflow completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
