from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class BaseConfig(BaseSettings):
    """Base configuration for the Option Trading system."""
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
