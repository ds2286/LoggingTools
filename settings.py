# library
from typing import Optional

# installed
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)
from pydantic import Field




class ListenerSettings(BaseSettings):
    monitor_path: str = Field(..., env='PATH_TO_MONITOR')
    specific_file: str = Field(..., env='SPECIFIC_FILE')
    
    class Config:
        env_file="config/env/.env"
        env_prefix = "APP_"
        extra="ignore"
    
    
