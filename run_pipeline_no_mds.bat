@echo off
REM Batch file to run the pipeline without MDS calculation and with advanced model optimization

echo Checking for virtual environment...
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo No virtual environment found. Make sure to install dependencies manually.
    echo Required: pandas numpy scikit-learn matplotlib seaborn lightgbm shap pyyaml openpyxl optuna
)

echo.
echo Running enhanced pipeline with:
echo  - Feature subset comparison (7 different feature combinations)
echo  - Advanced Optuna hyperparameter optimization
echo  - Comparative analysis and visualization
echo.
echo This may take some time as multiple models will be trained and optimized.
echo.
echo Quick run options:
echo  - For faster results: python run_pipeline_no_mds.py --data-dir "data" --output-dir "output" --optuna-trials 10
echo  - To skip optimization: python run_pipeline_no_mds.py --data-dir "data" --output-dir "output" --skip-optuna
echo.

python run_pipeline_no_mds.py --data-dir "data" --output-dir "output" --optuna-trials 50

echo.
if %ERRORLEVEL% NEQ 0 (
    echo Pipeline execution failed. Check the logs for details.
) else (
    echo Pipeline completed successfully! Results saved in output directory.
    echo.
    echo Outputs include:
    echo - Optimized models for each feature subset
    echo - Feature subset comparison to identify best predictors
    echo - Comprehensive visualizations and performance metrics
    echo - Detailed breakdown of feature importance
)
echo.
pause 