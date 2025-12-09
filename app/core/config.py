from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Database
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_NAME: str = "bananay_calc"

    # App
    APP_NAME: str = "Bananay Delivery Calculator"
    DEBUG: bool = True

    # External APIs - Routing
    # Yandex Router API
    YANDEX_API_KEY: str | None = None
    YANDEX_ROUTER_API_URL: str = "https://api.routing.yandex.net/v2/route"
    YANDEX_API_TIMEOUT: int = 5

    OPENROUTESERVICE_API_KEY: str | None = None
    OPENROUTESERVICE_API_URL: str = "https://api.openrouteservice.org/v2/directions/driving-car"
    OPENROUTESERVICE_TIMEOUT: int = 5

    # Which provider to use: 'yandex', 'openroute' or 'fallback'
    ROUTING_PROVIDER: str = "openroute"

    # Calculator settings
    DISTANCE_FALLBACK_COEFFICIENT: float = 1.4

    # Search settings
    SEARCH_SIMILARITY_THRESHOLD: float = 0.4
    SEARCH_DEFAULT_LIMIT: int = 15
    SEARCH_MIN_LENGTH: int = 3
    SEARCH_FUZZY_MIN_LENGTH: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )

    @property
    def database_url(self) -> str:
        """Get async database URL."""
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            f"?server_settings=search_path%3Dpublic"
        )

    @property
    def database_url_sync(self) -> str:
        """Get sync database URL for Alembic."""
        return (
            f"postgresql+psycopg2://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            f"?options=-csearch_path%3Dpublic"
        )


settings = Settings()
