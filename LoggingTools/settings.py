# library
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




class LoggerSettings(BaseSettings):
    
    base_config_path: str = Field(..., description="Base path for the configuration files", env='BASE_CONFIG_PATH')
    push_config_path: str = Field(..., description="Path to the configuration file for the push logger", env='PUSH_CONFIG_PATH')
    app_config_dict: Dict[str, str] = Field(default_factory=dict, description="Dictionary of application-specific logging configurations", env='APP_CONFIG_DICT')
    
    class Config:
        env_file="config/env/.env"
        env_prefix = "LOG_"
        extra="ignore"
    
    @model_validator(mode='before')
    def extract_dict(cls, values):
        # Extract environment variables that start with deliminter and build the dict
        dict_values = {}
        for key, value in values.items():
            if key.startswith("LOG__".casefold()):
                dict_key = key.split("__", 1)[-1]
                dict_values[dict_key] = value
        # Assign the extracted dictionary to the field
        values["app_config_dict"] = dict_values
        return values
    
    
class S3Settings(BaseSettings):
    access_key: str = Field(..., description="Access key for the S3 bucket", env='ACCESS_KEY')
    secret_key: str = Field(..., description="Secret key for the S3 bucket", env='SECRET_KEY')
    endpoint_url: str = Field(..., description="Endpoint URL for the S3 bucket", env='ENDPOINT_URL')
    bucket_name: str = Field(..., description="Name of the S3 bucket", env='BUCKET_NAME')
    key_prefix: Optional[str] = Field('', description="Prefix for the S3 key", env='KEY_PREFIX')
    region: str = Field('us-east-1', description="Region of the S3 bucket", env='REGION')
    upload_directory: Optional[str] = Field(..., description="Directory to upload to S3", env='UPLOAD_DIRECTORY')
    
    class Config:
        env_file="config/env/.env"
        env_prefix = "S3_"
        extra="ignore"