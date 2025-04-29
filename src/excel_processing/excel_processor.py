from typing import Dict, Any, List, Optional, Union, Tuple
import os
import logging
import pandas as pd
from datetime import datetime

from .config_loader import ConfigLoader
from .excel_reader import ExcelReader


class ExcelProcessor:
    """
    Main class for processing Excel files according to configuration settings.
    Combines the functionality of ConfigLoader and ExcelReader.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the Excel processor with a configuration file.
        
        Args:
            config_path: Path to the configuration file (JSON or YAML)
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration file has invalid format
        """
        self.config_loader = ConfigLoader(config_path)
        self.excel_reader = ExcelReader(self.config_loader.get_column_mapping())
        self.logger = logging.getLogger(__name__)
        
    def process_file(self, 
                     input_file: str, 
                     output_file: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Process an Excel file according to the configuration.
        
        Args:
            input_file: Path to the input Excel file
            output_file: Optional path for the output file
            
        Returns:
            Dictionary of processed DataFrames
            
        Raises:
            FileNotFoundError: If the input file doesn't exist
            ValueError: If there's an error processing the file
        """
        try:
            self.logger.info(f"Processing Excel file: {input_file}")
            
            # Get processing options from config
            sheet_name = self.config_loader.get_processing_option('sheet_name', 0)
            skiprows = self.config_loader.get_processing_option('skiprows', None)
            usecols = self.config_loader.get_processing_option('usecols', None)
            
            # Read the Excel file
            excel_data = self.excel_reader.read_excel(
                input_file,
                sheet_name=sheet_name,
                skiprows=skiprows,
                usecols=usecols
            )
            
            # Process each sheet
            processed_data = {}
            for sheet_name, df in excel_data.items():
                processed_df = self._process_sheet(df, sheet_name)
                processed_data[sheet_name] = processed_df
            
            # Export to Excel if output file is specified
            if output_file:
                include_timestamp = self.config_loader.get_output_setting('include_timestamp', True)
                self.excel_reader.export_to_excel(processed_data, output_file, include_timestamp)
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error processing Excel file: {str(e)}")
            raise ValueError(f"Failed to process Excel file: {str(e)}")
    
    def _process_sheet(self, df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
        """
        Process a single sheet according to the configuration.
        
        Args:
            df: DataFrame to process
            sheet_name: Name of the sheet being processed
            
        Returns:
            Processed DataFrame
        """
        # Apply filters if configured
        filters = self.config_loader.get_filter_criteria()
        if filters:
            self.logger.debug(f"Applying {len(filters)} filters to sheet '{sheet_name}'")
            df = self.excel_reader.filter_data(df, filters)
        
        # Validate data if validation rules are configured
        validation_rules = self.config_loader.get_processing_option('validation_rules', [])
        if validation_rules:
            self.logger.debug(f"Validating data in sheet '{sheet_name}'")
            is_valid, error_messages = self.excel_reader.validate_data(df, validation_rules)
            
            if not is_valid:
                for error in error_messages:
                    self.logger.warning(f"Validation error in sheet '{sheet_name}': {error}")
                
                # Check if validation failure should stop processing
                strict_validation = self.config_loader.get_processing_option('strict_validation', False)
                if strict_validation:
                    raise ValueError(f"Validation failed for sheet '{sheet_name}': {error_messages[0]}")
        
        # Apply transformations
        df = self._apply_transformations(df, sheet_name)
        
        return df
    
    def _apply_transformations(self, df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
        """
        Apply transformations to a DataFrame based on configuration.
        
        Args:
            df: DataFrame to transform
            sheet_name: Name of the sheet being processed
            
        Returns:
            Transformed DataFrame
        """
        transformations = self.config_loader.get_processing_option('transformations', [])
        result_df = df.copy()
        
        for transform in transformations:
            operation = transform.get('operation')
            
            try:
                if operation == 'drop_columns':
                    columns = transform.get('columns', [])
                    result_df = result_df.drop(columns=[c for c in columns if c in result_df.columns], 
                                               errors='ignore')
                    
                elif operation == 'fill_na':
                    column = transform.get('column')
                    value = transform.get('value')
                    if column in result_df.columns:
                        result_df[column] = result_df[column].fillna(value)
                        
                elif operation == 'convert_type':
                    column = transform.get('column')
                    dtype = transform.get('type')
                    if column in result_df.columns:
                        try:
                            result_df[column] = result_df[column].astype(dtype)
                        except (ValueError, TypeError) as e:
                            self.logger.warning(f"Type conversion failed for column '{column}': {str(e)}")
                
                elif operation == 'rename_columns':
                    mapping = transform.get('mapping', {})
                    result_df = result_df.rename(columns=mapping)
                
                elif operation == 'sort':
                    columns = transform.get('columns', [])
                    ascending = transform.get('ascending', True)
                    if all(col in result_df.columns for col in columns):
                        result_df = result_df.sort_values(by=columns, ascending=ascending)
                
                elif operation == 'drop_duplicates':
                    columns = transform.get('columns', None)
                    keep = transform.get('keep', 'first')
                    result_df = result_df.drop_duplicates(subset=columns, keep=keep)
                    
                elif operation == 'add_calculated_column':
                    column = transform.get('column')
                    expression = transform.get('expression')
                    if expression:
                        # This is using eval which can be dangerous
                        # In a production environment, you'd want a safer alternative
                        result_df[column] = result_df.eval(expression)
                        
                elif operation == 'filter_rows':
                    condition = transform.get('condition')
                    if condition:
                        # This is using eval which can be dangerous
                        # In a production environment, you'd want a safer alternative
                        mask = result_df.eval(condition)
                        result_df = result_df[mask]
                
            except Exception as e:
                self.logger.warning(f"Error applying transformation '{operation}' in sheet '{sheet_name}': {str(e)}")
                
        return result_df
    
    def batch_process(self, 
                     input_directory: str, 
                     output_directory: str,
                     file_pattern: str = "*.xlsx") -> List[str]:
        """
        Process multiple Excel files in a directory.
        
        Args:
            input_directory: Directory containing input files
            output_directory: Directory for output files
            file_pattern: File pattern to match (e.g., "*.xlsx")
            
        Returns:
            List of paths to processed output files
        """
        import glob
        
        if not os.path.exists(input_directory):
            raise FileNotFoundError(f"Input directory not found: {input_directory}")
            
        # Create output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)
        
        # Find all matching files
        input_files = glob.glob(os.path.join(input_directory, file_pattern))
        
        if not input_files:
            self.logger.warning(f"No files matching pattern '{file_pattern}' found in {input_directory}")
            return []
            
        self.logger.info(f"Found {len(input_files)} files to process")
        
        output_files = []
        for input_file in input_files:
            try:
                file_name = os.path.basename(input_file)
                output_file = os.path.join(output_directory, file_name)
                
                self.process_file(input_file, output_file)
                output_files.append(output_file)
                
            except Exception as e:
                self.logger.error(f"Error processing file {input_file}: {str(e)}")
                
        return output_files
    
    def summarize_data(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Generate a summary of the processed data.
        
        Args:
            data: Dictionary of processed DataFrames
            
        Returns:
            Dictionary with summary information
        """
        summary = {
            "processed_time": datetime.now().isoformat(),
            "sheets": {},
            "total_rows": 0,
            "total_sheets": len(data)
        }
        
        for sheet_name, df in data.items():
            sheet_summary = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns)
            }
            
            # Add numeric column statistics if configured
            include_stats = self.config_loader.get_output_setting('include_summary_stats', False)
            if include_stats:
                numeric_columns = df.select_dtypes(include=['number']).columns
                if not numeric_columns.empty:
                    sheet_summary["statistics"] = {}
                    for col in numeric_columns:
                        sheet_summary["statistics"][col] = {
                            "min": df[col].min(),
                            "max": df[col].max(),
                            "mean": df[col].mean(),
                            "median": df[col].median()
                        }
            
            summary["sheets"][sheet_name] = sheet_summary
            summary["total_rows"] += sheet_summary["row_count"]
            
        return summary 