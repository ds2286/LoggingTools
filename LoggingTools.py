# library
import logging
import logging.config
import os
import datetime

# installed
import yaml

# custom
from settings import LoggerSettings




class LoggerFactory:
    """Logger factory class that loads logging configuration from YAML files,
    applies dynamic log file names, and provides logger instances.
    
    
    ### Usage:
    Create the factory instance:  
    logger_factory = LoggerFactory(
        
        base_config_path='base_logging_config.yml', 
        app_config_path='app_logger_config.yml'  
    )
    
    Set up logging (load config, apply dynamic filename, etc.):  
    logger_factory.setup_logger()
    
    Get the logger instance:  
    logger = logger_factory.get_logger('my_logger')

    Example logging:  
    logger.debug("This is a debug message")  
    logger.info("This is an info message")  
    logger.warning("This is a warning message")
    """
    
    def __init__(
        self, 
        base_config_path=None, 
        app_config_path=None,
        logger_settings: LoggerSettings=None
    ):
        """
        Initializes the LoggerFactory with the paths to the base and application-specific
        logging configuration files.
        """
        
        self.logger_settings = logger_settings or LoggerSettings()
        self.base_config_path = base_config_path or self.logger_settings.base_config_path
        self.app_config_path = app_config_path or self.logger_settings.app_config_path
        self.config = None
    
    def load_config(self):
        """
        Loads the base and application-specific logging configuration from YAML files.
        """
        with open(self.base_config_path, 'r') as file:
            base_config = yaml.safe_load(file)
        
        if self.app_config_path:
            with open(self.app_config_path, 'r') as file:
                app_config = yaml.safe_load(file)
            # Merge application-specific logger configuration with base config
            self.config = self.merge_dicts(base_config, app_config)
        else:
            self.config = base_config
    
    def set_dynamic_log_filename(self):
        """
        Sets a dynamic log file name to ensure a new log file is created for every process execution.
        """
        if 'handlers' in self.config and 'file' in self.config['handlers']:
            log_file_name = f"logs/app_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
            self.config['handlers']['file']['filename'] = log_file_name
    
    def apply_config(self):
        """
        Applies the final logging configuration.
        """
        if self.config:
            logging.config.dictConfig(self.config)
    
    def get_logger(self, logger_name='root'):
        """
        Returns the logger instance for a given logger name.
        """
        return logging.getLogger(logger_name)
    
    def add_logger_from_yaml(self, new_logger_config_path=None):
        """
        Adds a new logger configuration from a YAML file.
        
        The new logger is merged into the existing logging configuration.
        """
        
        if not new_logger_config_path and self.app_config_path:
            new_logger_config_path = self.app_config_path 
        else:
            raise ValueError("New logger configuration path must be provided.")
        
        # Load the new logger configuration from the provided YAML file
        with open(new_logger_config_path, 'r') as file:
            new_logger_config = yaml.safe_load(file)
        
        # Merge the new logger configuration into the existing config
        self.config = self.merge_dicts(self.config, new_logger_config)
        
        # Reapply the updated logging configuration
        self.apply_config()
    
    @staticmethod
    def merge_dicts(a, b):
        """
        Recursively merge dictionary b into dictionary a.
        """
        for key, value in b.items():
            if isinstance(value, dict):
                a[key] = LoggerFactory.merge_dicts(a.get(key, {}), value)
            else:
                a[key] = value
        return a
    
    @staticmethod
    def is_logger_configured() -> bool:
        if logging.getLogger().hasHandlers():
            logging.info("Logging is already configured.")
            return True
        else:
            logging.info("Logging is not configured.")
            return False
    
    def setup_logger(self):
        """
        Complete the process of loading configuration, setting dynamic log file name, 
        and applying the configuration.
        """
        self.load_config()
        self.set_dynamic_log_filename()
        self.apply_config()

