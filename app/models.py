import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Boolean,
    DateTime,
    Date,
    Enum,
    ForeignKey,
    DECIMAL,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


Base = declarative_base()


class AdminStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"


class TravelPlanStatus(enum.Enum):
    PLANNING = "PLANNING"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class UserRole(enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True, "autoload_replace": False}
    user_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # OAuth 사용자는 비밀번호가 없을 수 있음
    nickname = Column(String, unique=True, index=True, nullable=False)
    profile_image = Column(String)
    preferences = Column(JSONB)
    preferred_region = Column(String)  # 선호 지역
    preferred_theme = Column(String)   # 선호 테마
    bio = Column(Text)                 # 자기소개
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    google_id = Column(String, unique=True, nullable=True)  # 구글 OAuth ID
    auth_provider = Column(String, default="local")  # 인증 제공자 (local, google 등)
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # id 속성을 user_id의 별칭으로 추가
    @property
    def id(self):
        return self.user_id

    travel_plans = relationship("TravelPlan", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    activity_logs = relationship("UserActivityLog", back_populates="user")


class Admin(Base):
    __tablename__ = "admins"
    admin_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    phone = Column(String)
    status = Column(Enum(AdminStatus), default=AdminStatus.ACTIVE)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    roles = relationship("AdminRole", back_populates="admin")


class Role(Base):
    __tablename__ = "roles"
    role_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    admins = relationship("AdminRole", back_populates="role")


class AdminRole(Base):
    __tablename__ = "admin_roles"
    admin_id = Column(Integer, ForeignKey("admins.admin_id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.role_id"), primary_key=True)
    assigned_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    admin = relationship("Admin", back_populates="roles")
    role = relationship("Role", back_populates="admins")


class Destination(Base):
    __tablename__ = "destinations"
    destination_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    name = Column(String, nullable=False, index=True)
    province = Column(String, nullable=False, index=True) # 도/광역시
    region = Column(String, index=True) # 시/군/구
    category = Column(String)
    is_indoor = Column(Boolean, default=False) # 실내/실외 여부
    tags = Column(JSONB) # 여행지 특성 태그
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    amenities = Column(JSONB)
    image_url = Column(String)
    rating = Column(Float)
    recommendation_weight = Column(DECIMAL(3, 2))
    created_at = Column(DateTime, server_default=func.now())

    weather_data = relationship("WeatherData", back_populates="destination")
    reviews = relationship("Review", back_populates="destination")


class TravelPlan(Base):
    __tablename__ = "travel_plans"
    plan_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    budget = Column(DECIMAL(10, 2))
    status = Column(Enum(TravelPlanStatus), default=TravelPlanStatus.PLANNING)
    itinerary = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="travel_plans")
    reviews = relationship("Review", back_populates="travel_plan")


class WeatherData(Base):
    __tablename__ = "weather_data"
    weather_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=True
    )
    # 기상청 격자 좌표
    grid_x = Column(Integer)  # nx: 예보지점 X 좌표
    grid_y = Column(Integer)  # ny: 예보지점 Y 좌표

    # 예보 날짜와 시간
    forecast_date = Column(Date, nullable=False)
    forecast_time = Column(String)  # 예보시간 (HHMM 형식)
    base_date = Column(Date)  # 발표일자
    base_time = Column(String)  # 발표시각

    # 기온 정보
    temperature = Column(Float)  # TMP: 1시간 기온 (℃)
    temperature_max = Column(Float)  # TMX: 일 최고기온 (℃)
    temperature_min = Column(Float)  # TMN: 일 최저기온 (℃)

    # 습도 및 강수 정보
    humidity = Column(Float)  # REH: 습도 (%)
    precipitation_probability = Column(Float)  # POP: 강수확률 (%)
    precipitation_type = Column(String)  # PTY: 강수형태 (없음/비/비눈/눈)

    # 하늘 상태
    sky_condition = Column(String)  # SKY: 하늘상태 (맑음/구름많음/흐림)
    weather_condition = Column(String)  # 종합 날씨 상태

    # 지역 정보
    region_name = Column(String)  # 지역명

    # 원본 데이터
    raw_data = Column(JSONB)  # 원본 API 응답 데이터

    created_at = Column(DateTime, server_default=func.now())

    destination = relationship("Destination", back_populates="weather_data")


class Review(Base):
    __tablename__ = "reviews"
    review_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    travel_plan_id = Column(
        UUID(as_uuid=True), ForeignKey("travel_plans.plan_id"), nullable=True
    )
    rating = Column(Integer, nullable=False)
    content = Column(Text)
    photos = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="reviews")
    destination = relationship("Destination", back_populates="reviews")
    travel_plan = relationship("TravelPlan", back_populates="reviews")


class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"
    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    activity_type = Column(String, nullable=False)
    resource_type = Column(String)
    details = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="activity_logs")


class SystemLog(Base):
    __tablename__ = "system_logs"
    log_id = Column(Integer, primary_key=True, index=True)
    level = Column(String, nullable=False)
    source = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    context = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class FavoritePlace(Base):
    __tablename__ = "favorite_places"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    place_name = Column(String, nullable=False)
    place_type = Column(String, nullable=False)  # restaurant, accommodation, transport
    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class Restaurant(Base):
    __tablename__ = "restaurants"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    address = Column(String, nullable=False)
    phone = Column(String)
    rating = Column(Float)
    price_range = Column(String)
    opening_hours = Column(JSONB)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class Transportation(Base):
    __tablename__ = "transportation"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # bus, subway, taxi, etc.
    route = Column(String)
    schedule = Column(JSONB)
    fare = Column(String)
    contact = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class Accommodation(Base):
    __tablename__ = "accommodations"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # hotel, motel, guesthouse, etc.
    address = Column(String, nullable=False)
    phone = Column(String)
    rating = Column(Float)
    price_range = Column(String)
    amenities = Column(JSONB)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class CityInfo(Base):
    __tablename__ = "city_info"
    id = Column(Integer, primary_key=True, index=True)
    city_name = Column(String, nullable=False, unique=True)
    region = Column(String, nullable=False)
    population = Column(Integer)
    area = Column(Float)
    description = Column(Text)
    attractions = Column(JSONB)
    weather_info = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())


# Pydantic 모델들
class WeatherRequest(BaseModel):
    city: str
    country: Optional[str] = None


class WeatherCondition(BaseModel):
    temperature: float
    feels_like: float
    humidity: int
    pressure: float
    condition: str
    description: str
    icon: str
    wind_speed: float
    wind_direction: int
    visibility: float
    uv_index: float


class WeatherResponse(BaseModel):
    city: str
    country: str
    current: WeatherCondition
    timezone: str
    local_time: str


class ForecastDay(BaseModel):
    date: str
    temperature_max: float
    temperature_min: float
    condition: str
    description: str
    icon: str
    humidity: int
    wind_speed: float
    precipitation_chance: float


class ForecastResponse(BaseModel):
    city: str
    country: str
    forecast: List[ForecastDay]
    timezone: str


# 인증 관련 Pydantic 모델들
class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    email: str
    password: str
    nickname: str


class UserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    nickname: Optional[str] = None
    profile_image: Optional[str] = None
    preferred_region: Optional[str] = None
    preferred_theme: Optional[str] = None
    bio: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_info: UserResponse


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    profile_image: Optional[str] = None
    preferences: Optional[List[str]] = None
    preferred_region: Optional[str] = None
    preferred_theme: Optional[str] = None
    bio: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class GoogleLoginRequest(BaseModel):
    code: str
    redirect_uri: str


class GoogleLoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class GoogleAuthUrlResponse(BaseModel):
    auth_url: str


class EmailVerificationRequest(BaseModel):
    email: str
    nickname: str


class EmailVerificationConfirm(BaseModel):
    email: str
    code: str


class EmailVerificationResponse(BaseModel):
    message: str
    success: bool


class ResendVerificationRequest(BaseModel):
    email: str
    nickname: str


# 추천 및 여행 계획 관련 모델들
class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class PaginationInfo(BaseModel):
    page: int
    page_size: int
    total_count: int
    total_pages: int


class DestinationCreate(BaseModel):
    name: str
    province: str
    region: Optional[str] = None
    category: Optional[str] = None
    is_indoor: Optional[bool] = False
    tags: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    amenities: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None


class DestinationResponse(BaseModel):
    destination_id: uuid.UUID
    name: str
    province: str
    region: Optional[str] = None
    category: Optional[str] = None
    is_indoor: Optional[bool] = None
    tags: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    amenities: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    recommendation_weight: Optional[float] = None

    class Config:
        from_attributes = True


class RecommendationRequest(BaseModel):
    destination_types: Optional[List[str]] = None
    budget_range: Optional[Dict[str, float]] = None
    travel_dates: Optional[Dict[str, str]] = None
    preferences: Optional[Dict[str, Any]] = None


class RecommendationResponse(BaseModel):
    destinations: List[DestinationResponse]
    total_count: int
    recommendation_score: float


class TravelPlanCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: str
    end_date: str
    budget: Optional[float] = None
    itinerary: Optional[Dict[str, Any]] = None


class TravelPlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[float] = None
    status: Optional[str] = None
    itinerary: Optional[Dict[str, Any]] = None


class TravelPlanResponse(BaseModel):
    plan_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: Optional[str] = None
    start_date: str
    end_date: str
    budget: Optional[float] = None
    status: str
    itinerary: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# 지역 정보 관련 모델들
class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    location: Optional[str] = None
    limit: Optional[int] = 10


class SearchResult(BaseModel):
    results: List[Dict[str, Any]]
    total_count: int
    category: str


class RestaurantResponse(BaseModel):
    id: str
    name: str
    category: str
    address: str
    phone: Optional[str] = None
    rating: Optional[float] = None
    price_range: Optional[str] = None
    opening_hours: Optional[Dict[str, Any]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class AccommodationResponse(BaseModel):
    id: str
    name: str
    type: str  # hotel, motel, guesthouse, etc.
    address: str
    phone: Optional[str] = None
    rating: Optional[float] = None
    price_range: Optional[str] = None
    amenities: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TransportationResponse(BaseModel):
    id: str
    name: str
    type: str  # bus, subway, taxi, etc.
    route: Optional[str] = None
    schedule: Optional[Dict[str, Any]] = None
    fare: Optional[str] = None
    contact: Optional[str] = None


class CityInfoResponse(BaseModel):
    city_name: str
    region: str
    population: Optional[int] = None
    area: Optional[float] = None
    description: Optional[str] = None
    attractions: Optional[List[str]] = None
    weather_info: Optional[Dict[str, Any]] = None


class FavoritePlaceResponse(BaseModel):
    id: int
    place_name: str
    place_type: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    destination_id: uuid.UUID
    travel_plan_id: Optional[uuid.UUID] = None
    rating: int
    content: Optional[str] = None
    photos: Optional[List[str]] = None


class ReviewResponse(BaseModel):
    review_id: uuid.UUID
    user_id: uuid.UUID
    destination_id: uuid.UUID
    travel_plan_id: Optional[uuid.UUID] = None
    rating: int
    content: Optional[str] = None
    photos: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# 사용자 활동 로그 테이블 (이미 UserActivityLog가 있으므로 별칭으로 사용)
UserActivity = UserActivityLog
