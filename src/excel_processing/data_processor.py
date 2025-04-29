from typing import Dict, Any, List, Optional
import pandas as pd
import logging

from src.excel_processing.config_loader import ConfigLoader
from src.excel_processing.excel_reader import ExcelReader


class DataProcessor:
    """
    Class for processing Excel data based on configuration settings.
    """
    
    def __init__(self, config_loader: ConfigLoader):
        """
        Initialize the data processor with configuration settings.
        
        Args:
            config_loader: Initialized ConfigLoader object
        """
        self.config = config_loader
        self.logger = logging.getLogger(__name__)
        
    def process_workflow(self, excel_file_path: str) -> Dict[str, pd.DataFrame]:
        """
        Execute the complete data processing workflow.
        
        Args:
            excel_file_path: Path to the Excel file to process
            
        Returns:
            Dictionary of processed DataFrames with keys for each processing stage
        """
        try:
            # Initialize Excel reader
            excel_reader = ExcelReader(excel_file_path)
            
            # Get configuration settings
            column_mapping = self.config.get_column_mapping()
            filter_criteria = self.config.get_filter_criteria()
            processing_options = self.config.get_processing_options()
            
            # Read the Excel file
            sheet_name = processing_options.get('sheet_name', 0)
            raw_data = excel_reader.read_sheet(sheet_name=sheet_name, column_mapping=column_mapping)
            
            # Filter data if criteria specified
            filtered_data = raw_data
            if filter_criteria:
                filtered_data = excel_reader.filter_data(raw_data, filter_criteria)
                
            # Apply transformations
            transformations = processing_options.get('transformations', [])
            processed_data = excel_reader.apply_transformations(filtered_data, transformations)
            
            # Return all stages of processing
            return {
                'raw_data': raw_data,
                'filtered_data': filtered_data,
                'processed_data': processed_data
            }
            
        except Exception as e:
            self.logger.error(f"Error processing workflow: {str(e)}")
            raise
    
    def get_summary_statistics(self, data: pd.DataFrame, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Calculate summary statistics for the specified columns.
        
        Args:
            data: DataFrame to analyze
            columns: Optional list of columns to include (all numeric columns if None)
            
        Returns:
            DataFrame with summary statistics
        """
        # If no columns specified, use all numeric columns
        if columns is None:
            columns = data.select_dtypes(include=['number']).columns.tolist()
        else:
            # Filter to include only columns that exist and are numeric
            columns = [col for col in columns if col in data.columns 
                      and pd.api.types.is_numeric_dtype(data[col])]
            
        if not columns:
            return pd.DataFrame()
            
        # Calculate statistics
        return data[columns].describe()
    
    def process_and_aggregate(self, excel_file_path: str, 
                             group_by_columns: List[str],
                             agg_functions: Dict[str, str]) -> pd.DataFrame:
        """
        Process data and perform aggregation by group.
        
        Args:
            excel_file_path: Path to the Excel file
            group_by_columns: Columns to group by
            agg_functions: Dictionary of column:aggregation_function pairs
            
        Returns:
            Aggregated DataFrame
        """
        # Process the data
        data_dict = self.process_workflow(excel_file_path)
        processed_data = data_dict['processed_data']
        
        # Check if all groupby columns exist
        valid_group_cols = [col for col in group_by_columns if col in processed_data.columns]
        if not valid_group_cols:
            self.logger.warning("No valid groupby columns found")
            return processed_data
        
        # Filter aggregation functions to only include existing columns
        valid_agg = {col: func for col, func in agg_functions.items() 
                    if col in processed_data.columns}
        
        if not valid_agg:
            self.logger.warning("No valid aggregation functions found")
            return processed_data
        
        # Perform groupby and aggregation
        return processed_data.groupby(valid_group_cols).agg(valid_agg).reset_index() 