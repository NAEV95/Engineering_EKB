from typing import Dict, Any, List, Optional, Union
import json
import os
import yaml
import logging


class ConfigLoader:
    """
    ConfigLoader class for loading and managing Excel processing configuration
    from either JSON or YAML files.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the ConfigLoader with a path to a configuration file.
        
        Args:
            config_path: Path to the configuration file (JSON or YAML)
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration file has invalid format
        """
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from the specified file.
        
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration file has invalid format
        """
        if not os.path.exists(self.config_path):
            self.logger.error(f"Config file not found: {self.config_path}")
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        file_ext = os.path.splitext(self.config_path)[1].lower()
        
        try:
            if file_ext == '.json':
                with open(self.config_path, 'r') as file:
                    return json.load(file)
            elif file_ext in ['.yaml', '.yml']:
                with open(self.config_path, 'r') as file:
                    return yaml.safe_load(file)
            else:
                self.logger.error(f"Unsupported config file format: {file_ext}")
                raise ValueError(f"Unsupported config file format: {file_ext}. Use .json, .yaml, or .yml")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON config: {str(e)}")
            raise ValueError(f"Invalid JSON format in config file: {str(e)}")
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML config: {str(e)}")
            raise ValueError(f"Invalid YAML format in config file: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error loading config file: {str(e)}")
            raise ValueError(f"Error loading config file: {str(e)}")
    
    def get_column_mapping(self) -> Dict[str, str]:
        """
        Get column mapping from the configuration.
        
        Returns:
            Dictionary mapping original column names to new column names
        """
        return self.config.get('column_mapping', {})
    
    def get_filter_criteria(self) -> List[Dict[str, Any]]:
        """
        Get filter criteria from the configuration.
        
        Returns:
            List of filter criteria dictionaries
        """
        return self.config.get('filters', [])
    
    def get_processing_option(self, key: str, default: Any = None) -> Any:
        """
        Get a specific processing option from the configuration.
        
        Args:
            key: The option key to retrieve
            default: Default value if key is not found
            
        Returns:
            The value associated with the key, or the default
        """
        processing_options = self.config.get('processing_options', {})
        return processing_options.get(key, default)
    
    def get_output_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a specific output setting from the configuration.
        
        Args:
            key: The setting key to retrieve
            default: Default value if key is not found
            
        Returns:
            The value associated with the key, or the default
        """
        output_settings = self.config.get('output_settings', {})
        return output_settings.get(key, default)
    
    def save_config(self, config_path: Optional[str] = None) -> None:
        """
        Save the current configuration to a file.
        
        Args:
            config_path: Path to save the configuration (defaults to original path)
            
        Raises:
            ValueError: If there's an error saving the configuration
        """
        save_path = config_path or self.config_path
        file_ext = os.path.splitext(save_path)[1].lower()
        
        try:
            if file_ext == '.json':
                with open(save_path, 'w') as file:
                    json.dump(self.config, file, indent=2)
            elif file_ext in ['.yaml', '.yml']:
                with open(save_path, 'w') as file:
                    yaml.dump(self.config, file, default_flow_style=False)
            else:
                raise ValueError(f"Unsupported config file format: {file_ext}. Use .json, .yaml, or .yml")
                
            self.logger.info(f"Config saved to: {save_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving config to {save_path}: {str(e)}")
            raise ValueError(f"Error saving config to {save_path}: {str(e)}")
    
    def update_config(self, key: str, value: Any) -> None:
        """
        Update a top-level configuration key.
        
        Args:
            key: The key to update
            value: The new value
        """
        self.config[key] = value
        self.logger.debug(f"Updated config key: {key}")
    
    def update_processing_option(self, key: str, value: Any) -> None:
        """
        Update a processing option in the configuration.
        
        Args:
            key: The option key to update
            value: The new value
        """
        if 'processing_options' not in self.config:
            self.config['processing_options'] = {}
        
        self.config['processing_options'][key] = value
        self.logger.debug(f"Updated processing option: {key}")
    
    def update_output_setting(self, key: str, value: Any) -> None:
        """
        Update an output setting in the configuration.
        
        Args:
            key: The setting key to update
            value: The new value
        """
        if 'output_settings' not in self.config:
            self.config['output_settings'] = {}
        
        self.config['output_settings'][key] = value
        self.logger.debug(f"Updated output setting: {key}")
    
    def get_validation_rules(self) -> List[Dict[str, Any]]:
        """
        Get validation rules from the configuration.
        
        Returns:
            List of validation rule dictionaries
        """
        return self.config.get('validation_rules', [])
    
    def get_transformations(self) -> List[Dict[str, Any]]:
        """
        Get data transformations from the configuration.
        
        Returns:
            List of transformation dictionaries
        """
        return self.config.get('transformations', [])
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the complete configuration dictionary.
        
        Returns:
            The complete configuration dictionary
        """
        return self.config


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Helper function to load a configuration file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dict containing the configuration
    """
    loader = ConfigLoader(config_path)
    return loader.get_config() 