from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "CareAssist AI"
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'careassist.db').as_posix()}"
    secret_key: str = "development-only-change-me"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:4200"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    chroma_persist_directory: str = str(BACKEND_DIR / "data" / "chroma")
    upload_directory: str = str(BACKEND_DIR / "data" / "uploads")
    max_upload_size_mb: int = 10
    clinic_timezone: str = "UTC"
    clinic_open_time: str = "08:00"
    clinic_close_time: str = "17:00"
    clinic_working_days: str = "0,1,2,3,4"
    appointment_duration_minutes: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def working_day_numbers(self) -> set[int]:
        try:
            days = {int(day.strip()) for day in self.clinic_working_days.split(",") if day.strip()}
        except ValueError as exc:
            raise ValueError("CLINIC_WORKING_DAYS must contain weekday numbers 0 through 6") from exc
        if not days.issubset(set(range(7))):
            raise ValueError("CLINIC_WORKING_DAYS must contain weekday numbers 0 through 6")
        return days

    @property
    def clinic_zone(self) -> ZoneInfo:
        return ZoneInfo(self.clinic_timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
