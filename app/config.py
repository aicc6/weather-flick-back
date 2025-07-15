"""Application configuration settings."""

import os

from dotenv import load_dotenv
from pydantic import validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings configuration."""

    # 기본 설정
    app_name: str = "Weather Flick API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS 설정
    cors_origins: list[str] = ["*"]

    # JWT 설정
    secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 10080  # 7 days

    # 데이터베이스 설정
    database_url: str = os.getenv("DATABASE_URL", "")
    database_host: str | None = os.getenv("DATABASE_HOST")
    database_port: int | None = int(os.getenv("DATABASE_PORT", "5432"))
    database_user: str | None = os.getenv("DATABASE_USER")
    database_password: str | None = os.getenv("DATABASE_PASSWORD")
    database_name: str | None = os.getenv("DATABASE_NAME")

    # 이메일 설정
    mail_username: str = os.getenv("MAIL_USERNAME", "")
    mail_password: str = os.getenv("MAIL_PASSWORD", "")
    mail_from: str = os.getenv("MAIL_FROM", "noreply@weatherflick.com")
    mail_port: int = int(os.getenv("MAIL_PORT", "587"))
    mail_server: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_starttls: bool = os.getenv("MAIL_STARTTLS", "true").lower() == "true"
    mail_ssl_tls: bool = os.getenv("MAIL_SSL_TLS", "false").lower() == "true"
    mail_from_name: str = os.getenv("MAIL_FROM_NAME", "Weather Flick")

    # Redis 설정
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # 외부 API 설정
    weather_api_key: str = os.getenv("WEATHER_API_KEY", "")
    weather_api_url: str = "http://api.weatherapi.com/v1"

    kma_api_key: str = os.getenv("KMA_API_KEY", "")
    kma_forecast_url: str = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"

    kakao_api_key: str = os.getenv("KAKAO_API_KEY", "")
    kakao_api_url: str = "https://dapi.kakao.com/v2/local"

    naver_client_id: str = os.getenv("NAVER_CLIENT_ID", "")
    naver_client_secret: str = os.getenv("NAVER_CLIENT_SECRET", "")
    naver_api_url: str = "https://openapi.naver.com/v1"

    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    google_places_url: str = "https://maps.googleapis.com/maps/api/place"
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
    )

    korea_tourism_api_key: str = os.getenv("KOREA_TOURISM_API_KEY", "")
    korea_tourism_api_url: str = (
        "http://api.visitkorea.or.kr/openapi/service/rest/KorService"
    )

    # OpenAI 설정
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "1500"))
    openai_temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

    # 교통정보 API 설정
    odsay_api_key: str = os.getenv("ODsay_API_KEY", "")
    odsay_api_url: str = "https://api.odsay.com/v1/api"

    tmap_api_key: str = os.getenv("TMAP_API_KEY", "")
    tmap_api_url: str = "https://apis.openapi.sk.com/tmap"

    # 프론트엔드 설정
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # 헬스체크를 위한 API URL들
    @property
    def KMA_API_URL(self) -> str:
        """기상청 API 기본 URL"""
        return f"{self.kma_forecast_url}/getVilageFcst"

    @property
    def TOUR_API_BASE_URL(self) -> str:
        """한국관광공사 API 기본 URL"""
        return self.korea_tourism_api_url

    @property
    def GOOGLE_PLACES_API_URL(self) -> str:
        """Google Places API 기본 URL"""
        return f"{self.google_places_url}/nearbysearch/json"

    @property
    def NAVER_MAP_API_URL(self) -> str:
        """네이버 지도 API 기본 URL"""
        return f"{self.naver_api_url}/map-geocode/v2/geocode"

    @validator("secret_key")
    def secret_key_must_be_set(cls, v: str) -> str:
        """Validate that secret key is set."""
        if not v:
            raise ValueError("JWT_SECRET_KEY must be set")
        return v

    @validator("database_url")
    def database_url_must_be_set(cls, v: str) -> str:
        """Validate that database URL is set."""
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as list."""
        if self.is_production:
            return [self.frontend_url]
        return self.cors_origins

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# 설정 인스턴스 생성
settings = Settings()

# 필수 환경 변수 검증
if not settings.secret_key:
    raise ValueError("JWT_SECRET_KEY environment variable is required")

if not settings.database_url:
    raise ValueError("DATABASE_URL environment variable is required")
