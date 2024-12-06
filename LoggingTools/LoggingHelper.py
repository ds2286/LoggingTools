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
    QueueListener,
    RotatingFileHandler,
    TimedRotatingFileHandler
)
from logging.config import dictConfig
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
        filename: Union[str, List[str]]
    ) -> dict:
        """
        Load the content of a YAML file from a package into a dictionary.
        
        :param package: The package containing the file.
        :param filename: The name of the file, or list of files, to load.
        :return: The content of the file(s).
        """
        if isinstance(filename, list):
            
            data_dict = {}
            for item in filename:
                data_dict = LoggerFactory.merge_dicts(
                    data_dict, 
                    yaml.safe_load(importlib.resources.open_text(package, item))
                )
            return data_dict
        else:
            return yaml.safe_load(importlib.resources.open_text(package, filename))
            
    
    @staticmethod
    def duplicate_handler(
        original_handler: logging.Handler,
        new_filename: Optional[str] = None,
        new_level: Optional[int] = None,
        new_formatter: Optional[logging.Formatter] = None,
        **kwargs
    ) -> logging.Handler:
        """
        Duplicates an existing handler with optional customizations.

        Args:
            original_handler (logging.Handler): The handler to copy.
            new_filename (str, optional): The filename for the new handler (if applicable).
            new_level (int, optional): The logging level for the new handler.
            new_formatter (logging.Formatter, optional): The formatter for the new handler.
            **kwargs: Additional arguments to customize specialized handlers.

        Returns:
            logging.Handler: A new handler based on the original with customizations.
        """
        # Determine the type of the original handler
        if isinstance(original_handler, logging.FileHandler):
            # Create a FileHandler (or derived type) with optional new filename
            original_filename = getattr(original_handler, "baseFilename", None)
            parent_dir = os.path.dirname(original_filename) if original_filename else "."
            just_filename = os.path.basename(original_filename) if original_filename else "logfile.log"
            filename = new_filename or os.path.join(parent_dir, "fallback", just_filename)
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            # Handle specific file-based handlers
            if isinstance(original_handler, RotatingFileHandler):
                new_handler = RotatingFileHandler(
                    filename,
                    maxBytes=kwargs.get("maxBytes", original_handler.maxBytes),
                    backupCount=kwargs.get("backupCount", original_handler.backupCount),
                    encoding=kwargs.get("encoding", original_handler.encoding),
                    delay=kwargs.get("delay", original_handler.delay),
                )
            elif isinstance(original_handler, TimedRotatingFileHandler):
                new_handler = TimedRotatingFileHandler(
                    filename,
                    when=kwargs.get("when", original_handler.when),
                    interval=kwargs.get("interval", original_handler.interval),
                    backupCount=kwargs.get("backupCount", original_handler.backupCount),
                    encoding=kwargs.get("encoding", original_handler.encoding),
                    delay=kwargs.get("delay", original_handler.delay),
                    utc=kwargs.get("utc", original_handler.utc),
                )
            else:
                # Default to a standard FileHandler
                new_handler = logging.FileHandler(filename)

        elif isinstance(original_handler, logging.StreamHandler):
            # Create a new StreamHandler
            new_handler = logging.StreamHandler(stream=kwargs.get("stream", original_handler.stream))

        elif isinstance(original_handler, logging.NullHandler):
            # Create a NullHandler
            new_handler = logging.NullHandler()

        elif isinstance(original_handler, logging.handlers.QueueHandler):
            # Create a QueueHandler
            queue = kwargs.get("queue", original_handler.queue)
            new_handler = logging.handlers.QueueHandler(queue)

        else:
            raise ValueError(f"Unsupported handler type: {type(original_handler).__name__}")

        # Copy attributes from the original handler
        new_handler.setLevel(new_level or original_handler.level)
        new_handler.setFormatter(new_formatter or getattr(original_handler, "formatter", None))

        # Copy filters from the original handler
        for filt in original_handler.filters:
            new_handler.addFilter(filt)

        return new_handler
    
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
                
    def start_configured_queue_listeners(self):
        """
        Searches the logging configuration for QueueListeners and starts them.

        This function assumes that QueueListeners are defined and properly associated
        with QueueHandlers in the logging configuration.
        """
        # List to track started listeners
        started_listeners = []

        # Access all handlers in the current logging configuration
        for logger_name in logging.root.manager.loggerDict:
            logger = logging.getLogger(logger_name)

            # Check each handler in the logger
            for handler in logger.handlers:
                if hasattr(handler, 'listener') and isinstance(handler.listener, QueueListener):
                    listener = handler.listener

                    # Start the listener if it hasn't already been started
                    if not listener._thread or not listener._thread.is_alive():
                        listener.start()
                        started_listeners.append(listener)
                        # print(f"Started QueueListener for logger '{logger_name}'")

        # if not started_listeners:
        #     print("No QueueListeners found or started.")
        # else:
        #     print(f"Started {len(started_listeners)} QueueListener(s).")
        
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
        self.start_configured_queue_listeners()
        

