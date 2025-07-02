import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

load_dotenv()

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

    # 데이터베이스 설정
    database_host: Optional[str] = None
    database_port: Optional[int] = None
    database_user: Optional[str] = None
    database_password: Optional[str] = None
    database_name: Optional[str] = None

    # 이메일 설정
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "noreply@weatherflick.com"
    mail_port: int = 587
    mail_server: str = "smtp.gmail.com"
    mail_starttls: bool = True
    mail_ssl_tls: bool = False
    mail_from_name: str = "Weather Flick"

    # WeatherAPI 설정
    weather_api_key: str = ""
    weather_api_url: str = "http://api.weatherapi.com/v1"

    # 기상청 API 설정
    kma_api_key: str = ""

    # 카카오 API 설정
    kakao_api_key: str = ""
    kakao_api_url: str = "https://dapi.kakao.com/v2/local"

    # 네이버 API 설정
    naver_client_id: str = ""
    naver_client_secret: str = ""
    naver_api_url: str = "https://openapi.naver.com/v1"

    # 구글 API 설정
    google_api_key: str = ""
    google_places_url: str = "https://maps.googleapis.com/maps/api/place"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # 공공데이터포털 API 설정
    public_data_api_key: str = ""
    public_data_api_url: str = "http://api.visitkorea.or.kr/openapi/service/rest/KorService"

    # 한국관광공사 API 설정
    korea_tourism_api_key: str = ""
    korea_tourism_api_url: str = "http://api.visitkorea.or.kr/openapi/service/rest/KorService"

    # 구글 GCP API 키 (Geocoding 등)
    gcp_api_key: str = ""

    @property
    def database_url(self) -> str:
        """데이터베이스 URL 생성 - PostgreSQL이 설정되지 않으면 SQLite 사용"""
        if all([self.database_host, self.database_user, self.database_password, self.database_name]):
            return f"postgresql://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port or 5432}/{self.database_name}"
        else:
            # SQLite 사용 (개발 환경)
            return "sqlite:///./weather_flick.db"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
