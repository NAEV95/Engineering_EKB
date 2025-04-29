@echo off
SETLOCAL

REM Check if Python is installed and in PATH
where python >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in your PATH.
    echo Please install Python and make sure it's in your PATH.
    exit /b 1
)

REM Set default Excel file location
SET EXCEL_FILE=data\raw\mutation_data.xlsx
SET OUTPUT_DIR=data\processed
SET CONFIG_FILE=config\excel_workflow.yml

REM Check if an Excel file was specified as argument
IF NOT "%~1"=="" (
    SET EXCEL_FILE=%~1
)

REM Create directories if they don't exist
IF NOT EXIST data\raw mkdir data\raw
IF NOT EXIST data\processed mkdir data\processed
IF NOT EXIST data\results mkdir data\results
IF NOT EXIST config mkdir config
IF NOT EXIST figures mkdir figures

REM Check if the Excel file exists
IF NOT EXIST "%EXCEL_FILE%" (
    echo ERROR: Excel file not found: %EXCEL_FILE%
    echo Place your Excel file in the data\raw directory or specify the path as an argument.
    echo Example: run_workflow.bat path\to\your\excel_file.xlsx
    exit /b 1
)

REM Create a basic config file if it doesn't exist
IF NOT EXIST "%CONFIG_FILE%" (
    echo Creating default configuration file...
    echo # ProMut-MD Configuration > "%CONFIG_FILE%"
    echo parameters: >> "%CONFIG_FILE%"
    echo   sample_size: 100 >> "%CONFIG_FILE%"
    echo   threshold: 0.5 >> "%CONFIG_FILE%"
)

echo ==============================================
echo  ProMut-MD Workflow
echo ==============================================
echo Input Excel file: %EXCEL_FILE%
echo Output directory: %OUTPUT_DIR%
echo Config file: %CONFIG_FILE%
echo.
echo Starting workflow...
echo.

REM Execute the Python script
python scripts\excel_workflow.py --excel "%EXCEL_FILE%" --output-dir "%OUTPUT_DIR%" --config "%CONFIG_FILE%"

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Workflow failed with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
) ELSE (
    echo.
    echo Workflow completed successfully!
    echo Results are available in:
    echo - Processed data: %OUTPUT_DIR%
    echo - Results: data\results
    echo - Figures: figures
)

ENDLOCAL

REM Ask if cleanup should be performed
set /p CLEANUP=Would you like to clean up old files? (Y/N): 

if /i "%CLEANUP%"=="Y" (
    echo.
    echo ------------------------------------------------------
    echo Cleaning up old files (dry run)...
    echo ------------------------------------------------------
    
    REM First run in dry-run mode to show what would be deleted
    python scripts/cleanup.py --clean-all --dry-run --days 30 --keep 2
    
    echo.
    set /p CONFIRM=Proceed with deletion? (Y/N): 
    
    if /i "%CONFIRM%"=="Y" (
        echo.
        echo ------------------------------------------------------
        echo Performing actual cleanup...
        echo ------------------------------------------------------
        python scripts/cleanup.py --clean-all --days 30 --keep 2
    ) else (
        echo Cleanup cancelled.
    )
)

echo.
echo All operations completed.
echo. 