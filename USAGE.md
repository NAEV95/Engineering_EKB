# ProMut-MD: Quick Start Guide

This guide provides simple instructions for running the ProMut-MD pipeline with Excel files.

## Prerequisites

- Windows operating system
- Python installed and available in PATH
- All dependencies installed (as specified in `requirements.txt` or `environment.yml`)

## Running the Pipeline

### Option 1: Using the Batch File (Simplest)

1. Place your Excel file in the `data/raw` directory
2. Open Command Prompt in the project directory
3. Run the batch file:

```
run_workflow.bat
```

This will use the default Excel file location (`data/raw/mutation_data.xlsx`).

If you want to use a different Excel file, specify the path as an argument:

```
run_workflow.bat path\to\your\file.xlsx
```

The batch file will:
- Verify Python is installed
- Check if the Excel file exists
- Run the full pipeline
- Offer to clean up old files and results after completion

### Option 2: Direct Python Execution

If you prefer to run the Python script directly:

```
python scripts/excel_workflow.py --excel data/raw/mutation_data.xlsx --sheet 0
```

Additional options:
- `--sheet`: Specify the sheet name or index (default: 0)
- `--config`: Specify a custom config file (default: config/excel_workflow.yml)

### Cleaning Up Old Files

To clean up old files without running the workflow:

```
python scripts/cleanup.py --clean-all --days 30 --keep 2
```

Options:
- `--clean-all`: Clean all categories (temp, processed, results, models, figures)
- `--clean-temp`: Clean only temporary files
- `--clean-processed`: Clean only processed data files
- `--clean-results`: Clean only results files
- `--clean-models`: Clean only model files
- `--clean-figures`: Clean only figure files
- `--days`: Keep files newer than specified days (default: 30)
- `--keep`: Keep at least this many newest files (default: 2)
- `--dry-run`: Show what would be deleted without actually deleting

## Output Files

The pipeline generates the following outputs:
- Processed features: `data/processed/`
- Trained models: `models/`
- Evaluation results: `data/results/`
- Visualizations: `figures/` 