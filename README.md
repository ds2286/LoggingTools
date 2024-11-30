# LoggingTools

This repository standardizes logging for Python applications by providing a flexible, configurable logging system with S3 integration and log processing capabilities.

## Overview

### Application Directory
```text
LoggingTools/
├── __init__.py
├── LoggingHelper.py      # Core logging functionality
├── LogProcessor.py       # Log processing and parsing
├── LogPush.py           # S3 integration
├── settings.py          # Configuration settings
└── config/
    ├── base_logging_config.yml
    ├── json_logging_config.yml
    ├── log_formats.yml
    ├── process_logging_config.yml
    ├── push_logging_config.yml
    ├── s3_manager_logging_config.yml
    └── timestamp_formats.yml
```

### Features
- Dynamic log file naming and rotation
- Multiple logging formats support
- Configurable logging levels and handlers
- S3 integration for log archival
- Log processing and parsing capabilities
- Environment-based configuration
- Support for multiple timestamp formats
- Thread-safe logging

### Todo Tasks
- [ ] Complete database integration in LogProcessor
- [ ] Add more log format patterns in log_formats.yml
- [ ] Implement log compression before S3 upload
- [ ] Add log retention policies
- [ ] Implement log search functionality

## Dependencies

Core dependencies:
```python
PyYAML>=6.0
pydantic>=2.0
pydantic-settings>=2.0
setuptools>=65.0
```

Optional dependencies:
- boto3 (for S3 integration)
- `S3Tools` (for enhanced S3 functionality)
- `dbTools` (for database integration)

## Setup

### Prerequisites
- Python 3.11 or higher
- pip (Python package installer)
- Access to S3-compatible storage (optional)

### Configuration
1. Create environment file based on example.env
2. Configure logging settings:
   - Base logging: base_logging_config.yml
   - Log formats: log_formats.yml
   - Process logging: process_logging_config.yml

### Installation

#### Option 1: Standard Installation
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install directly from GitHub
pip install git+https://github.com/EpiGenomicsCode/LoggingTools.git

pip install git+https://github.com/EpiGenomicsCode/LoggingTools.git[s3_tools] # S3 support
pip install git+https://github.com/EpiGenomicsCode/LoggingTools.git[database] # Database support
pip install git+https://github.com/EpiGenomicsCode/LoggingTools.git[all] # All features
```

#### Option 2: Development Installation
```bash
# Clone repository
git clone https://github.com/EpiGenomicsCode/LoggingTools.git
cd LoggingTools

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -e .[all]
```

## Usage

Basic logging setup:
```python
from LoggingTools.LoggingHelper import LoggerFactory
from LoggingTools.settings import LoggerSettings

# Initialize logger
logger_settings = LoggerSettings(_env_file="config/env/.env")
logger_factory = LoggerFactory(logger_settings=logger_settings)
logger_factory.setup_logger(dynamic_log_filename=True)
logger = logger_factory.get_logger("my_logger")

# Use logger
logger.info("Application started")
logger.debug("Debug information")
logger.error("Error occurred")
```

S3 Integration:
```python
from LoggingTools.LogPush import S3Uploader
from LoggingTools.settings import S3Settings

# Initialize S3 uploader
s3_settings = S3Settings(_env_file="config/env/.env")
uploader = S3Uploader(s3_settings=s3_settings)

# Upload logs
uploader.upload_directory("logs")
```

## Security Considerations

### Authentication
- Store credentials in environment files outside version control
- Use IAM roles when possible for S3 authentication
- Implement credential rotation policies
- Use secure credential storage solutions in production

### Data Protection
- Encrypt logs in transit using TLS/SSL
- Enable server-side encryption for S3 storage
- Sanitize sensitive information before logging
- Implement log retention policies
- Use secure connections for database operations

### Best Practices
- Follow principle of least privilege for S3 and database access
- Regularly rotate access credentials
- Monitor and audit log access
- Implement log backup strategies
- Use dynamic log filenames to prevent conflicts
- Configure appropriate log levels for different environments
- Implement error handling for all external service interactions
