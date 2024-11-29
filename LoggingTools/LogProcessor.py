import re
import logging
import shutil
from datetime import datetime
from pathlib import Path
from dateutil import parser as date_parser
import yaml

# installed
# import psycopg3

# custom
try:
    from S3Tools.S3Manager import S3Manager
except ImportError:
    S3Manager = None

from settings import (
    S3Settings,
    LoggerSettings
)
# from S3Manager import S3Manager
from LoggingHelper import LoggerFactory




class LogProcessor:
    
    def __init__(
        self, 
        s3_settings: S3Settings,
        logger_settings: LoggerSettings,
        logger_factory: LoggerFactory=None,
        logger_config_path: str=None,
    ):
        
        self.log_dir = Path(logger_settings.directory_name)
        self.unprocessed_dir = self.log_dir / "unprocessed"
        self.processed_dir = self.log_dir / "processed"
        self.error_dir = self.log_dir / "errors"
        
        self.log_formats = {}
        self.timestamp_formats = {}
        self.insert_num = 0
        
        try:
            if not logger_factory:
                logger_factory = LoggerFactory(
                    logger_settings=logger_settings
                )
                logger_factory.setup_logger()
            
            if not LoggerFactory.is_logger_configured("process_logger"):        
                logger_factory.add_logger_from_yaml(
                    new_logger_config_path=logger_config_path,
                )
            
            self.logger = logger_factory.get_logger("process_logger")
        except Exception as e:
            raise e
        
        self.s3_settings = s3_settings
        
        if S3Manager:
            self.s3_manager = S3Manager(
                s3_settings=s3_settings,
                logger_factory=logger_factory
            )
        else: # S3Tools not installed
            self.logger.warning("S3Tools not installed. S3 functionality will be disabled.")
        
        self.logger.debug("Log processor started.")
        
    def initialize(self):
        
        # Ensure directories exist
        for directory in [self.unprocessed_dir, self.processed_dir, self.error_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Load log formats from YAML configuration
        with open("LoggingTools/config/log_formats.yml", "r") as config_file:
            self.log_formats = yaml.safe_load(config_file)
            
        with open("LoggingTools/config/timestamp_formats.yml", "r") as config_file:
            self.timestamp_formats = yaml.safe_load(config_file)
            
        self.logger.info("Log processor initialized.")
            
    # Parse a timestamp flexibly
    def parse_timestamp(
        self, 
        timestamp
    ):
        for fmt in self.timestamp_formats:
            try:
                return datetime.strptime(timestamp, fmt.get("pattern"))
            except ValueError:
                continue
        try:
            # Fallback to dateutil for unusual formats
            return date_parser.parse(timestamp)
        except Exception as e:
            self.logger.warning(f"Timestamp parsing failed: {timestamp} ({e})")
            return None
        
    # Detect if a line is a continuation
    def is_continuation(
        self, 
        line
    ):
        """
        Determine if a line is a continuation of the previous log entry.
        """
        line = line.strip()
        # Continuation lines often lack timestamps or start with a whitespace
        if not line:
            return False  # Skip empty lines
        if any(re.match(fmt["pattern"], line) for fmt in self.log_formats):
            return False  # Matches a known log pattern
        if line.startswith(" "):  # Indented continuation line
            return True
        return False  # Default: assume it's not a continuation
    
    # Parse a single log line
    def parse_log_line(
        self,
        line
    ):
        for fmt in self.log_formats:

            match = re.match(fmt["pattern"], line)
            if match:
                parsed_data = match.groupdict()
                # Parse timestamp if present
                if "timestamp" in parsed_data and parsed_data["timestamp"]:
                    parsed_data["timestamp"] = self.parse_timestamp(parsed_data["timestamp"])
                self.logger.debug(f"Parsed log line: {parsed_data}")
                return parsed_data
            # else:
            #     self.logger.info(f"Pattern mismatch: {fmt['pattern']} vs. {line.strip()}")
        return None
    
    def db_connect(self):
        
        # Database connection
        # conn = psycopg3.connect("dbname=logs_db user=your_user password=your_password host=localhost")
        # cursor = conn.cursor()
        pass
    
    # Insert parsed data into Postgres
    def insert_into_database(
        self,
        log_data
    ):
        # query = """
        # INSERT INTO logs (timestamp, level, message, raw_line)
        # VALUES (%s, %s, %s, %s)
        # """
        # cursor.execute(query, (
        #     log_data.get("timestamp"),
        #     log_data.get("level"),
        #     log_data.get("message"),
        #     log_data.get("raw_line")
        # ))
        # conn.commit()
        # self.logger.info(f"Inserted log entry: {log_data}")
        self.insert_num += 1
        
    def process_log_file(
        self,
        file_path
    ):
        """
        Process a log file line-by-line to ensure multiline entries are handled correctly.
        """
        try:
            log_line_num = 0
            buffer = None  # Buffer for the current log entry

            with open(file_path, 'r') as log_file:
                for line in log_file:
                    line = line.strip()
                    log_line_num += 1

                    # Check if the line starts a new log entry
                    if not self.is_continuation(line):
                        # Flush the current buffer
                        if buffer:
                            self.insert_into_database(buffer)
                            buffer = None

                        # Parse the new log line
                        parsed_data = self.parse_log_line(line)
                        if parsed_data:
                            parsed_data["raw_line"] = line
                            buffer = parsed_data
                        else:
                            self.logger.warning(f"Unparseable structured line: {line}")

                    else:  # It's a continuation line
                        if buffer:
                            buffer["message"] += f" {line}"
                        else:
                            self.logger.warning(f"Continuation line without a preceding buffer: {line}")

                # Flush the last buffer
                if buffer:
                    self.insert_into_database(buffer)

            # Move file to processed directory
            shutil.move(file_path, self.processed_dir / file_path.name)
            self.logger.info(f"Successfully processed file: {file_path.name}")

        except Exception as e:
            self.logger.error(f"Error processing file {file_path.name}: {e}")
            shutil.move(file_path, self.error_dir / file_path.name)
            
            
    def process_all_logs(
        self,
        s3_pull: bool
    ):
        
        self.initialize()
        if s3_pull and S3Manager:
            self.s3_manager.download_files(
                files_to_download,
                self.unprocessed_dir
            )
        else:
            self.logger.warning("Skipping S3 download.")
            
        for file_path in self.unprocessed_dir.iterdir():
            if file_path.is_file():
                self.process_log_file(file_path)


# Usage
if __name__ == "__main__":

    env_path = "/home/ubuntu/projects/LoggingTools/LoggingTools/config/env/.env"
    s3_settings = S3Settings(_env_file=env_path)
    logger_settings = LoggerSettings(_env_file=env_path)

    files_to_download = [
        "aws_20231109_AV234001_977.tar.zst_2024-06-15-06.log",
        "20240612_AV234001_1020.log",
        "archive_process_2024-06-15_05-26-58.log",
        "20240715_AV234001_1032-1033.log",
    ]
    
    log_processor = LogProcessor(
        s3_settings,
        logger_settings
    )
    log_processor.process_all_logs(
        s3_pull=True
    )
    
    print("Log processing complete. Check 'log_processor.log' for details.")
    print(f"Total log entries inserted: {log_processor.insert_num}")