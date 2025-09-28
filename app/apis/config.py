from pydantic_settings import BaseSettings, SettingsConfigDict


_base_config = SettingsConfigDict(
    env_file="./.env", extra="ignore", env_ignore_empty=True
)


class APIConfiguration(BaseSettings):
    model_config = _base_config
    VIACEP_URL: str


api_settings = APIConfiguration()
