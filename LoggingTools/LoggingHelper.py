# library
from pathlib import Path
import logging
import logging.config
import os
import datetime
import sys

current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(current_directory)

# Add directory to the sys.path
if parent_directory not in sys.path:
    sys.path.append(parent_directory)

# installed
import yaml

# custom
from LoggingTools.settings import LoggerSettings


FILE_TYPE_CLASSES = [
    'logging.FileHandler',
    'logging.handlers.RotatingFileHandler',
    'logging.handlers.TimedRotatingFileHandler',
]

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
            
        if self.logger_settings.push_config_path:
            with open(self.logger_settings.push_config_path, 'r') as file:
                push_config = yaml.safe_load(file)
            # Merge push logger configuration with base config
            base_config = self.merge_dicts(base_config, push_config)
        
        self.config = base_config
        for config_name, config_str in self.app_config_dict.items():
            
            config_path = Path(config_str)
            if config_path.is_file() and config_path.exists():
                with open(config_str, 'r') as file:
                    app_config = yaml.safe_load(file)
                # Merge application-specific logger configuration with base config
                self.config = self.merge_dicts(self.config, app_config)
                
    def set_log_filename(
        self,
        dynamic_log_filename=False
    ):
        """
        Sets a dynamic log file name to ensure a new log file is created for every process execution.
        This also switch all rotating file handlers to standard file 
        handlers with dynamic filenames, modifying only the in-memory configuration.
        """

        if 'handlers' not in self.config:
            return
            
        for logger_name,logger_values in self.config['loggers'].items():
            if logger_name == "root":
                continue
                
            # custom settings
            specific_filename = logger_values.pop("filename", None)
            add_to = logger_values.pop("add_to", [])
            
            default_filename = self.logger_settings.filename or \
                self.config['handlers']['file']['filename']
            log_filename = specific_filename or default_filename
            full_path = f"{self.logger_settings.directory_name}/{log_filename}"
            
            if "{0}" in log_filename:
                log_filename = log_filename.format(
                    datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                )
            
            if dynamic_log_filename:
                # Remove file class handlers from the logger
                logger_values["handlers"] = [
                    h for h in logger_values.get("handlers", [])
                    if self.config['handlers'].get(h, {}).get('class') 
                    not in FILE_TYPE_CLASSES
                ]
                
                log_filename_list = log_filename.split('.')
                now_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                log_filename = \
                f"{self.logger_settings.directory_name}/" + \
                f"{log_filename_list[0]}_{now_time}.{log_filename_list[1]}"
            
            # Assign determined filename to the appropriate handler
            if specific_filename:
                    
                # Create a custom handler for the logger
                special_handler = self.config['handlers']['file'].copy()
                special_handler['filename'] = full_path

                handler_name = f"{logger_name}_handler"
                self.config['handlers'][handler_name] = special_handler

                logger_values["handlers"] = [
                    h for h in logger_values["handlers"] if h != "file"
                ] + [handler_name]
                
                if add_to:
                    for name_of_logger in add_to:
                        self.config['loggers'][name_of_logger]['handlers'] += [handler_name]
                
            else:
                # Use the default file handler
                self.config['handlers']['file']['filename'] = full_path
            
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
        
        if not new_logger_config_path:
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
    def is_logging_configured() -> bool:
        if logging.getLogger().hasHandlers():
            logging.info("Logging is already configured.")
            return True
        else:
            logging.info("Logging is not configured.")
            return False
        
    @staticmethod
    def is_logger_configured(logger_name: str) -> bool:
        logger = logging.getLogger(logger_name)
        return bool(logger.handlers)
    
    def setup_logger(
        self,
        dynamic_log_filename=False
    ):
        """
        Complete the process of loading configuration, setting dynamic log file name, 
        and applying the configuration.
        """
        # log_dir = Path(f"{os.getcwd()}/logs")
        log_dir = Path(self.logger_settings.directory_name)
        log_dir.mkdir(parents=True, exist_ok=True)
        self.load_config()
        
        self.set_log_filename(
            dynamic_log_filename=dynamic_log_filename
        )

        self.apply_config()

