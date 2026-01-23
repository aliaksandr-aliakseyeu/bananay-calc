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

    # JWT Authentication
    SECRET_KEY: str = "secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3001"

    # Email settings
    EMAIL_LOG_FILE: str = "emails_log.txt"  # For mock/testing

    # SMTP settings (for real email sending)
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_FROM_NAME: str = "Bananay"
    SMTP_USE_TLS: bool = True

    # Use real email sending if SMTP is configured
    USE_REAL_EMAIL: bool = False

    # Delivery lists settings
    MAX_DELIVERY_LISTS_PER_USER: int = 20
    MAX_ITEMS_PER_LIST: int = 500
    DEFAULT_SEARCH_RADIUS_METERS: int = 300
    MAX_SEARCH_RADIUS_METERS: int = 5000

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
