"""App settings. Load from env when you add .env."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "raboo3-ml"
    debug: bool = False
    # API
    host: str = "0.0.0.0"
    port: int = 8000
    # MySQL (Docker)
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = "raboo3_root"
    db_name: str = "raboo3"  # must match db/schema.sql and load_dummy_to_mysql
    # Google Maps / Places / Geocoding (مفتاح واحد للمرحلة الحالية)
    google_maps_api_key: str = ""
    # LLM للتوصية والتقرير (OpenAI أو غيره)
    openai_api_key: str = ""
    # Add later: model_path, data_path, etc.

    @property
    def database_url(self) -> str:
        """MySQL connection URL (for SQLAlchemy etc.)."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # DB_* and MYSQL_* from .env
        extra = "ignore"


settings = Settings()
