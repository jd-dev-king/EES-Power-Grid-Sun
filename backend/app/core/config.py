from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EES Power Grid Sun API"
    environment: str = "development"

    # Local-development fallback only.
    # Railway will override this with DATABASE_URL.
    database_url: str = (
        "postgresql+psycopg://jeremiahlupton@localhost:5432/"
        "ees_data_platform"
    )

    cors_origins: str = (
        "http://localhost:5500,"
        "http://localhost:8080,"
        "https://jd-dev-king.github.io"
    )
    
    rc_controls_api_url: str = (
    "https://ees-rc-controls-production.up.railway.app"
    )

    api_key: str = "change-me"
    simulation_interval_seconds: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
