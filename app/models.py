from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    Enum,
    Float,
    DECIMAL,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import enum
import uuid

Base = declarative_base()


# 사용자 역할 열거형
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


# SQLAlchemy 모델
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # 구글 로그인의 경우 NULL 가능
    nickname = Column(String(50), nullable=True)
    profile_image_url = Column(Text, nullable=True)
    region = Column(String(100), nullable=True)
    birth_year = Column(Integer, nullable=True)
    status = Column(String(20), default="active")

    # 사용자 선호도 및 설정 (JSONB)
    preferences = Column(
        JSONB, nullable=True
    )  # {"travel_style": [], "interests": [], "budget_range": ""}
    notification_settings = Column(JSONB, nullable=True)

    # 인증 관련
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)

    # 활동 통계
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0)

    # 구글 OAuth 관련 필드
    google_id = Column(String(100), unique=True, index=True, nullable=True)
    auth_provider = Column(String(20), default="email")  # email, google

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# 사용자 활동 로그 모델
class UserActivity(Base):
    __tablename__ = "user_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False)  # login, logout, api_call, etc.
    resource_type = Column(String(50), nullable=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Pydantic 모델 - 사용자 인증
class UserBase(BaseModel):
    email: EmailStr
    nickname: Optional[str] = None


class UserCreate(UserBase):
    password: str
    region: Optional[str] = None
    birth_year: Optional[int] = None
    role: Optional[UserRole] = UserRole.USER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPreferences(BaseModel):
    travel_style: Optional[List[str]] = (
        None  # ["adventure", "relaxation", "culture", "nature"]
    )
    interests: Optional[List[str]] = None  # ["beach", "mountain", "city", "historic"]
    budget_range: Optional[str] = None  # "low", "medium", "high", "luxury"


class UserNotificationSettings(BaseModel):
    email_notifications: bool = True
    push_notifications: bool = True
    weather_alerts: bool = True
    travel_reminders: bool = True


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    profile_image_url: Optional[str] = None
    region: Optional[str] = None
    birth_year: Optional[int] = None
    preferences: Optional[UserPreferences] = None
    notification_settings: Optional[UserNotificationSettings] = None


class UserAdminUpdate(BaseModel):
    nickname: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    role: Optional[UserRole] = None
    status: Optional[str] = None
    region: Optional[str] = None


class UserResponse(UserBase):
    id: str  # UUID as string
    nickname: Optional[str] = None
    profile_image_url: Optional[str] = None
    region: Optional[str] = None
    birth_year: Optional[int] = None
    status: str
    is_active: bool
    is_verified: bool
    role: UserRole
    preferences: Optional[Dict[str, Any]] = None
    notification_settings: Optional[Dict[str, Any]] = None
    last_login_at: Optional[datetime] = None
    login_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    id: str  # UUID as string
    email: str
    nickname: Optional[str] = None
    region: Optional[str] = None
    is_active: bool
    is_verified: bool
    role: UserRole
    status: str
    last_login_at: Optional[datetime] = None
    login_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_info: UserResponse


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


# Pydantic 모델 - 날씨 API
class WeatherRequest(BaseModel):
    city: str
    country: Optional[str] = None


class WeatherResponse(BaseModel):
    city: str
    country: str
    region: str
    temperature: float
    feels_like: float
    description: str
    icon: str
    humidity: int
    wind_speed: float
    wind_direction: str
    pressure: float
    visibility: float
    uv_index: float
    last_updated: str


class ForecastDay(BaseModel):
    date: str
    max_temp: float
    min_temp: float
    avg_temp: float
    description: str
    icon: str
    humidity: int
    chance_of_rain: int
    chance_of_snow: int
    uv_index: float


class ForecastResponse(BaseModel):
    city: str
    country: str
    region: str
    forecast: List[ForecastDay]


class FavoriteCity(BaseModel):
    city: str
    country: Optional[str] = None
    added_at: datetime


# 관리자 통계 모델
class AdminStats(BaseModel):
    total_users: int
    active_users: int
    verified_users: int
    admin_users: int
    moderator_users: int
    today_logins: int
    this_week_logins: int
    this_month_logins: int


class UserActivityResponse(BaseModel):
    id: int
    user_id: int
    activity_type: str
    description: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Pydantic 모델 - 지역 정보
class LocationInfo(BaseModel):
    city: str
    region: str
    latitude: float
    longitude: float
    description: Optional[str] = None


# Pydantic 모델 - 맛집 정보
class RestaurantBase(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    category: str  # 한식, 중식, 일식, 양식, 카페, 기타
    rating: Optional[float] = None
    price_range: Optional[str] = None  # 저렴, 보통, 고급
    description: Optional[str] = None
    operating_hours: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class RestaurantCreate(RestaurantBase):
    city: str
    region: str


class RestaurantResponse(RestaurantBase):
    id: int
    city: str
    region: str
    created_at: datetime

    class Config:
        from_attributes = True


# Pydantic 모델 - 교통 정보
class TransportationBase(BaseModel):
    name: str
    type: str  # 지하철, 버스, 택시, 기차, 공항
    description: str
    route_info: Optional[str] = None
    operating_hours: Optional[str] = None
    fare_info: Optional[str] = None
    contact: Optional[str] = None


class TransportationCreate(TransportationBase):
    city: str
    region: str


class TransportationResponse(TransportationBase):
    id: int
    city: str
    region: str
    created_at: datetime

    class Config:
        from_attributes = True


# Pydantic 모델 - 숙소 정보
class AccommodationBase(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    type: str  # 호텔, 펜션, 게스트하우스, 모텔, 리조트
    rating: Optional[float] = None
    price_range: Optional[str] = None  # 저렴, 보통, 고급, 럭셔리
    amenities: Optional[List[str]] = None  # 편의시설 목록
    description: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class AccommodationCreate(AccommodationBase):
    city: str
    region: str


class AccommodationResponse(AccommodationBase):
    id: int
    city: str
    region: str
    created_at: datetime

    class Config:
        from_attributes = True


# Pydantic 모델 - 지역 통합 정보
class CityInfoSchema(BaseModel):
    city: str
    region: str
    description: str
    attractions: Optional[List[str]] = None
    best_time_to_visit: Optional[str] = None
    population: Optional[int] = None
    area: Optional[float] = None


class CityInfoResponse(CityInfoSchema):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Pydantic 모델 - 검색 요청
class SearchRequest(BaseModel):
    city: str
    category: Optional[str] = None  # restaurant, transportation, accommodation
    keyword: Optional[str] = None
    price_range: Optional[str] = None
    rating_min: Optional[float] = None


# Pydantic 모델 - 검색 결과
class SearchResult(BaseModel):
    restaurants: List[RestaurantResponse] = []
    transportations: List[TransportationResponse] = []
    accommodations: List[AccommodationResponse] = []
    city_info: Optional[CityInfoResponse] = None


# Pydantic 모델 - 즐겨찾기
class FavoritePlaceSchema(BaseModel):
    place_id: int
    place_type: str  # restaurant, transportation, accommodation
    city: str
    added_at: datetime


class FavoritePlaceResponse(BaseModel):
    id: int
    user_id: int
    place_id: int
    place_type: str
    city: str
    added_at: datetime

    class Config:
        from_attributes = True


# Pydantic 모델 - 리뷰
class ReviewBase(BaseModel):
    rating: int  # 1-5
    comment: str
    place_id: int
    place_type: str  # restaurant, transportation, accommodation


class ReviewCreate(ReviewBase):
    pass


class ReviewResponse(ReviewBase):
    id: int
    user_id: int
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


# 맛집 정보 모델
class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    address = Column(String(500), nullable=False)
    phone = Column(String(50), nullable=True)
    category = Column(
        String(50), nullable=False, index=True
    )  # 한식, 중식, 일식, 양식, 카페, 기타
    rating = Column(Float, nullable=True)
    price_range = Column(String(20), nullable=True)  # 저렴, 보통, 고급
    description = Column(Text, nullable=True)
    operating_hours = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    city = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# 교통 정보 모델
class Transportation(Base):
    __tablename__ = "transportations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    type = Column(
        String(50), nullable=False, index=True
    )  # 지하철, 버스, 택시, 기차, 공항
    description = Column(Text, nullable=False)
    route_info = Column(Text, nullable=True)
    operating_hours = Column(String(200), nullable=True)
    fare_info = Column(String(200), nullable=True)
    contact = Column(String(100), nullable=True)
    city = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# 숙소 정보 모델
class Accommodation(Base):
    __tablename__ = "accommodations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    address = Column(String(500), nullable=False)
    phone = Column(String(50), nullable=True)
    type = Column(
        String(50), nullable=False, index=True
    )  # 호텔, 펜션, 게스트하우스, 모텔, 리조트
    rating = Column(Float, nullable=True)
    price_range = Column(String(20), nullable=True)  # 저렴, 보통, 고급, 럭셔리
    amenities = Column(Text, nullable=True)  # JSON string
    description = Column(Text, nullable=True)
    check_in = Column(String(50), nullable=True)
    check_out = Column(String(50), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    city = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# 리뷰 모델
class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    place_id = Column(Integer, nullable=False, index=True)
    place_type = Column(
        String(50), nullable=False
    )  # restaurant, transportation, accommodation
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# 지역 정보 모델
class CityInfo(Base):
    __tablename__ = "city_info"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    attractions = Column(Text, nullable=True)  # JSON string
    best_time_to_visit = Column(String(200), nullable=True)
    population = Column(Integer, nullable=True)
    area = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# 즐겨찾기 모델
class FavoritePlace(Base):
    __tablename__ = "favorite_places"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    place_id = Column(Integer, nullable=False)
    place_type = Column(
        String(50), nullable=False
    )  # restaurant, transportation, accommodation
    city = Column(String(100), nullable=False, index=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())


# 대기질 관련 모델들
class AirQualityRecord(Base):
    __tablename__ = "air_quality_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    source = Column(String(50), nullable=False)  # public_data, weather_api, local_data
    pm10_value = Column(Float, nullable=True)
    pm25_value = Column(Float, nullable=True)
    o3_value = Column(Float, nullable=True)
    no2_value = Column(Float, nullable=True)
    co_value = Column(Float, nullable=True)
    so2_value = Column(Float, nullable=True)
    aqi_value = Column(Integer, nullable=True)
    aqi_grade = Column(String(20), nullable=True)  # 좋음, 보통, 나쁨, 매우나쁨
    station_name = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AirQualityFavorite(Base):
    __tablename__ = "air_quality_favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())


class AirQualityAlert(Base):
    __tablename__ = "air_quality_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    alert_type = Column(
        String(50), nullable=False
    )  # daily_report, grade_change, health_advice
    threshold_grade = Column(String(20), nullable=True)  # 나쁨, 매우나쁨
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AirQualityHealthProfile(Base):
    __tablename__ = "air_quality_health_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True, unique=True)
    has_respiratory_condition = Column(Boolean, default=False)
    has_heart_condition = Column(Boolean, default=False)
    is_pregnant = Column(Boolean, default=False)
    age_group = Column(String(20), nullable=True)  # child, adult, elderly
    sensitivity_level = Column(String(20), default="normal")  # low, normal, high
    preferred_activities = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Pydantic 모델 - 대기질 관련
class AirQualityRecordResponse(BaseModel):
    id: int
    user_id: int
    city: str
    source: str
    pm10_value: Optional[float] = None
    pm25_value: Optional[float] = None
    o3_value: Optional[float] = None
    no2_value: Optional[float] = None
    co_value: Optional[float] = None
    so2_value: Optional[float] = None
    aqi_value: Optional[int] = None
    aqi_grade: Optional[str] = None
    station_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AirQualityFavoriteResponse(BaseModel):
    id: int
    user_id: int
    city: str
    added_at: datetime

    class Config:
        from_attributes = True


class AirQualityAlertCreate(BaseModel):
    city: str
    alert_type: str
    threshold_grade: Optional[str] = None


class AirQualityAlertResponse(BaseModel):
    id: int
    user_id: int
    city: str
    alert_type: str
    threshold_grade: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AirQualityHealthProfileCreate(BaseModel):
    has_respiratory_condition: bool = False
    has_heart_condition: bool = False
    is_pregnant: bool = False
    age_group: Optional[str] = None
    sensitivity_level: str = "normal"
    preferred_activities: Optional[List[str]] = None


class AirQualityHealthProfileResponse(BaseModel):
    id: int
    user_id: int
    has_respiratory_condition: bool
    has_heart_condition: bool
    is_pregnant: bool
    age_group: Optional[str] = None
    sensitivity_level: str
    preferred_activities: Optional[List[str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AirQualityHistoryResponse(BaseModel):
    city: str
    records: List[AirQualityRecordResponse]
    summary: dict


class AirQualityUserStats(BaseModel):
    total_queries: int
    favorite_cities: List[str]
    most_queried_city: Optional[str] = None
    average_aqi: Optional[float] = None
    health_profile: Optional[AirQualityHealthProfileResponse] = None


# 여행 계획 관련 모델
class TravelPlan(Base):
    __tablename__ = "travel_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(String, nullable=False)  # Date string (YYYY-MM-DD)
    end_date = Column(String, nullable=False)  # Date string (YYYY-MM-DD)
    budget = Column(DECIMAL(10, 2), nullable=True)
    participants = Column(Integer, default=1)
    transportation = Column(String(50), nullable=True)
    status = Column(
        String(20), default="draft"
    )  # draft, confirmed, completed, cancelled
    itinerary = Column(JSONB, nullable=True)  # 여행 일정 상세 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Destination(Base):
    __tablename__ = "destinations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    latitude = Column(DECIMAL(10, 8), nullable=True)
    longitude = Column(DECIMAL(11, 8), nullable=True)
    rating = Column(DECIMAL(3, 1), default=0.0)
    image_url = Column(Text, nullable=True)
    gallery_urls = Column(ARRAY(Text), nullable=True)  # PostgreSQL array
    status = Column(String(20), default="active")
    recommendation_weight = Column(DECIMAL(3, 2), default=1.0)
    weather_tags = Column(ARRAY(String(50)), nullable=True)  # PostgreSQL array
    activity_tags = Column(ARRAY(String(50)), nullable=True)  # PostgreSQL array
    season_preferences = Column(JSONB, nullable=True)
    popularity_score = Column(DECIMAL(5, 2), default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    destination_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    forecast_date = Column(String, nullable=False)  # Date string (YYYY-MM-DD)
    temperature_max = Column(Float, nullable=True)
    temperature_min = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    weather_condition = Column(String(100), nullable=True)
    precipitation_prob = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    uv_index = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Pydantic 모델 - 여행 계획
class TravelPlanCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: str
    end_date: str
    budget: Optional[float] = None
    participants: int = 1
    transportation: Optional[str] = None


class TravelPlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[float] = None
    participants: Optional[int] = None
    transportation: Optional[str] = None
    status: Optional[str] = None
    itinerary: Optional[dict] = None


class TravelPlanResponse(BaseModel):
    id: str  # UUID as string
    user_id: str  # UUID as string
    title: str
    description: Optional[str] = None
    start_date: str
    end_date: str
    budget: Optional[float] = None
    participants: int
    transportation: Optional[str] = None
    status: str
    itinerary: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Pydantic 모델 - 여행지
class DestinationCreate(BaseModel):
    name: str
    category: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None
    gallery_urls: Optional[List[str]] = None
    weather_tags: Optional[List[str]] = None
    activity_tags: Optional[List[str]] = None
    season_preferences: Optional[dict] = None


class DestinationResponse(BaseModel):
    id: str  # UUID as string
    name: str
    category: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: float
    image_url: Optional[str] = None
    gallery_urls: Optional[List[str]] = None
    status: str
    recommendation_weight: float
    weather_tags: Optional[List[str]] = None
    activity_tags: Optional[List[str]] = None
    season_preferences: Optional[Dict[str, Any]] = None
    popularity_score: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Pydantic 모델 - 여행지 추천
class RecommendationRequest(BaseModel):
    travel_dates: List[str]  # ["2024-08-01", "2024-08-03"]
    origin: Dict[str, float]  # {"latitude": 37.5665, "longitude": 126.978}
    preferences: Optional[Dict[str, Any]] = None  # 사용자 선호도
    weather_preferences: Optional[Dict[str, Any]] = None  # 날씨 선호도
    max_distance: Optional[int] = 500  # km
    budget_range: Optional[str] = None  # "low", "medium", "high"


class RecommendationResponse(BaseModel):
    destinations: List[DestinationResponse]
    weather_forecast: Optional[Dict[str, Any]] = None
    total_results: int
    recommendation_score: Optional[float] = None


# 구글 OAuth 관련 모델
class GoogleLoginRequest(BaseModel):
    id_token: str


class GoogleLoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_info: UserResponse
    is_new_user: bool


class GoogleAuthUrlResponse(BaseModel):
    auth_url: str
    state: str


# 이메일 인증 관련 모델
class EmailVerificationRequest(BaseModel):
    email: str
    username: Optional[str] = None


class EmailVerificationConfirm(BaseModel):
    email: str
    verification_code: str


class EmailVerificationResponse(BaseModel):
    message: str
    success: bool


class ResendVerificationRequest(BaseModel):
    email: str


# 관리자 관련 모델
class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    status = Column(String(20), default="active")
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0)
    failed_login_attempts = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AdminRole(Base):
    __tablename__ = "admin_roles"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, nullable=False, index=True)
    role_id = Column(Integer, nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False)
    source = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    context = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Pydantic 모델 - 관리자 시스템
class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class AdminResponse(BaseModel):
    id: int
    email: str
    name: str
    phone: Optional[str] = None
    status: str
    last_login_at: Optional[datetime] = None
    login_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class AdminToken(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    admin_info: AdminResponse


# Pydantic 모델 - 대시보드 통계
class DashboardStats(BaseModel):
    realtime_metrics: dict
    daily_stats: dict
    alerts: List[dict] = []


class UserAnalytics(BaseModel):
    total_users: int
    active_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    user_growth_rate: float
    retention_rate: float


class SystemMetrics(BaseModel):
    api_response_time: float
    database_query_time: float
    cache_hit_ratio: float
    error_rate: float
    uptime_percentage: float


class ContentStats(BaseModel):
    total_destinations: int
    active_destinations: int
    total_travel_plans: int
    completed_travel_plans: int
    total_reviews: int
    average_rating: float


# 이메일 인증 모델
class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    verification_code = Column(String(10), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# API 표준 응답 형식
class StandardResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[dict] = None
    pagination: Optional[dict] = None
    timestamp: str


class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[List[dict]] = None
