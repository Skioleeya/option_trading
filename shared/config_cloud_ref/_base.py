"""Shared pydantic-settings base configuration for all domain config classes."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Base class for all domain config fragments.

    Loads from .env or ../.env automatically; all sub-classes share the
    same SettingsConfigDict so the file is not re-read multiple times.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
