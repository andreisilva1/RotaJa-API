from pydantic_settings import BaseSettings, SettingsConfigDict


_base_config = SettingsConfigDict(
    env_file="./.env", extra="ignore", env_ignore_empty=True
)


class DatabaseSettings(BaseSettings):
    model_config = _base_config
    DATABASE_URL: str


database_settings = DatabaseSettings()
