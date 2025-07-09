import enum
import uuid
from datetime import datetime, date
from typing import Any, Optional, List

from pydantic import BaseModel
from sqlalchemy import (
    DECIMAL,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

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
    hashed_password = Column(
        String, nullable=True
    )  # OAuth 사용자는 비밀번호가 없을 수 있음
    nickname = Column(String, index=True, nullable=False)
    profile_image = Column(String)
    preferences = Column(JSONB)
    preferred_region = Column(String)  # 선호 지역
    preferred_theme = Column(String)  # 선호 테마
    bio = Column(Text)  # 자기소개
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
    province = Column(String, nullable=False, index=True)  # 도/광역시
    region = Column(String, index=True)  # 시/군/구
    category = Column(String)
    is_indoor = Column(Boolean, default=False)  # 실내/실외 여부
    tags = Column(JSONB)  # 여행지 특성 태그
    latitude = Column(Float)
    longitude = Column(Float)
    amenities = Column(JSONB)
    image_url = Column(String)
    rating = Column(Float)
    recommendation_weight = Column(Float)
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
    budget = Column(Float)
    status = Column(Enum(TravelPlanStatus), default=TravelPlanStatus.PLANNING)
    itinerary = Column(JSONB)
    participants = Column(Integer, nullable=True)
    transportation = Column(String, nullable=True)
    start_location = Column(String, nullable=True)  # 출발지
    weather_info = Column(JSONB, nullable=True)  # 날씨 정보
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="travel_plans")
    reviews = relationship("Review", back_populates="travel_plan")


# 성능 개선을 위한 복합 인덱스
Index("idx_travel_plan_user_status", TravelPlan.user_id, TravelPlan.status)
Index("idx_travel_plan_dates", TravelPlan.start_date, TravelPlan.end_date)


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


# WeatherData 성능 최적화 인덱스
Index(
    "idx_weather_forecast_location",
    WeatherData.forecast_date,
    WeatherData.grid_x,
    WeatherData.grid_y,
)
Index(
    "idx_weather_destination_date",
    WeatherData.destination_id,
    WeatherData.forecast_date,
)


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


# Review 성능 최적화 인덱스
Index("idx_review_destination_date", Review.destination_id, Review.created_at)
Index("idx_review_user_rating", Review.user_id, Review.rating)


class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"
    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    activity_type = Column(String, nullable=False)
    resource_type = Column(String)
    details = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="activity_logs")


class ChatMessage(Base):
    """챗봇 메시지 테이블"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    message = Column(Text, nullable=False)
    sender = Column(String, nullable=False)  # 'user' 또는 'bot'
    context = Column(JSONB, nullable=True)  # 대화 컨텍스트
    suggestions = Column(JSONB, nullable=True)  # 추천 질문 목록
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    user = relationship("User", backref="chat_messages")


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
    """음식점 정보 테이블 - 한국관광공사 API 데이터 기반 (통합됨)"""
    __tablename__ = "restaurants"
    __table_args__ = {"extend_existing": True, "autoload_replace": False}

    # Primary Key (복합키)
    content_id = Column(String, primary_key=True)
    region_code = Column(String, ForeignKey("regions.region_code"), primary_key=True)

    # Foreign Keys
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    restaurant_name = Column(String, nullable=False, index=True)
    category_code = Column(String)
    sub_category_code = Column(String)

    # 주소 및 위치 정보
    address = Column(String)
    detail_address = Column(String)
    zipcode = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    # 연락처 정보
    tel = Column(String)
    homepage = Column(String)

    # 음식점 정보
    cuisine_type = Column(String)
    specialty_dish = Column(String)
    operating_hours = Column(String)
    rest_date = Column(String)
    reservation_info = Column(String)

    # 편의시설
    credit_card = Column(String)
    smoking = Column(String)
    parking = Column(String)
    room_available = Column(String)
    children_friendly = Column(String)
    takeout = Column(String)
    delivery = Column(String)

    # 설명 및 이미지
    overview = Column(Text)
    first_image = Column(String)
    first_image_small = Column(String)

    # 메타데이터
    data_quality_score = Column(Float)
    processing_status = Column(String, default="processed")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_sync_at = Column(DateTime, server_default=func.now())


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
    """숙박시설 정보 테이블 - 한국관광공사 API 데이터 기반 (통합됨)"""
    __tablename__ = "accommodations"
    __table_args__ = {"extend_existing": True, "autoload_replace": False}

    # Primary Key - 새로운 데이터 구조에 맞춘 변경
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(String, ForeignKey("regions.region_code"), nullable=False, index=True)
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보 - 한국관광공사 API 스키마에 맞춤
    accommodation_name = Column(String, nullable=False)  # 실제 DB 컬럼명
    accommodation_type = Column(String, nullable=False)  # 실제 DB 컬럼명
    address = Column(String, nullable=False)
    tel = Column(String)  # 실제 DB 컬럼명

    # 선택적 컬럼들 (실제 DB에 존재하지 않을 수 있음)
    # rating = Column(Float)
    # price_range = Column(String)
    # amenities = Column(JSONB)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    # 새로운 상세 필드들 추가 (실제 DB에 존재하지 않을 수 있음)
    # category_code = Column(String(10))
    # sub_category_code = Column(String(10))
    # detail_address = Column(String)
    # zipcode = Column(String(10))
    # homepage = Column(Text)

    # 숙박 정보 (실제 DB에 존재하지 않을 수 있음)
    # room_count = Column(String)
    # checkin_time = Column(String)
    # checkout_time = Column(String)
    parking = Column(String)
    # cooking = Column(String)
    # room_amenities = Column(Text)

    # 부대시설 (실제 DB에 존재하지 않을 수 있음)
    # barbecue = Column(String)
    # beauty = Column(String)
    # bicycle = Column(String)
    # campfire = Column(String)
    # fitness = Column(String)
    # karaoke = Column(String)
    # public_bath = Column(String)
    # public_pc = Column(String)
    # sauna = Column(String)
    # seminar = Column(String)
    # sports = Column(String)
    # pickup_service = Column(String)

    # 설명 및 이미지 (실제 DB에 존재하지 않을 수 있음)
    # description = Column(Text)
    # overview = Column(Text)
    # first_image = Column(String)
    # first_image_small = Column(String)

    # API 원본 필드 (실제 DB에 존재하지 않을 수 있음)
    # booktour = Column(String(1))
    # createdtime = Column(String(14))
    # modifiedtime = Column(String(14))
    # telname = Column(String(100))
    # faxno = Column(String(50))
    # mlevel = Column(Integer)

    # JSON 데이터 (실제 DB에 존재하지 않을 수 있음)
    # detail_intro_info = Column(JSONB)
    # detail_additional_info = Column(JSONB)

    # 메타데이터 (실제 DB에 존재하지 않을 수 있음)
    # data_quality_score = Column(DECIMAL(5, 2))
    # processing_status = Column(String(20), default="processed")
    # updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    # last_sync_at = Column(DateTime, server_default=func.now())

    # 기존 API 호환성을 위한 프로퍼티
    @property
    def id(self):
        """기존 API 호환성을 위한 id 프로퍼티"""
        return self.content_id

    @property
    def name(self):
        """기존 API 호환성을 위한 name 프로퍼티"""
        return self.accommodation_name

    @property
    def type(self):
        """기존 API 호환성을 위한 type 프로퍼티"""
        return self.accommodation_type

    @property
    def phone(self):
        """기존 API 호환성을 위한 phone 프로퍼티"""
        return self.tel


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
    country: str | None = None


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
    forecast: list[ForecastDay]
    timezone: str


# 인증 관련 Pydantic 모델들
class TokenData(BaseModel):
    email: str | None = None
    role: str | None = None


class UserCreate(BaseModel):
    email: str
    password: str
    nickname: str


class UserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    nickname: str | None = None
    profile_image: str | None = None
    preferred_region: str | None = None
    preferred_theme: str | None = None
    bio: str | None = None
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
    nickname: str | None = None
    profile_image: str | None = None
    preferences: list[str | None] = []
    preferred_region: str | None = None
    preferred_theme: str | None = None
    bio: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class GoogleLoginRequest(BaseModel):
    code: str
    redirect_uri: str


class GoogleLoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_info: UserResponse
    is_new_user: bool


class GoogleAuthUrlResponse(BaseModel):
    auth_url: str
    state: str


class GoogleAuthCodeRequest(BaseModel):
    auth_code: str


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
    data: dict[str, Any | None] = {}


class PaginationInfo(BaseModel):
    page: int
    page_size: int
    total_count: int
    total_pages: int


class DestinationCreate(BaseModel):
    name: str
    province: str
    region: str | None = None
    category: str | None = None
    is_indoor: bool | None = False
    tags: list[str | None] = []
    latitude: float | None = None
    longitude: float | None = None
    amenities: dict[str, Any | None] = {}
    image_url: str | None = None


class DestinationResponse(BaseModel):
    destination_id: uuid.UUID
    name: str
    province: str
    region: str | None = None
    category: str | None = None
    is_indoor: bool | None = None
    tags: list[str | None] = []
    latitude: float | None = None
    longitude: float | None = None
    amenities: dict[str, Any | None] = {}
    image_url: str | None = None
    rating: float | None = None
    recommendation_weight: float | None = None

    class Config:
        from_attributes = True


class RecommendationRequest(BaseModel):
    destination_types: list[str | None] = []
    budget_range: dict[str, float | None] = {}
    travel_dates: dict[str, str | None] = {}
    preferences: dict[str, Any | None] = {}


class RecommendationResponse(BaseModel):
    destinations: list[DestinationResponse]
    total_count: int
    recommendation_score: float


class TravelPlanCreate(BaseModel):
    title: str
    description: str | None = None
    start_date: str
    end_date: str
    budget: float | None = None
    itinerary: Optional[dict[str, List[dict[str, Any]]]] = None
    participants: int | None = None
    transportation: str | None = None
    start_location: str | None = None  # 출발지 추가
    weather_info: Optional[dict[str, Any]] = None  # 날씨 정보 추가


class TravelPlanUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    budget: float | None = None
    status: str | None = None
    itinerary: Optional[dict[str, List[dict[str, Any]]]] = None
    participants: int | None = None
    transportation: str | None = None
    start_location: str | None = None
    weather_info: Optional[dict[str, Any]] = None


class TravelPlanResponse(BaseModel):
    plan_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None = None
    start_date: date
    end_date: date
    budget: float | None = None
    status: str
    itinerary: Optional[dict[str, List[dict[str, Any]]]] = None
    participants: int | None = None
    transportation: str | None = None
    start_location: str | None = None
    weather_info: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# 지역 정보 관련 모델들
class SearchRequest(BaseModel):
    query: str
    category: str | None = None
    location: str | None = None
    limit: int | None = 10


class SearchResult(BaseModel):
    results: list[dict[str, Any]]
    total_count: int
    category: str


class RestaurantResponse(BaseModel):
    content_id: str
    region_code: str
    restaurant_name: str
    category_code: str | None = None
    sub_category_code: str | None = None
    address: str | None = None
    detail_address: str | None = None
    zipcode: str | None = None
    tel: str | None = None
    homepage: str | None = None
    overview: str | None = None
    first_image: str | None = None
    first_image_small: str | None = None
    cuisine_type: str | None = None
    specialty_dish: str | None = None
    operating_hours: str | None = None
    rest_date: str | None = None
    reservation_info: str | None = None
    credit_card: str | None = None
    smoking: str | None = None
    parking: str | None = None
    room_available: str | None = None
    children_friendly: str | None = None
    takeout: str | None = None
    delivery: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    data_quality_score: float | None = None
    raw_data_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_sync_at: datetime | None = None
    processing_status: str | None = None


class AccommodationResponse(BaseModel):
    id: str
    name: str
    type: str  # hotel, motel, guesthouse, etc.
    address: str
    phone: str | None = None
    rating: float | None = None
    price_range: str | None = None
    amenities: list[str | None] = []
    latitude: float | None = None
    longitude: float | None = None


class TransportationResponse(BaseModel):
    id: str
    name: str
    type: str  # bus, subway, taxi, etc.
    route: str | None = None
    schedule: dict[str, Any | None] = {}
    fare: str | None = None
    contact: str | None = None


class CityInfoResponse(BaseModel):
    city_name: str
    region: str
    population: int | None = None
    area: float | None = None
    description: str | None = None
    attractions: list[str | None] = []
    weather_info: dict[str, Any | None] = {}


class FavoritePlaceResponse(BaseModel):
    id: int
    place_name: str
    place_type: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    destination_id: uuid.UUID
    travel_plan_id: uuid.UUID | None = None
    rating: int
    content: str | None = None
    photos: list[str | None] = []


class ReviewResponse(BaseModel):
    review_id: uuid.UUID
    user_id: uuid.UUID
    destination_id: uuid.UUID
    travel_plan_id: uuid.UUID | None = None
    rating: int
    content: str | None = None
    photos: list[str | None] = []
    created_at: datetime

    class Config:
        from_attributes = True


# 사용자 활동 로그 테이블 (이미 UserActivityLog가 있으므로 별칭으로 사용)
UserActivity = UserActivityLog


# ===========================================
# 실제 데이터베이스 테이블에 대응하는 ORM 모델들
# ===========================================

class TouristAttraction(Base):
    """관광지 정보 테이블 - 한국관광공사 API 데이터 기반"""
    __tablename__ = "tourist_attractions"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(String, ForeignKey("regions.region_code"), nullable=False, index=True)
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    attraction_name = Column(String, nullable=False, index=True)
    category_code = Column(String(10))
    category_name = Column(String(50))
    # sub_category_code = Column(String(10))  # 실제 DB에 없음
    # sub_category_name = Column(String(50))  # 실제 DB에 없음

    # 주소 및 위치 정보
    address = Column(String)
    # detail_address = Column(String)  # 실제 DB에 없음
    zipcode = Column(String(10))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))

    # 연락처 정보
    # tel = Column(String(50))  # 실제 DB에 없음
    homepage = Column(Text)

    # 설명 및 이미지
    description = Column(Text)
    # overview = Column(Text)  # 실제 DB에 없음
    image_url = Column(String)
    # first_image = Column(String)  # 실제 DB에 없음
    # first_image_small = Column(String)  # 실제 DB에 없음

    # API 원본 필드
    booktour = Column(String(1))
    createdtime = Column(String(14))
    modifiedtime = Column(String(14))
    telname = Column(String(100))
    faxno = Column(String(50))
    mlevel = Column(Integer)

    # JSON 데이터
    detail_intro_info = Column(JSONB)
    detail_additional_info = Column(JSONB)

    # 메타데이터
    data_quality_score = Column(DECIMAL(5, 2))
    processing_status = Column(String(20), default="processed")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_sync_at = Column(DateTime, server_default=func.now())


class CulturalFacility(Base):
    """문화시설 정보 테이블"""
    __tablename__ = "cultural_facilities"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(String, ForeignKey("regions.region_code"), nullable=False, index=True)
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    facility_name = Column(String, nullable=False, index=True)
    facility_type = Column(String)
    category_code = Column(String(10))
    sub_category_code = Column(String(10))

    # 주소 및 위치 정보
    address = Column(String)
    detail_address = Column(String)
    zipcode = Column(String(10))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))

    # 연락처 정보
    tel = Column(String(50))
    homepage = Column(Text)

    # 시설 정보
    admission_fee = Column(String)
    operating_hours = Column(String)
    parking_info = Column(String)
    rest_date = Column(String)
    use_season = Column(String)
    use_time = Column(String)

    # 설명 및 이미지
    description = Column(Text)
    overview = Column(Text)
    first_image = Column(String)
    first_image_small = Column(String)

    # API 원본 필드
    booktour = Column(String(1))
    createdtime = Column(String(14))
    modifiedtime = Column(String(14))
    telname = Column(String(100))
    faxno = Column(String(50))
    mlevel = Column(Integer)

    # JSON 데이터
    detail_intro_info = Column(JSONB)
    detail_additional_info = Column(JSONB)

    # 메타데이터
    data_quality_score = Column(DECIMAL(5, 2))
    processing_status = Column(String(20), default="processed")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_sync_at = Column(DateTime, server_default=func.now())


class FestivalEvent(Base):
    """축제/행사 정보 테이블"""
    __tablename__ = "festivals_events"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(String, ForeignKey("regions.region_code"), nullable=False, index=True)
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    event_name = Column(String, nullable=False, index=True)
    category_code = Column(String(10))
    sub_category_code = Column(String(10))

    # 일정 정보
    event_start_date = Column(Date)
    event_end_date = Column(Date)
    event_place = Column(String)

    # 주소 및 위치 정보
    address = Column(String)
    detail_address = Column(String)
    zipcode = Column(String(10))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))

    # 연락처 정보
    tel = Column(String(50))
    homepage = Column(Text)

    # 행사 정보
    event_program = Column(Text)
    sponsor = Column(String)
    organizer = Column(String)
    play_time = Column(String)
    age_limit = Column(String)
    cost_info = Column(String)
    discount_info = Column(String)

    # 설명 및 이미지
    description = Column(Text)
    overview = Column(Text)
    first_image = Column(String)
    first_image_small = Column(String)

    # API 원본 필드
    booktour = Column(String(1))
    createdtime = Column(String(14))
    modifiedtime = Column(String(14))
    telname = Column(String(100))
    faxno = Column(String(50))
    mlevel = Column(Integer)

    # JSON 데이터
    detail_intro_info = Column(JSONB)
    detail_additional_info = Column(JSONB)

    # 메타데이터
    data_quality_score = Column(DECIMAL(5, 2))
    processing_status = Column(String(20), default="processed")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_sync_at = Column(DateTime, server_default=func.now())


# RestaurantNew 클래스 제거 - 기존 Restaurant 클래스에 통합됨


# AccommodationNew 클래스 제거 - 기존 Accommodation 클래스에 통합됨


class Shopping(Base):
    """쇼핑 정보 테이블"""
    __tablename__ = "shopping"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(String, ForeignKey("regions.region_code"), nullable=False, index=True)
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    shop_name = Column(String, nullable=False, index=True)
    shop_type = Column(String)
    category_code = Column(String(10))
    sub_category_code = Column(String(10))

    # 주소 및 위치 정보
    address = Column(String)
    detail_address = Column(String)
    zipcode = Column(String(10))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))

    # 연락처 정보
    tel = Column(String(50))
    homepage = Column(Text)

    # 쇼핑 정보
    opening_hours = Column(String)
    rest_date = Column(String)
    parking_info = Column(String)
    credit_card = Column(String)
    pet_allowed = Column(String)
    baby_carriage = Column(String)
    sale_item = Column(String)
    fair_day = Column(String)

    # 설명 및 이미지
    description = Column(Text)
    overview = Column(Text)
    first_image = Column(String)
    first_image_small = Column(String)

    # API 원본 필드
    booktour = Column(String(1))
    createdtime = Column(String(14))
    modifiedtime = Column(String(14))
    telname = Column(String(100))
    faxno = Column(String(50))
    mlevel = Column(Integer)

    # JSON 데이터
    detail_intro_info = Column(JSONB)
    detail_additional_info = Column(JSONB)

    # 메타데이터
    data_quality_score = Column(DECIMAL(5, 2))
    processing_status = Column(String(20), default="processed")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_sync_at = Column(DateTime, server_default=func.now())


class PetTourInfo(Base):
    """반려동물 관광정보 테이블"""
    __tablename__ = "pet_tour_info"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Unique 필드
    content_id = Column(String(50), unique=True)

    # Foreign Keys
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    content_type_id = Column(String)
    title = Column(String)

    # 주소 및 위치 정보
    address = Column(String)
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    area_code = Column(String)
    sigungu_code = Column(String)

    # 연락처 정보
    tel = Column(String)
    homepage = Column(Text)

    # 설명 및 이미지
    overview = Column(Text)
    first_image = Column(Text)
    first_image2 = Column(Text)

    # 카테고리
    cat1 = Column(String)
    cat2 = Column(String)
    cat3 = Column(String)

    # 반려동물 관련 정보
    pet_acpt_abl = Column(String)  # 반려동물 수용 가능 여부
    pet_info = Column(Text)  # 반려동물 관련 상세 정보

    # 메타데이터
    data_quality_score = Column(DECIMAL(5, 2))
    processing_status = Column(String(20), default="processed")
    last_sync_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UnifiedRegionNew(Base):
    """통합 지역정보 테이블 (기존 UnifiedRegion 클래스와 구분)"""
    __tablename__ = "unified_regions"
    __table_args__ = {"extend_existing": True, "autoload_replace": False}

    # Primary Key
    region_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Unique 필드
    region_code = Column(String(20), unique=True, index=True)

    # Foreign Keys (자기 참조)
    parent_region_id = Column(UUID(as_uuid=True), ForeignKey("unified_regions.region_id"), nullable=True, index=True)

    # 기본 정보
    region_name = Column(String, nullable=False)
    region_name_full = Column(String)
    region_name_en = Column(String)
    region_level = Column(Integer)

    # 좌표 정보
    center_latitude = Column(String)
    center_longitude = Column(String)
    boundary_data = Column(JSONB)

    # 행정 정보
    administrative_code = Column(String)
    is_active = Column(Boolean, default=True)

    # 메타데이터
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정 (자기 참조) - 임시 주석 처리
    # children = relationship("UnifiedRegionNew", back_populates="parent")
    # parent = relationship("UnifiedRegionNew", remote_side=[region_id], back_populates="children")


class TravelCourse(Base):
    __tablename__ = "travel_courses"
    content_id = Column(String, primary_key=True)
    region_code = Column(String, primary_key=True)
    course_name = Column(String, primary_key=True)
    course_theme = Column(String)
    required_time = Column(String)
    difficulty_level = Column(String)
    schedule = Column(Text)
    course_distance = Column(String)
    category_code = Column(String)
    sub_category_code = Column(String)
    address = Column(String)
    detail_address = Column(String)
    zipcode = Column(String)
    tel = Column(String)
    telname = Column(String)
    faxno = Column(String)
    homepage = Column(String)
    overview = Column(Text)
    first_image = Column(String)
    first_image_small = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    data_quality_score = Column(Float)
    processing_status = Column(String)
    raw_data_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    last_sync_at = Column(DateTime)
    mlevel = Column(Integer)
    detail_intro_info = Column(JSONB)
    detail_additional_info = Column(JSONB)
    booktour = Column(String(1))
    createdtime = Column(String)
    modifiedtime = Column(String)
    sigungu_code = Column(String)


# 성능 최적화를 위한 인덱스들
Index("idx_tourist_attractions_region_category", TouristAttraction.region_code, TouristAttraction.category_code)
Index("idx_cultural_facilities_region_type", CulturalFacility.region_code, CulturalFacility.facility_type)
Index("idx_festivals_events_region_dates", FestivalEvent.region_code, FestivalEvent.event_start_date, FestivalEvent.event_end_date)
Index("idx_restaurants_region_cuisine", Restaurant.region_code, Restaurant.cuisine_type)
Index("idx_accommodations_region_type", Accommodation.region_code, Accommodation.accommodation_type)
Index("idx_shopping_region_type", Shopping.region_code, Shopping.shop_type)
Index("idx_pet_tour_info_content_id", PetTourInfo.content_id)
Index("idx_unified_regions_code_level", UnifiedRegionNew.region_code, UnifiedRegionNew.region_level)


class Region(Base):
    __tablename__ = "regions"
    region_code = Column(String, primary_key=True)
    region_name = Column(String, nullable=False)
    parent_region_code = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    region_level = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UnifiedRegion(Base):
    __tablename__ = "unified_regions"
    __table_args__ = {"extend_existing": True, "autoload_replace": False}
    region_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    region_code = Column(String, index=True)
    region_name = Column(String, nullable=False)
    region_name_full = Column(String)
    region_name_en = Column(String)
    parent_region_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    region_level = Column(Integer)
    center_latitude = Column(String)
    center_longitude = Column(String)
    boundary_data = Column(JSONB)
    administrative_code = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TravelRoute(Base):
    """여행 경로 정보 테이블"""
    __tablename__ = "travel_routes"
    
    route_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("travel_plans.plan_id"), nullable=False)
    day = Column(Integer, nullable=False)
    sequence = Column(Integer, nullable=False)
    
    # 출발지 정보
    departure_name = Column(String, nullable=False)
    departure_lat = Column(Float)
    departure_lng = Column(Float)
    
    # 도착지 정보
    destination_name = Column(String, nullable=False)
    destination_lat = Column(Float)
    destination_lng = Column(Float)
    
    # 교통 정보
    transport_type = Column(String)  # car, bus, subway, walk, taxi
    route_data = Column(JSONB)  # 상세 경로 정보
    duration = Column(Integer)  # 소요 시간 (분)
    distance = Column(Float)  # 거리 (km)
    cost = Column(Float)  # 교통비 (원)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계 설정
    travel_plan = relationship("TravelPlan", backref="routes")


class TransportationDetail(Base):
    """교통수단 상세 정보 테이블"""
    __tablename__ = "transportation_details"
    
    detail_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    route_id = Column(UUID(as_uuid=True), ForeignKey("travel_routes.route_id"), nullable=False)
    
    # 교통수단 정보
    transport_name = Column(String)  # 지하철 2호선, 버스 146번 등
    transport_color = Column(String)  # 노선 색상
    
    # 정류장/역 정보
    departure_station = Column(String)
    arrival_station = Column(String)
    
    # 시간 정보
    departure_time = Column(DateTime)
    arrival_time = Column(DateTime)
    
    # 요금 정보
    fare = Column(Float)
    
    # 환승 정보
    transfer_info = Column(JSONB)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계 설정
    route = relationship("TravelRoute", backref="transport_details")
# 임시 비밀번호 관련 스키마
class ForgotPasswordRequest(BaseModel):
    """비밀번호 찾기 요청"""
    email: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class ForgotPasswordResponse(BaseModel):
    """비밀번호 찾기 응답"""
    message: str
    success: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "message": "임시 비밀번호가 이메일로 전송되었습니다.",
                "success": True
            }
        }


# 회원탈퇴 관련 스키마
class WithdrawRequest(BaseModel):
    """회원탈퇴 요청"""
    password: str | None = None  # 소셜 로그인 사용자는 비밀번호 불필요
    reason: str | None = None  # 탈퇴 사유 (선택사항)

    class Config:
        json_schema_extra = {
            "example": {
                "password": "current_password",
                "reason": "서비스 이용이 불필요해짐"
            }
        }


class WithdrawResponse(BaseModel):
    """회원탈퇴 응답"""
    message: str
    success: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "message": "회원탈퇴가 완료되었습니다.",
                "success": True
            }
        }


# ===========================================
# 새로 추가된 모델들에 대한 Pydantic 스키마
# ===========================================

class TouristAttractionResponse(BaseModel):
    """관광지 정보 응답 스키마"""
    content_id: str
    region_code: str
    attraction_name: str
    category_code: str | None = None
    category_name: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    tel: str | None = None
    homepage: str | None = None
    description: str | None = None
    overview: str | None = None
    first_image: str | None = None
    data_quality_score: float | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class CulturalFacilityResponse(BaseModel):
    """문화시설 정보 응답 스키마"""
    content_id: str
    region_code: str
    facility_name: str
    facility_type: str | None = None
    category_code: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    tel: str | None = None
    homepage: str | None = None
    admission_fee: str | None = None
    operating_hours: str | None = None
    parking_info: str | None = None
    overview: str | None = None
    first_image: str | None = None
    data_quality_score: float | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class FestivalEventResponse(BaseModel):
    """축제/행사 정보 응답 스키마"""
    content_id: str
    region_code: str
    event_name: str
    category_code: str | None = None
    event_start_date: date | None = None
    event_end_date: date | None = None
    event_place: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    tel: str | None = None
    homepage: str | None = None
    event_program: str | None = None
    sponsor: str | None = None
    organizer: str | None = None
    cost_info: str | None = None
    overview: str | None = None
    first_image: str | None = None
    data_quality_score: float | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# RestaurantNewResponse와 AccommodationNewResponse는 기존 RestaurantResponse와 AccommodationResponse로 대체됨
# 기존 스키마가 새로운 데이터 구조를 지원하도록 업데이트 필요


class ShoppingResponse(BaseModel):
    """쇼핑 정보 응답 스키마"""
    content_id: str
    region_code: str
    shop_name: str
    shop_type: str | None = None
    category_code: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    tel: str | None = None
    homepage: str | None = None
    opening_hours: str | None = None
    rest_date: str | None = None
    parking_info: str | None = None
    credit_card: str | None = None
    sale_item: str | None = None
    overview: str | None = None
    first_image: str | None = None
    data_quality_score: float | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class PetTourInfoResponse(BaseModel):
    """반려동물 관광정보 응답 스키마"""
    id: uuid.UUID
    content_id: str | None = None
    content_type_id: str | None = None
    title: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    area_code: str | None = None
    sigungu_code: str | None = None
    tel: str | None = None
    homepage: str | None = None
    overview: str | None = None
    first_image: str | None = None
    cat1: str | None = None
    cat2: str | None = None
    cat3: str | None = None
    pet_acpt_abl: str | None = None
    pet_info: str | None = None
    data_quality_score: float | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class UnifiedRegionResponse(BaseModel):
    """통합 지역정보 응답 스키마"""
    region_id: uuid.UUID
    region_code: str | None = None
    region_name: str
    region_name_full: str | None = None
    region_name_en: str | None = None
    region_level: int | None = None
    center_latitude: str | None = None
    center_longitude: str | None = None
    administrative_code: str | None = None
    is_active: bool | None = True
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# 경로 정보 관련 Pydantic 스키마
class TravelRouteCreate(BaseModel):
    """여행 경로 생성 요청"""
    plan_id: uuid.UUID
    day: int
    sequence: int
    departure_name: str
    departure_lat: float | None = None
    departure_lng: float | None = None
    destination_name: str
    destination_lat: float | None = None
    destination_lng: float | None = None
    transport_type: str | None = None


class TravelRouteUpdate(BaseModel):
    """여행 경로 수정 요청"""
    day: int | None = None
    sequence: int | None = None
    departure_name: str | None = None
    departure_lat: float | None = None
    departure_lng: float | None = None
    destination_name: str | None = None
    destination_lat: float | None = None
    destination_lng: float | None = None
    transport_type: str | None = None
    duration: int | None = None
    distance: float | None = None
    cost: float | None = None


class TravelRouteResponse(BaseModel):
    """여행 경로 응답"""
    route_id: uuid.UUID
    plan_id: uuid.UUID
    day: int
    sequence: int
    departure_name: str
    departure_lat: float | None = None
    departure_lng: float | None = None
    destination_name: str
    destination_lat: float | None = None
    destination_lng: float | None = None
    transport_type: str | None = None
    route_data: dict[str, Any] | None = None
    duration: int | None = None
    distance: float | None = None
    cost: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransportationDetailCreate(BaseModel):
    """교통수단 상세 정보 생성 요청"""
    route_id: uuid.UUID
    transport_name: str | None = None
    transport_color: str | None = None
    departure_station: str | None = None
    arrival_station: str | None = None
    departure_time: datetime | None = None
    arrival_time: datetime | None = None
    fare: float | None = None
    transfer_info: dict[str, Any] | None = None


class TransportationDetailResponse(BaseModel):
    """교통수단 상세 정보 응답"""
    detail_id: uuid.UUID
    route_id: uuid.UUID
    transport_name: str | None = None
    transport_color: str | None = None
    departure_station: str | None = None
    arrival_station: str | None = None
    departure_time: datetime | None = None
    arrival_time: datetime | None = None
    fare: float | None = None
    transfer_info: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class RouteCalculationRequest(BaseModel):
    """경로 계산 요청"""
    departure_lat: float
    departure_lng: float
    destination_lat: float
    destination_lng: float
    transport_type: str = "walk"  # walk, car, transit


class RouteCalculationResponse(BaseModel):
    """경로 계산 응답"""
    success: bool
    duration: int | None = None  # 분
    distance: float | None = None  # km
    cost: float | None = None  # 원
    route_data: dict[str, Any] | None = None
    transport_type: str
    message: str | None = None
