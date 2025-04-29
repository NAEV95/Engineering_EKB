# ProMut-MD: Protein Mutation Effect Prediction using MD Simulations

## Project Description

ProMut-MD is a computational biology pipeline for predicting the effects of mutations on protein function using molecular dynamics (MD) simulations and machine learning. The workflow integrates structural dynamics data with sequence features to build predictive models for mutation impact assessment.

### Overview

This project consists of three main steps:

1. **Molecular Dynamics Simulations**: Simulates protein dynamics to capture conformational changes induced by mutations.
   - Uses GROMACS for performing the MD simulations
   - Analyzes protein stability, flexibility, and structural changes

2. **Feature Extraction**: Extracts relevant features from MD trajectories and protein sequences:
   - Pocket descriptors (volume, hydrophobicity, etc.)
   - Dynamic properties (RMSD, RMSF, Radius of Gyration)
   - Secondary structure compositions
   - Sequence-based features (amino acid properties)

3. **Machine Learning Models**: Builds predictive models for mutation effect prediction:
   - Uses LightGBM gradient boosting framework
   - Performs feature selection and importance analysis
   - Evaluates model performance with cross-validation
   - Visualizes predictions and feature importance

![Abstract Figure](figures/Abstract_fig.png)

## Repository Structure

```
├── data/                  # Data files and datasets
│   ├── raw/               # Original input data (PDB files, etc.)
│   ├── processed/         # Processed data ready for analysis
│   └── results/           # Results from model training and evaluation
├── figures/               # Generated figures and visualizations
├── notebooks/             # Jupyter notebooks for analysis and visualization
├── scripts/               # Scripts for running simulations and analysis
│   ├── md_simulations/    # Scripts for running MD simulations
│   ├── feature_extraction/# Scripts for extracting features from MD
│   └── utils/             # Utility scripts used across the project
├── src/                   # Source code for the project
│   ├── data/              # Code for data loading and processing
│   ├── features/          # Code for feature engineering
│   ├── models/            # Code for model training and evaluation
│   └── visualization/     # Code for visualization
├── tests/                 # Tests for the codebase
├── config/                # Configuration files
├── environment.yml        # Conda environment file
├── requirements.txt       # Python dependencies
├── setup.py               # Package installation
└── README.md              # Project overview and documentation
```

## Installation

### Prerequisites

- Python 3.8+
- GROMACS 2019.3+
- MDpocket/Fpocket

### Setting up the environment

#### Option 1: Using conda

```bash
# Clone the repository
git clone https://github.com/yourusername/ProMut-MD.git
cd ProMut-MD

# Create and activate conda environment
conda env create -f environment.yml
conda activate promut-md
```

#### Option 2: Using pip

```bash
# Clone the repository
git clone https://github.com/yourusername/ProMut-MD.git
cd ProMut-MD

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Option 3: Using uv (faster)

```bash
# Clone the repository
git clone https://github.com/yourusername/ProMut-MD.git
cd ProMut-MD

# Install uv if you don't have it
pip install uv

# Create and activate virtual environment
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt
```

## Usage

### Complete Pipeline

The complete pipeline can be run using the main script:

```bash
python scripts/run_pipeline.py --config config/default.yml
```

You can customize the execution by skipping specific steps:

```bash
python scripts/run_pipeline.py --skip-md --skip-visualization
```

### Individual Steps

#### 1. Running MD Simulations

```bash
python scripts/md_simulations/run_md.py --input data/raw/protein.pdb --output data/processed/md_results
```

#### 2. Extracting Features

```bash
python scripts/feature_extraction/extract_features.py --md-dir data/processed/md_results --output data/processed/features.csv
```

#### 3. Training Models

```bash
python src/models/train_model.py --features data/processed/features.csv --output-dir models
```

#### 4. Evaluating Models

```bash
python src/models/evaluate_model.py --model models/model_20230101_120000.pkl --features data/processed/features.csv --output-dir data/results
```

#### 5. Generating Visualizations

```bash
python src/visualization/visualize.py --features data/processed/features.csv --model models/model_20230101_120000.pkl --results data/results/evaluation_20230101_120000.json --output-dir figures
```

## Running Without MDS

For users who want to skip the computationally intensive Molecular Dynamics Simulations (MDS), we provide an alternative workflow using pre-computed features from the `new_df_66.xlsx` dataset.

### Quick Start Without MDS

```bash
python run_pipeline_no_mds.py --data-dir data --output-dir output
```

This script:
1. Uses the pre-computed `new_df_66.xlsx` file directly
2. Skips the MD simulation step
3. Proceeds with feature processing, model training, evaluation, and visualization

### Testing Results

We've successfully tested this workflow with the following results:
- MAE: 0.856
- RMSE: 1.241
- R²: 0.446

The model achieves good performance even without running new MD simulations, making it suitable for quick prototyping or when computational resources are limited.

#### Required Dependencies

To run the pipeline without MDS, you'll need to install:
```bash
uv pip install pandas numpy scikit-learn matplotlib seaborn lightgbm shap pyyaml openpyxl
```

For detailed instructions on running the pipeline without MDS, see the `README_no_mds.md` file.

## Configuration

The behavior of the pipeline can be customized by editing the configuration files in the `config/` directory:

- `default.yml`: Default configuration for all components
- Custom configurations can be created for specific experiments

Example configuration options:

```yaml
# Feature extraction parameters
feature_extraction:
  pocket_analysis:
    enabled: true
    tool: "mdpocket"
  dynamic_features:
    enabled: true
    rmsd:
      enabled: true
  # ... more options
```

## Example Results

The pipeline generates various outputs:

1. Processed MD data in `data/processed/`
2. Extracted features in CSV format
3. Trained models saved as pickle files
4. Evaluation metrics in JSON format
5. Visualizations in the `figures/` directory:
   - Feature importance plots
   - SHAP summary plots
   - Prediction scatter plots
   - Performance metrics by data range

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

To contribute:
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Citation

If you use this code in your research, please cite:

```
@article{doi:10.1021/acs.jcim.3c00999,
author = {Venanzi, Niccolo Alberto Elia and Basciu, Andrea and Vargiu, Attilio Vittorio and Kiparissides, Alexandros and Dalby, Paul A. and Dikicioglu, Duygu},
title = {Machine Learning Integrating Protein Structure, Sequence, and Dynamics to Predict the Enzyme Activity of Bovine Enterokinase Variants},
journal = {Journal of Chemical Information and Modeling},
volume = {64},
number = {7},
pages = {2681-2694},
year = {2024},
doi = {10.1021/acs.jcim.3c00999},
    note ={PMID: 38386417},
URL = { 
        https://doi.org/10.1021/acs.jcim.3c00999
},
eprint = {  
        https://doi.org/10.1021/acs.jcim.3c00999
}
}
```


## Contact

For questions or support, please contact [your.email@example.com](mailto:venanzi.nae@gmail.com)

