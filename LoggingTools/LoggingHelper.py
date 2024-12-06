# library
from __future__ import annotations
import re
import threading
from typing import List, Optional, Union
from pathlib import Path
from logging import Handler
from threading import Lock
from queue import Queue
from logging.handlers import (
    QueueHandler, 
    QueueListener
)
from logging.config import (
    ConvertingList,
    ConvertingDict,
    dictConfig,
    valid_ident
)
import importlib.resources
import logging.config
import logging
import datetime
import atexit
import sys
import os



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
    
    _lock = threading.Lock()
    
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
        
        self.logger_settings = logger_settings or LoggerSettings(
            _env_file=os.getenv("ENV_PATH")
        )
        self.base_config_path = base_config_path or self.logger_settings.base_config_path
        self.app_config_dict = app_config_dict or self.logger_settings.app_config_dict
        self.config = None
        self.default_file_handler = None
    
    def load_config(
        self,
        config_data_dict: dict = {}
    ):
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
        if config_data_dict:
            self.config = self.merge_dicts(self.config, config_data_dict)
            
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
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            if "{0}" in full_path:
                full_path = full_path.format(
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
        print(self.config)
        if self.config:
            dictConfig(self.config)
            self.default_file_handler = logging.getHandlerByName('file')
    
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
    
    @staticmethod
    def load_from_package(
        package: str, 
        filenames: Optional[list[str]] = None, 
        collect_all: bool = False, 
        pattern: Optional[str] = None
    ) -> dict[str, str]:
        """
        Load file paths from a package into a dictionary.
        
        :param package: The package containing the files.
        :param filenames: A list of filenames to retrieve paths for. Ignored if `collect_all` is True.
        :param collect_all: If True, collect paths for all files in the package directory.
        :param pattern: If provided, collect paths for files matching the regex pattern.
        :return: A dictionary where keys are filenames and values are their paths.
        """
        file_paths = {}

        if collect_all or pattern:
            # Collect all or filtered file paths in the package directory
            for file in importlib.resources.files(package).iterdir():
                if file.is_file():  # Ensure it's a file, not a subdirectory
                    if pattern:
                        if re.search(pattern, file.name):  # Check if the file name matches the pattern
                            file_paths[file.name] = str(file)
                    elif collect_all:
                        file_paths[file.name] = str(file)
        elif filenames:
            # Collect specified file paths
            for filename in filenames:
                with importlib.resources.path(package, filename) as file_path:
                    file_paths[filename] = str(file_path)
        
        return file_paths
        
    @staticmethod
    def load_yaml_from_package(
        package: str, 
        filename: str
    ) -> dict:
        """
        Load the content of a YAML file from a package into a dictionary.
        
        :param package: The package containing the file.
        :param filename: The name of the file to load.
        :return: The content of the file.
        """

        return yaml.safe_load(importlib.resources.open_text(package, filename))
        
    @staticmethod
    def replace_logger_handlers(
        logger: logging.Logger,
        new_handlers: List[Handler]
    ):
        """
        Replace the handlers of a logger with new handlers.
        
        :param logger: The logger to modify.
        :param new_handlers: The new handlers to set for the logger.
        """
        with LoggerFactory._lock:
            for handler in logger.handlers:
                logger.removeHandler(handler)
            for handler in new_handlers:
                logger.addHandler(handler)
    
    def setup_logger(
        self,
        dynamic_log_filename=False,
        config_data_dict: dict = {},
        files_to_load_dict: dict = {}
    ):
        """
        Complete the process of loading configuration, setting dynamic log file name, 
        and applying the configuration.
        """
        # log_dir = Path(f"{os.getcwd()}/logs")
        log_dir = Path(self.logger_settings.directory_name)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        if files_to_load_dict:
            for file_name, file_path in files_to_load_dict.items():
                self.app_config_dict[file_name] = file_path

        self.load_config(config_data_dict=config_data_dict)
        
        self.set_log_filename(
            dynamic_log_filename=dynamic_log_filename
        )

        self.apply_config()

