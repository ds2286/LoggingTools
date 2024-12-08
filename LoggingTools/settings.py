# library
import importlib.resources as pkg_resources
from pathlib import Path
from typing import (
    Optional,
    Dict
)

# installed
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)
from pydantic import (
    Field,
    model_validator
)




class LoggingConfigFiles(BaseSettings):
    config_dict: Dict[str, str] = Field(
        default_factory=dict, 
        description="Dictionary of application-specific logging configurations"
    )
    
    @model_validator(mode="before")
    def populate_dict(cls, values):
        if not values:
            values = {}
            values["config_dict"] = {}
            return values
        
        prefix = "LOG_APP_"
        config_dict = {
            key[len(prefix):]: value
            for key, value in values.items()
            if key.startswith(prefix)
        }
        values["config_dict"] = config_dict
        return values
    
    class Config:
        env_file = "config/env/.env"
        env_prefix = "LOG_APP_"
        extra = "ignore"

class LoggerSettings(BaseSettings):
    base_config_path: Optional[str] = Field(
        None, 
        description="Base path for the configuration files", 
        env="BASE_CONFIG_PATH"
    )
    push_config_path: Optional[str] = Field(
        None, 
        description="Path to the configuration file for the push logger", 
        env="PUSH_CONFIG_PATH"
    )
    file_paths: LoggingConfigFiles = Field(
        None, 
        description="Application-specific logging configuration"
    )
    directory_name: str = Field(
        ..., 
        description="Name of the directory to store logs", 
        env="DIRECTORY_NAME"
    )
    filename: Optional[str] = Field(
        None, 
        description="Name of the log file", 
        env="LOG_FILE_NAME"
    )

    class Config:
        env_file = "config/env/.env"
        env_prefix = "LOG_"
        extra = "ignore"
    
    @staticmethod
    def resolve_file_path(file_name: str, package: Optional[str] = None) -> str:
        """
        Resolve a file path either locally or within an installed package.

        Args:
            file_name (str): The name of the file to find.
            package (Optional[str]): The package to search in if not found locally.

        Returns:
            str: The resolved file path.

        Raises:
            FileNotFoundError: If the file is not found.
        """
        # Check if file exists locally
        local_file = Path(file_name)
        if local_file.exists():
            return str(local_file.resolve())

        # Check if the file exists within the package
        if package:
            try:
                with pkg_resources.path(package, file_name) as pkg_file:
                    return str(pkg_file.resolve())
            except FileNotFoundError:
                pass

        # Raise error if file is not found
        raise FileNotFoundError(f"{file_name} not found locally or in the package {package}.")

    @model_validator(mode="before")
    def load_paths(cls, values):
        """
        Validator to load and validate logging config file paths.

        Args:
            values (dict): Model field values before validation.

        Returns:
            dict: Updated field values with resolved file paths.
        """
        package = "LoggingTools.config"

        
        if not values.get("base_config_path"):
            values["base_config_path"] = cls.resolve_file_path(
                values["base_config_path"], package
            )

        if not values.get("push_config_path"):
            values["push_config_path"] = cls.resolve_file_path(
                values["push_config_path"], package
            )

        return values
    
class S3Settings(BaseSettings):
    access_key: str = Field(..., description="Access key for the S3 bucket", env='ACCESS_KEY')
    secret_key: str = Field(..., description="Secret key for the S3 bucket", env='SECRET_KEY')
    endpoint_url: Optional[str] = Field(..., description="Endpoint URL for the S3 bucket", env='ENDPOINT_URL')
    bucket_name: str = Field(..., description="Name of the S3 bucket", env='BUCKET_NAME')
    key_prefix: Optional[str] = Field('', description="Prefix for the S3 key", env='KEY_PREFIX')
    region: str = Field('us-east-1', description="Region of the S3 bucket", env='REGION')
    upload_directory: Optional[str] = Field(..., description="Directory to upload to S3", env='UPLOAD_DIRECTORY')
    max_workers: Optional[int] = Field(5, description="Number of threads for the thread pool", env='MAX_WORKERS')
    
    class Config:
        env_file="config/env/.env"
        env_prefix = "S3_"
        extra="ignore"