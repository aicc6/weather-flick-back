from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
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
