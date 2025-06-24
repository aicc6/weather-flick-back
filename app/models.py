from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import enum

Base = declarative_base()

# 사용자 역할 열거형
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

# SQLAlchemy 모델
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    profile_image = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# 사용자 활동 로그 모델
class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    activity_type = Column(String(100), nullable=False)  # login, logout, api_call, etc.
    description = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Pydantic 모델 - 사용자 인증
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str
    role: Optional[UserRole] = UserRole.USER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None

class UserAdminUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    role: Optional[UserRole] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    role: UserRole
    profile_image: Optional[str] = None
    bio: Optional[str] = None
    last_login: Optional[datetime] = None
    login_count: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    is_verified: bool
    role: UserRole
    last_login: Optional[datetime] = None
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
    category = Column(String(50), nullable=False, index=True)  # 한식, 중식, 일식, 양식, 카페, 기타
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
    type = Column(String(50), nullable=False, index=True)  # 지하철, 버스, 택시, 기차, 공항
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
    type = Column(String(50), nullable=False, index=True)  # 호텔, 펜션, 게스트하우스, 모텔, 리조트
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
    place_type = Column(String(50), nullable=False)  # restaurant, transportation, accommodation
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
    place_type = Column(String(50), nullable=False)  # restaurant, transportation, accommodation
    city = Column(String(100), nullable=False, index=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
