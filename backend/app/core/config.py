from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "EES Power Grid Sun API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:password@localhost:5432/ees_industrial_universe"
    cors_origins: str = "http://localhost:5500,http://localhost:8000"
    api_key: str = "change-me"
    simulation_interval_seconds: int = 2
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
