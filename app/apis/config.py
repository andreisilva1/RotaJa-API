from pydantic_settings import BaseSettings, SettingsConfigDict


_base_config = SettingsConfigDict(
    env_file="./.env", extra="ignore", env_ignore_empty=True
)


class APIConfiguration(BaseSettings):
    model_config = _base_config
    VIACEP_URL: str
    LOCATIONIQ_URL: str
    LOCATIONIQ_KEY: str
    OVERPASS_URL: str
    TOMTOM_KEY: str
    LOCATIONIQ_REVERSE_GEOCODING_URL: str
    WEATHER_API_KEY: str


api_settings = APIConfiguration()
