import pandas as pd
import numpy as np
from typing import Dict, Any, List, Union, Optional, Tuple
import os
import logging
from datetime import datetime
from openpyxl import load_workbook


class ExcelReader:
    """
    ExcelReader class for reading Excel files and converting them to pandas DataFrames.
    Provides methods for reading sheets, checking for headers, and validating Excel files.
    """
    
    def __init__(self):
        """
        Initialize the ExcelReader.
        """
        self.logger = logging.getLogger(__name__)
    
    def read_excel(self, file_path: str, sheet_name: Optional[Union[str, int, List[Union[str, int]]]] = None,
                  header: Union[int, List[int]] = 0, skip_rows: Optional[List[int]] = None, 
                  usecols: Optional[Union[List[int], str]] = None) -> Dict[str, pd.DataFrame]:
        """
        Read data from an Excel file.
        
        Args:
            file_path: Path to the Excel file
            sheet_name: Sheet name(s) or index(es) to read (None reads all sheets)
            header: Row index(es) to use as column names
            skip_rows: Row indexes to skip
            usecols: Columns to read (list of indices or string range like 'A:C')
            
        Returns:
            Dictionary mapping sheet names to pandas DataFrames
            
        Raises:
            FileNotFoundError: If the Excel file doesn't exist
            ValueError: If the file isn't a valid Excel file or there are issues reading it
        """
        if not os.path.exists(file_path):
            self.logger.error(f"Excel file not found: {file_path}")
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        
        if not file_path.endswith(('.xlsx', '.xls', '.xlsm')):
            self.logger.error(f"Not a valid Excel file: {file_path}")
            raise ValueError(f"Not a valid Excel file: {file_path}. File must have .xlsx, .xls, or .xlsm extension.")
        
        try:
            df_dict = {}
            excel_data = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                header=header,
                skiprows=skip_rows,
                usecols=usecols
            )
            
            # If a single sheet was read, excel_data will be a DataFrame
            # If multiple sheets were read, excel_data will be a dict of DataFrames
            if isinstance(excel_data, pd.DataFrame):
                # Single sheet was read (and sheet_name wasn't None)
                sheet = sheet_name if isinstance(sheet_name, (str, int)) else 'Sheet1'
                df_dict[str(sheet)] = excel_data
            else:
                # Multiple sheets were read
                df_dict = {str(sheet): df for sheet, df in excel_data.items()}
            
            sheet_count = len(df_dict)
            row_count = sum(len(df) for df in df_dict.values())
            self.logger.info(f"Successfully read {row_count} rows from {sheet_count} sheets in {file_path}")
            
            return df_dict
            
        except Exception as e:
            self.logger.error(f"Error reading Excel file {file_path}: {str(e)}")
            raise ValueError(f"Error reading Excel file: {str(e)}")
    
    def read_single_sheet(self, file_path: str, sheet_name: Union[str, int] = 0,
                         header: Union[int, List[int]] = 0, skip_rows: Optional[List[int]] = None,
                         usecols: Optional[Union[List[int], str]] = None) -> pd.DataFrame:
        """
        Read a single sheet from an Excel file.
        
        Args:
            file_path: Path to the Excel file
            sheet_name: Sheet name or index to read
            header: Row index(es) to use as column names
            skip_rows: Row indexes to skip
            usecols: Columns to read (list of indices or string range like 'A:C')
            
        Returns:
            Pandas DataFrame containing the sheet data
            
        Raises:
            ValueError: If the sheet doesn't exist or there are issues reading it
        """
        try:
            result = self.read_excel(
                file_path=file_path,
                sheet_name=sheet_name,
                header=header,
                skip_rows=skip_rows,
                usecols=usecols
            )
            
            # Extract the single sheet
            if isinstance(sheet_name, (str, int)):
                sheet_key = str(sheet_name)
                if sheet_key in result:
                    return result[sheet_key]
                
            # If we get here, we couldn't find the requested sheet
            available_sheets = ', '.join(result.keys())
            self.logger.error(f"Sheet '{sheet_name}' not found in {file_path}. Available sheets: {available_sheets}")
            raise ValueError(f"Sheet '{sheet_name}' not found. Available sheets: {available_sheets}")
            
        except Exception as e:
            if "Sheet '{sheet_name}' not found" in str(e):
                raise
            self.logger.error(f"Error reading sheet '{sheet_name}' from {file_path}: {str(e)}")
            raise ValueError(f"Error reading sheet '{sheet_name}': {str(e)}")
    
    def get_sheet_names(self, file_path: str) -> List[str]:
        """
        Get the list of sheet names from an Excel file.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            List of sheet names
            
        Raises:
            FileNotFoundError: If the Excel file doesn't exist
            ValueError: If there are issues reading the file
        """
        if not os.path.exists(file_path):
            self.logger.error(f"Excel file not found: {file_path}")
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        
        try:
            # Use openpyxl to get sheet names without reading data
            workbook = load_workbook(file_path, read_only=True)
            sheet_names = workbook.sheetnames
            workbook.close()
            return sheet_names
            
        except Exception as e:
            self.logger.error(f"Error getting sheet names from {file_path}: {str(e)}")
            raise ValueError(f"Error getting sheet names: {str(e)}")
    
    def validate_excel_structure(self, file_path: str, required_headers: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Validate that the Excel file has the required headers in specified sheets.
        
        Args:
            file_path: Path to the Excel file
            required_headers: Dictionary mapping sheet names to lists of required column headers
            
        Returns:
            Dictionary mapping sheet names to lists of missing headers
            
        Raises:
            FileNotFoundError: If the Excel file doesn't exist
        """
        if not os.path.exists(file_path):
            self.logger.error(f"Excel file not found: {file_path}")
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        
        # Get all sheet names
        sheet_names = self.get_sheet_names(file_path)
        missing_headers = {}
        
        # Check each required sheet
        for sheet, headers in required_headers.items():
            if sheet not in sheet_names:
                missing_headers[sheet] = headers  # All headers are missing if sheet doesn't exist
                continue
                
            try:
                # Read only the header row
                df = pd.read_excel(file_path, sheet_name=sheet, nrows=1)
                
                # Check which required headers are missing
                sheet_missing = [header for header in headers if header not in df.columns]
                
                if sheet_missing:
                    missing_headers[sheet] = sheet_missing
                    
            except Exception as e:
                self.logger.error(f"Error validating headers in sheet '{sheet}': {str(e)}")
                missing_headers[sheet] = headers  # Consider all headers missing if there's an error
        
        return missing_headers
    
    def check_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Check metadata of the Excel file.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dictionary with file metadata (size, sheet count, etc.)
            
        Raises:
            FileNotFoundError: If the Excel file doesn't exist
        """
        if not os.path.exists(file_path):
            self.logger.error(f"Excel file not found: {file_path}")
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        
        try:
            # Get file size and modification time
            file_stats = os.stat(file_path)
            file_size = file_stats.st_size
            mod_time = pd.Timestamp(file_stats.st_mtime, unit='s')
            
            # Get sheet names and count
            sheet_names = self.get_sheet_names(file_path)
            sheet_count = len(sheet_names)
            
            # Create metadata dictionary
            metadata = {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'last_modified': mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                'sheet_count': sheet_count,
                'sheet_names': sheet_names
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error checking file metadata for {file_path}: {str(e)}")
            raise ValueError(f"Error checking file metadata: {str(e)}")
    
    def preview_sheet(self, file_path: str, sheet_name: Union[str, int] = 0, 
                     rows: int = 5) -> pd.DataFrame:
        """
        Preview the first few rows of a sheet in an Excel file.
        
        Args:
            file_path: Path to the Excel file
            sheet_name: Sheet name or index to preview
            rows: Number of rows to preview
            
        Returns:
            Pandas DataFrame with the first few rows
            
        Raises:
            FileNotFoundError: If the Excel file doesn't exist
            ValueError: If there are issues reading the sheet
        """
        df = self.read_single_sheet(file_path, sheet_name)
        return df.head(rows)
    
    def _apply_column_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply column mapping to standardize column names.
        
        Args:
            df: Input DataFrame with original column names
            
        Returns:
            DataFrame with renamed columns
        """
        # Only rename columns that exist in the dataframe
        valid_mappings = {k: v for k, v in self.column_mapping.items() if k in df.columns}
        
        if valid_mappings:
            df = df.rename(columns=valid_mappings)
            self.logger.debug(f"Applied column mapping: {valid_mappings}")
        
        return df
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean the DataFrame by removing empty rows and columns,
        converting data types, etc.
        
        Args:
            df: Input DataFrame to clean
            
        Returns:
            Cleaned DataFrame
        """
        # Drop rows where all elements are NaN
        df = df.dropna(how='all')
        
        # Drop columns where all elements are NaN
        df = df.dropna(axis=1, how='all')
        
        # Remove leading/trailing whitespace from string columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip() if hasattr(df[col], 'str') else df[col]
        
        # Handle dates: try to convert columns with 'date' in the name to datetime
        date_cols = [col for col in df.columns if 'date' in str(col).lower()]
        for col in date_cols:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except:
                pass  # Ignore if conversion fails
        
        self.logger.debug(f"Cleaned DataFrame: {len(df)} rows remaining")
        return df
    
    def filter_data(self, 
                   df: pd.DataFrame, 
                   filters: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Filter DataFrame based on a list of filter criteria.
        
        Args:
            df: DataFrame to filter
            filters: List of filter criteria dictionaries, e.g.,
                    [{'column': 'age', 'operator': '>', 'value': 18}]
                    
        Returns:
            Filtered DataFrame
        """
        filtered_df = df.copy()
        
        for filter_criteria in filters:
            column = filter_criteria.get('column')
            operator = filter_criteria.get('operator')
            value = filter_criteria.get('value')
            
            if not (column and operator):
                continue
                
            if column not in filtered_df.columns:
                self.logger.warning(f"Filter column '{column}' not found in DataFrame")
                continue
                
            try:
                if operator == '==':
                    filtered_df = filtered_df[filtered_df[column] == value]
                elif operator == '!=':
                    filtered_df = filtered_df[filtered_df[column] != value]
                elif operator == '>':
                    filtered_df = filtered_df[filtered_df[column] > value]
                elif operator == '>=':
                    filtered_df = filtered_df[filtered_df[column] >= value]
                elif operator == '<':
                    filtered_df = filtered_df[filtered_df[column] < value]
                elif operator == '<=':
                    filtered_df = filtered_df[filtered_df[column] <= value]
                elif operator == 'contains':
                    filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(str(value), na=False)]
                elif operator == 'in':
                    if isinstance(value, list):
                        filtered_df = filtered_df[filtered_df[column].isin(value)]
                elif operator == 'not_in':
                    if isinstance(value, list):
                        filtered_df = filtered_df[~filtered_df[column].isin(value)]
                elif operator == 'between':
                    if isinstance(value, list) and len(value) == 2:
                        filtered_df = filtered_df[(filtered_df[column] >= value[0]) & 
                                                  (filtered_df[column] <= value[1])]
            except Exception as e:
                self.logger.warning(f"Error applying filter on column '{column}': {str(e)}")
                
        return filtered_df
    
    def validate_data(self, df: pd.DataFrame, rules: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, bool]:
        """
        Validate a DataFrame against a set of rules.
        
        Args:
            df (pd.DataFrame): The DataFrame to validate.
            rules (List[Dict[str, Any]]): A list of validation rules.
            
        Returns:
            Tuple[pd.DataFrame, bool]: A tuple containing the validated DataFrame and a boolean indicating whether validation passed.
        """
        all_valid = True
        valid_df = df.copy()
        
        for rule in rules:
            column = rule.get('column')
            rule_type = rule.get('type')
            
            if column not in valid_df.columns:
                logging.warning(f"Column {column} not found in DataFrame, skipping validation")
                continue
                
            if rule_type == 'not_empty':
                mask = valid_df[column].isna() | (valid_df[column] == '')
                if mask.any():
                    all_valid = False
                    valid_df.loc[mask, 'validation_error'] = valid_df.get('validation_error', '') + f"{column} cannot be empty; "
                    
            elif rule_type == 'numeric':
                # Try to convert to numeric, mark errors
                mask = pd.to_numeric(valid_df[column], errors='coerce').isna() & ~valid_df[column].isna()
                if mask.any():
                    all_valid = False
                    valid_df.loc[mask, 'validation_error'] = valid_df.get('validation_error', '') + f"{column} must be numeric; "
            
            elif rule_type == 'date':
                # Try to convert to datetime, mark errors
                mask = pd.to_datetime(valid_df[column], errors='coerce').isna() & ~valid_df[column].isna()
                if mask.any():
                    all_valid = False
                    valid_df.loc[mask, 'validation_error'] = valid_df.get('validation_error', '') + f"{column} must be a valid date; "
            
            elif rule_type == 'in_list':
                valid_values = rule.get('valid_values', [])
                mask = ~valid_df[column].isin(valid_values) & ~valid_df[column].isna()
                if mask.any():
                    all_valid = False
                    valid_df.loc[mask, 'validation_error'] = valid_df.get('validation_error', '') + f"{column} must be one of {valid_values}; "
            
            elif rule_type == 'custom':
                # Execute custom validation function
                custom_func = rule.get('function')
                if custom_func and callable(custom_func):
                    result = custom_func(valid_df, column)
                    if isinstance(result, tuple) and len(result) == 2:
                        error_mask, error_message = result
                        if error_mask.any():
                            all_valid = False
                            valid_df.loc[error_mask, 'validation_error'] = valid_df.get('validation_error', '') + error_message
        
        return valid_df, all_valid

    def _apply_column_mapping(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Renames columns according to the provided mapping.
        
        Args:
            df (pd.DataFrame): The DataFrame to rename columns for
            column_mapping (Dict[str, str]): Dictionary mapping from source to target column names
            
        Returns:
            pd.DataFrame: DataFrame with renamed columns
        """
        # Filter the mapping to only include columns that actually exist in the dataframe
        valid_mapping = {src: tgt for src, tgt in column_mapping.items() if src in df.columns}
        
        if not valid_mapping:
            logging.warning("None of the source columns in the mapping exist in the DataFrame")
            return df
            
        # Apply the mapping
        try:
            renamed_df = df.rename(columns=valid_mapping)
            logging.info(f"Successfully renamed columns: {valid_mapping}")
            return renamed_df
        except Exception as e:
            logging.error(f"Error applying column mapping: {str(e)}")
            return df
    
    def export_to_excel(self, dfs: Dict[str, pd.DataFrame], output_path: str, include_timestamp: bool = False) -> str:
        """
        Export DataFrames to an Excel file.
        
        Args:
            dfs (Dict[str, pd.DataFrame]): A dictionary mapping sheet names to DataFrames.
            output_path (str): The path where the Excel file will be saved.
            include_timestamp (bool, optional): Whether to include a timestamp in the filename. Defaults to False.
            
        Returns:
            str: The path to the saved Excel file.
        """
        try:
            if include_timestamp:
                # Insert timestamp before file extension
                base, ext = os.path.splitext(output_path)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = f"{base}_{timestamp}{ext}"
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                for sheet_name, df in dfs.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                
            logging.info(f"Successfully exported data to {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"Error exporting data to Excel: {str(e)}")
            raise 