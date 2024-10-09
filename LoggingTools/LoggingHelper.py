# library
from pathlib import Path
import logging
import logging.config
import os
import datetime

# installed
import yaml

# custom
from LoggingTools.settings import LoggerSettings




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
        app_config_dict={},
        logger_settings: LoggerSettings=None
    ):
        """
        Initializes the LoggerFactory with the paths to the base and application-specific
        logging configuration files.
        """
        
        self.logger_settings = logger_settings or LoggerSettings()
        self.base_config_path = base_config_path or self.logger_settings.base_config_path
        self.app_config_dict = app_config_dict or self.logger_settings.app_config_dict
        self.config = None
    
    def load_config(self):
        """
        Loads the base and application-specific logging configuration from YAML files.
        """
        
        with open(self.base_config_path, 'r') as file:
            base_config = yaml.safe_load(file)
        
        self.config = base_config
        for config_name, config_str in self.app_config_dict.items():
            
            config_path = Path(config_str)
            if config_path.is_file() and config_path.exists():
                with open(config_str, 'r') as file:
                    app_config = yaml.safe_load(file)
                # Merge application-specific logger configuration with base config
                self.config = self.merge_dicts(self.config, app_config)
                
    def set_dynamic_log_filename(self):
        """
        Sets a dynamic log file name to ensure a new log file is created for every process execution.
        This also switch all rotating file handlers to standard file 
        handlers with dynamic filenames, modifying only the in-memory configuration.
        """

        if 'handlers' in self.config:
            log_file_name = f"logs/app_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
            for handler_name, handler_config in self.config['handlers'].items():
                
                # If the handler is a rotating or timed rotating file handler, switch to FileHandler
                new_config = {}
                if handler_config['class'] in ['logging.handlers.RotatingFileHandler', 'logging.handlers.TimedRotatingFileHandler']:
                    # Change the handler class to FileHandler
                    new_config['class'] = 'logging.FileHandler'
                    # Set the dynamic filename
                    new_config['filename'] = log_file_name
                    # Ensure the mode and encoding are set appropriately
                    new_config['mode'] = 'a'  # Append mode
                    new_config['encoding'] = 'utf-8'
                    
                    self.config['handlers'].pop(handler_name)
                    self.config['handlers'][handler_name] = new_config
                
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
    
    def setup_logger(
        self,
        dynamic_log_filename=False
    ):
        """
        Complete the process of loading configuration, setting dynamic log file name, 
        and applying the configuration.
        """
        log_dir = Path(f"{os.getcwd()}/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        self.load_config()
        
        if dynamic_log_filename:
            self.set_dynamic_log_filename()
        
        self.apply_config()

