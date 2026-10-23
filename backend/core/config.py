from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DEBUG: bool = True
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"

    MONGO_URI: str = ""
    MONGO_DB_NAME: str = "gomechanic_tech_support"

    JWT_SECRET: str = "insecure-dev-key-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TTL_MINUTES: int = 60
    JWT_REFRESH_TTL_DAYS: int = 7

    KARIX_API_BASE_URL: str = "https://api.karix.io"
    KARIX_API_KEY: str = ""
    KARIX_SOURCE_ADDRESS: str = ""

    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    MEDIA_URL: str = "/media/"
    MEDIA_ROOT: str = "media"

    @property
    def cors_origins(self) -> list[str]:
        return _split_csv(self.CORS_ALLOWED_ORIGINS)

    @property
    def media_root_path(self) -> Path:
        path = Path(self.MEDIA_ROOT)
        return path if path.is_absolute() else BASE_DIR / path


settings = Settings()
