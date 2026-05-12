from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    app_name: str = "The Librarian API"
    database_url: str
    cors_origins: list[str] = ["https://thelibrarian-sigma.vercel.app","https://thelibrarian-git-master-global-techresolute-app.vercel.app",]
    public_backend_url: str | None = None
    max_pdf_upload_mb: int = 150
    max_cover_upload_mb: int = 10

    secret_key: str
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    jwt_algorithm: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()