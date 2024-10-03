# library
from typing import Optional

# installed
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)
from pydantic import Field




class LoggerSettings(BaseSettings):
    
    base_config_path: str = Field(..., description="Base path for the configuration files", env='BASE_CONFIG_PATH')
    app_config_path: str = Field(..., description="Application-specific path for the configuration files", env='APP_CONFIG_PATH')
    push_config_path: str = Field(..., description="Path to the configuration file for the push logger", env='PUSH_CONFIG_PATH')
    
    class Config:
        env_file="config/env/.env"
        env_prefix = "APP_"
        extra="ignore"
    
    
class S3Settings(BaseSettings):
    access_key: str = Field(..., description="Access key for the S3 bucket", env='ACCESS_KEY')
    secret_key: str = Field(..., description="Secret key for the S3 bucket", env='SECRET_KEY')
    endpoint_url: str = Field(..., description="Endpoint URL for the S3 bucket", env='ENDPOINT_URL')
    bucket_name: str = Field(..., description="Name of the S3 bucket", env='BUCKET_NAME')
    region: str = Field('us-east-1', description="Region of the S3 bucket", env='REGION')
    upload_directory: Optional[str] = Field(..., description="Directory to upload to S3", env='UPLOAD_DIRECTORY')
    
    class Config:
        env_file="config/env/.env"
        env_prefix = "S3_"
        extra="ignore"