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
    database_host: Optional[str] = None
    database_port: Optional[int] = None
    database_user: Optional[str] = None
    database_password: Optional[str] = None
    database_name: Optional[str] = None

    # WeatherAPI 설정
    weather_api_key: str = "your_weather_api_key_here"
    weather_api_url: str = "http://api.weatherapi.com/v1"

    # 기상청 API 설정
    kma_api_key: str = "your_kma_api_key_here"

    # 카카오 API 설정 (맛집, 장소 검색)
    kakao_api_key: str = "your_kakao_api_key_here"
    kakao_api_url: str = "https://dapi.kakao.com/v2/local"

    # 네이버 API 설정 (블로그, 뉴스 검색)
    naver_client_id: str = "your_naver_client_id_here"
    naver_client_secret: str = "your_naver_client_secret_here"
    naver_api_url: str = "https://openapi.naver.com/v1"

    # 구글 Places API 설정 (장소 검색)
    google_api_key: str = "your_google_api_key_here"
    google_places_url: str = "https://maps.googleapis.com/maps/api/place"

    # 공공데이터포털 API 설정 (관광정보, 대기질 정보)
    public_data_api_key: str = "your_public_data_api_key_here"
    public_data_api_url: str = "http://api.visitkorea.or.kr/openapi/service/rest/KorService"

    # 한국관광공사 API 설정
    korea_tourism_api_key: str = "your_korea_tourism_api_key_here"
    korea_tourism_api_url: str = "http://api.visitkorea.or.kr/openapi/service/rest/KorService"

    @property
    def database_url(self) -> str:
        """PostgreSQL 데이터베이스 URL 생성"""
        return f"postgresql://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
