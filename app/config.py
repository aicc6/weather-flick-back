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

    # JWT 설정
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # PostgreSQL 데이터베이스 설정
    database_host: str
    database_port: int
    database_user: str
    database_password: str
    database_name: str

    # WeatherAPI 설정
    weather_api_key: str = "your_weather_api_key_here"
    weather_api_url: str = "http://api.weatherapi.com/v1"

    @property
    def database_url(self) -> str:
        """PostgreSQL 데이터베이스 URL 생성"""
        return f"postgresql://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
