from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 기본 설정
    app_name: str = "Weather Flick API"
    app_version: str = "1.0.0"
    debug: bool = False

    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS 설정
    cors_origins: list = ["*"]

    # 외부 API 설정 (향후 사용)
    weather_api_key: Optional[str] = None
    weather_api_url: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
