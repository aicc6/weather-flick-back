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
    user_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)  # auth.py에서 사용하는 필드명
    nickname = Column(String)
    profile_image = Column(String)
    preferences = Column(JSONB)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
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
    name = Column(String, nullable=False)
    region = Column(String)
    category = Column(String)
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
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    forecast_date = Column(Date, nullable=False)
    temperature_max = Column(Float)
    temperature_min = Column(Float)
    humidity = Column(Float)
    weather_condition = Column(String)
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
    nickname: Optional[str] = None


class UserResponse(BaseModel):
    user_id: str
    email: str
    nickname: Optional[str] = None
    profile_image: Optional[str] = None
    role: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    profile_image: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


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


class DestinationResponse(BaseModel):
    destination_id: str
    name: str
    region: Optional[str] = None
    category: Optional[str] = None
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
    plan_id: str
    user_id: str
    title: str
    description: Optional[str] = None
    start_date: str
    end_date: str
    budget: Optional[float] = None
    status: str
    itinerary: Optional[Dict[str, Any]] = None
    created_at: str

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
    created_at: str

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    destination_id: str
    travel_plan_id: Optional[str] = None
    rating: int
    content: Optional[str] = None
    photos: Optional[List[str]] = None


class ReviewResponse(BaseModel):
    review_id: str
    user_id: str
    destination_id: str
    travel_plan_id: Optional[str] = None
    rating: int
    content: Optional[str] = None
    photos: Optional[List[str]] = None
    created_at: str

    class Config:
        from_attributes = True


# 사용자 활동 로그 테이블 (이미 UserActivityLog가 있으므로 별칭으로 사용)
UserActivity = UserActivityLog
