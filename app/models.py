"""
통합 데이터베이스 모델 정의
모든 서비스에서 공통으로 사용하는 SQLAlchemy ORM 모델들

각 모델의 주석에는 다음과 같은 정보가 포함됩니다:
- 사용처: 해당 모델을 사용하는 서비스 목록
- 설명: 테이블의 용도와 주요 기능
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    CHAR,
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
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


# ===========================================
# Enum 정의
# ===========================================


class AdminStatus(enum.Enum):
    """관리자 계정 상태"""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"


class TravelPlanStatus(enum.Enum):
    """여행 계획 상태"""

    PLANNING = "PLANNING"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class UserRole(enum.Enum):
    """사용자 역할"""

    USER = "USER"
    ADMIN = "ADMIN"


# ===========================================
# 사용자 및 인증 관련 테이블
# ===========================================


class User(Base):
    """
    사용자 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 일반 사용자 계정 정보 및 프로필 관리
    """

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
    preferences = Column(JSONB, default=dict)
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

    # 관계 설정
    travel_plans = relationship(
        "TravelPlan", back_populates="user", cascade="all, delete-orphan"
    )
    reviews = relationship(
        "Review", back_populates="user", cascade="all, delete-orphan"
    )
    activity_logs = relationship(
        "UserActivityLog", back_populates="user", cascade="all, delete-orphan"
    )
    chat_messages = relationship("ChatMessage", back_populates="user")

    # 알림 관련 관계
    notification_settings = relationship(
        "UserNotificationSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    device_tokens = relationship(
        "UserDeviceToken", back_populates="user", cascade="all, delete-orphan"
    )
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )


class Admin(Base):
    """
    관리자 계정 테이블
    사용처: weather-flick-admin-back
    설명: 관리자 계정 정보 및 권한 관리
    """

    __tablename__ = "admins"

    admin_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    phone = Column(String)
    status = Column(Enum(AdminStatus), default=AdminStatus.ACTIVE)
    is_superuser = Column(Boolean, default=False)  # 슈퍼관리자 여부
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class EmailVerification(Base):
    """
    이메일 인증 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 이메일 인증 코드 관리
    """

    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# ===========================================
# 여행 계획 및 일정 관련 테이블
# ===========================================


class TravelPlan(Base):
    """
    여행 계획 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 사용자의 여행 계획 및 일정 정보
    """

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
    participants = Column(Integer, nullable=True)
    transportation = Column(String, nullable=True)
    start_location = Column(String, nullable=True)  # 출발지
    weather_info = Column(JSONB, nullable=True)  # 날씨 정보
    plan_type = Column(String(50), default="manual")  # 'manual' 또는 'custom'
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    user = relationship("User", back_populates="travel_plans")
    reviews = relationship("Review", back_populates="travel_plan")
    routes = relationship("TravelRoute", back_populates="travel_plan")
    plan_destinations = relationship(
        "TravelPlanDestination",
        back_populates="travel_plan",
        cascade="all, delete-orphan",
    )


class TravelRoute(Base):
    """
    여행 경로 정보 테이블
    사용처: weather-flick-back
    설명: 여행 계획의 상세 경로 및 교통 정보
    """

    __tablename__ = "travel_routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    travel_plan_id = Column(
        UUID(as_uuid=True), ForeignKey("travel_plans.plan_id"), nullable=False
    )
    origin_place_id = Column(String)
    destination_place_id = Column(String)
    route_order = Column(Integer)
    transport_mode = Column(String)
    duration_minutes = Column(Integer)
    distance_km = Column(Float)
    route_data = Column(JSONB)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    travel_plan = relationship("TravelPlan", back_populates="routes")
    transport_details = relationship("TransportationDetail", back_populates="route")


class TransportationDetail(Base):
    """
    교통수단 상세 정보 테이블
    사용처: weather-flick-back
    설명: 경로별 상세 교통 정보 (환승, 요금 등)
    """

    __tablename__ = "transportation_details"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    travel_route_id = Column(
        UUID(as_uuid=True), ForeignKey("travel_routes.id"), nullable=False
    )

    departure_time = Column(DateTime)
    arrival_time = Column(DateTime)
    cost = Column(Integer)
    booking_info = Column(JSONB)
    notes = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    route = relationship("TravelRoute", back_populates="transport_details")


# ===========================================
# 여행지 및 시설 정보 테이블
# ===========================================


class Destination(Base):
    """
    여행지 정보 테이블
    사용처: weather-flick-admin-back
    설명: 추천 여행지 기본 정보 (관리자용)
    """

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
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    amenities = Column(JSONB)
    image_url = Column(String)
    rating = Column(Float)
    recommendation_weight = Column(DECIMAL(3, 2))
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    weather_data = relationship("WeatherData", back_populates="destination")
    reviews = relationship("Review", back_populates="destination")
    plan_destinations = relationship(
        "TravelPlanDestination",
        back_populates="destination",
        cascade="all, delete-orphan",
    )


class TouristAttraction(Base):
    """
    관광지 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 한국관광공사 API 기반 관광지 정보
    """

    __tablename__ = "tourist_attractions"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    attraction_name = Column(String, nullable=False, index=True)
    category_code = Column(String(10))
    category_name = Column(String(50))

    # 주소 및 위치 정보
    address = Column(String)
    zipcode = Column(String(10))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))

    # 연락처 정보
    homepage = Column(Text)

    # 설명 및 이미지
    description = Column(Text)
    image_url = Column(String)

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

    # 관계 설정
    region = relationship("Region", back_populates="tourist_attractions")


class CulturalFacility(Base):
    """
    문화시설 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 박물관, 전시관 등 문화시설 정보
    """

    __tablename__ = "cultural_facilities"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
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

    # 관계 설정
    region = relationship("Region", back_populates="cultural_facilities")


class FestivalEvent(Base):
    """
    축제/행사 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 지역 축제 및 행사 정보
    """

    __tablename__ = "festivals_events"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
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

    # 관계 설정
    region = relationship("Region", back_populates="festivals_events")


class Restaurant(Base):
    """
    음식점 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 한국관광공사 API 기반 음식점 정보
    """

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

    # 관계 설정
    region = relationship("Region", back_populates="restaurants")


class Accommodation(Base):
    """
    숙박시설 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 한국관광공사 API 기반 숙박시설 정보
    """

    __tablename__ = "accommodations"
    __table_args__ = {"extend_existing": True, "autoload_replace": False}

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
    raw_data_id = Column(UUID(as_uuid=True), index=True)

    # 기본 정보
    accommodation_name = Column(String, nullable=False)
    accommodation_type = Column(String, nullable=False)
    address = Column(String, nullable=False)
    tel = Column(String)

    # 위치 정보
    latitude = Column(Float)
    longitude = Column(Float)

    # 카테고리 정보
    category_code = Column(String(10))
    sub_category_code = Column(String(10))

    # 시설 정보
    parking = Column(String)

    # 메타데이터
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    region = relationship("Region", back_populates="accommodations")

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


class Shopping(Base):
    """
    쇼핑 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 쇼핑 시설 및 상점 정보
    """

    __tablename__ = "shopping"

    # Primary Key
    content_id = Column(String(20), primary_key=True, index=True)

    # Foreign Keys
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
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


class LeisureSports(Base):
    """
    레저스포츠 시설 정보 테이블
    사용처: weather-flick-admin-back, weather-flick-batch
    설명: 레저 및 스포츠 시설 정보
    """

    __tablename__ = "leisure_sports"

    content_id = Column(String(20), primary_key=True, index=True)
    region_code = Column(String, nullable=False, index=True)
    facility_name = Column(String, nullable=False, index=True)
    category_code = Column(String(10))
    sub_category_code = Column(String(10))
    raw_data_id = Column(UUID(as_uuid=True), index=True)
    sports_type = Column(String)
    reservation_info = Column(String)
    admission_fee = Column(String)
    parking_info = Column(String)
    rental_info = Column(String)
    capacity = Column(String)
    operating_hours = Column(String)
    address = Column(String)
    detail_address = Column(String)
    zipcode = Column(String)
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    tel = Column(String)
    homepage = Column(String)
    overview = Column(Text)
    first_image = Column(String)
    first_image_small = Column(String)
    data_quality_score = Column(DECIMAL(5, 2))
    processing_status = Column(String(20), default="processed")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_sync_at = Column(DateTime, server_default=func.now())
    booktour = Column(CHAR(1))
    createdtime = Column(String(14))
    modifiedtime = Column(String(14))
    telname = Column(String(100))
    faxno = Column(String(50))
    mlevel = Column(Integer)
    detail_intro_info = Column(JSONB)
    detail_additional_info = Column(JSONB)
    sigungu_code = Column(String)


class TravelCourse(Base):
    """
    여행 코스 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 추천 여행 코스 정보
    """

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
    place_id = Column(String, nullable=True, index=True)  # 구글 Place ID


class PetTourInfo(Base):
    """
    반려동물 관광정보 테이블
    사용처: weather-flick-back, weather-flick-batch
    설명: 반려동물 동반 가능 시설 정보
    """

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


class Transportation(Base):
    """
    교통수단 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 대중교통 정보
    """

    __tablename__ = "transportation"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # bus, subway, taxi, etc.
    route = Column(String)
    schedule = Column(JSONB)
    fare = Column(String)
    contact = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class CityInfo(Base):
    """
    도시 정보 테이블
    사용처: weather-flick-admin-back
    설명: 도시별 기본 정보 및 통계
    """

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


# ===========================================
# 날씨 관련 테이블
# ===========================================


class WeatherData(Base):
    """
    날씨 데이터 테이블
    사용처: weather-flick-admin-back
    설명: 기상청 API 기반 날씨 예보 데이터 (관리자용)
    """

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

    # 관계 설정
    destination = relationship("Destination", back_populates="weather_data")


class ApiRawData(Base):
    """
    API 원본 데이터 저장 테이블
    사용처: weather-flick-batch
    설명: 외부 API 호출 결과 원본 데이터 저장
    """

    __tablename__ = "api_raw_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_provider = Column(
        String(50), nullable=False
    )  # 'tourapi', 'kma', 'google_maps' 등
    endpoint = Column(String(200), nullable=False)
    request_method = Column(String(10), default="GET")
    request_params = Column(JSONB)
    request_headers = Column(JSONB)
    response_status = Column(Integer)
    raw_response = Column(JSONB, nullable=False)
    response_size = Column(Integer)  # bytes
    request_duration = Column(Integer)  # milliseconds
    api_key_hash = Column(String(64))  # API 키의 해시값 (보안)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)  # 데이터 만료 시간
    is_archived = Column(Boolean, default=False)
    file_path = Column(String(500))  # 아카이브된 파일 경로


class HistoricalWeatherDaily(Base):
    """
    과거 날씨 일일 데이터 테이블
    사용처: weather-flick-batch
    설명: 과거 날씨 통계 데이터 (일별)
    """

    __tablename__ = "historical_weather_daily"

    id = Column(Integer, primary_key=True, index=True)
    region_code = Column(String(10), nullable=False, index=True)
    weather_date = Column(Date, nullable=False, index=True)
    avg_temp = Column(Float)
    max_temp = Column(Float)
    min_temp = Column(Float)
    raw_data_id = Column(String(64))  # api_raw_data 참조
    created_at = Column(DateTime, server_default=func.now())

    # 복합 인덱스: region_code + weather_date 조합으로 자주 조회
    __table_args__ = (
        Index("idx_historical_weather_region_date", "region_code", "weather_date"),
    )


class WeatherCurrent(Base):
    """
    현재 날씨 정보 테이블
    사용처: weather-flick-batch
    설명: 실시간 날씨 정보
    """

    __tablename__ = "weather_current"

    id = Column(Integer, primary_key=True, index=True)
    region_code = Column(String(10), nullable=False, index=True)
    region_name = Column(String(50))
    weather_date = Column(Date, nullable=False)
    year = Column(Integer)
    month = Column(Integer)
    day = Column(Integer)
    avg_temp = Column(Float)
    max_temp = Column(Float)
    min_temp = Column(Float)
    humidity = Column(Float)
    precipitation = Column(Float)
    wind_speed = Column(Float)
    weather_condition = Column(String(100))
    visibility = Column(Float)
    uv_index = Column(Float)
    raw_data_id = Column(String(64))  # api_raw_data 참조
    created_at = Column(DateTime, server_default=func.now())


class WeatherForecast(Base):
    """
    날씨 예보 테이블
    사용처: weather-flick-batch
    설명: 단기/중기 날씨 예보 데이터
    """

    __tablename__ = "weather_forecast"

    id = Column(Integer, primary_key=True, index=True)
    region_code = Column(String(10), nullable=False, index=True)
    region_name = Column(String(50))
    forecast_date = Column(Date, nullable=False, index=True)
    forecast_type = Column(String(20))  # 'short_term', 'mid_term'
    min_temp = Column(Float)
    max_temp = Column(Float)
    precipitation_prob = Column(Float)
    weather_condition = Column(String(100))
    forecast_issued_at = Column(DateTime)
    raw_data_id = Column(String(64))  # api_raw_data 참조
    created_at = Column(DateTime, server_default=func.now())

    # 복합 인덱스
    __table_args__ = (
        Index("idx_weather_forecast_region_date", "region_code", "forecast_date"),
    )


# ===========================================
# 지역 정보 관련 테이블
# ===========================================


class Region(Base):
    """
    지역 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 기본 지역 코드 및 계층 정보
    """

    __tablename__ = "regions"

    region_code = Column(String, primary_key=True)
    region_name = Column(String, nullable=False)
    parent_region_code = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    region_level = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    grid_x = Column(Integer)
    grid_y = Column(Integer)
    region_name_full = Column(String)
    region_name_en = Column(String)
    region_id = Column(String)
    center_latitude = Column(Float)
    center_longitude = Column(Float)
    administrative_code = Column(String)
    api_mappings = Column(JSONB)
    coordinate_info = Column(JSONB)
    tour_api_area_code = Column(
        String, nullable=True, index=True
    )  # 한국관광공사 API 지역 코드

    # 관계 설정
    tourist_attractions = relationship("TouristAttraction", back_populates="region")
    cultural_facilities = relationship("CulturalFacility", back_populates="region")
    festivals_events = relationship("FestivalEvent", back_populates="region")
    restaurants = relationship("Restaurant", back_populates="region")
    accommodations = relationship("Accommodation", back_populates="region")


class CategoryCode(Base):
    """
    카테고리 코드 매핑 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 한국관광공사 API 카테고리 코드 정보
    """

    __tablename__ = "category_codes"

    category_code = Column(String, primary_key=True)
    category_name = Column(String, nullable=False)
    content_type_id = Column(String)
    parent_category_code = Column(String)
    category_level = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ===========================================
# 리뷰 및 평가 관련 테이블
# ===========================================


class Review(Base):
    """
    리뷰 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 여행지 및 여행 계획에 대한 리뷰
    """

    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=True
    )
    travel_plan_id = Column(
        UUID(as_uuid=True), ForeignKey("travel_plans.plan_id"), nullable=True
    )
    rating = Column(Integer, nullable=False)
    content = Column(Text)
    photos = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    user = relationship("User", back_populates="reviews")
    destination = relationship("Destination", back_populates="reviews")
    travel_plan = relationship("TravelPlan", back_populates="reviews")


class RecommendReview(Base):
    """
    추천 코스 리뷰 테이블
    사용처: weather-flick-back
    설명: 추천 여행 코스에 대한 리뷰
    """

    __tablename__ = "reviews_recommend"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(Integer, nullable=False, index=True)  # 추천코스 ID
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    nickname = Column(String(50), nullable=False)
    rating = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    parent_id = Column(
        UUID(as_uuid=True), ForeignKey("reviews_recommend.id"), nullable=True
    )  # 답글용

    # 관계 설정
    user = relationship("User")


class RecommendLike(Base):
    """
    추천 코스 좋아요 테이블
    사용처: weather-flick-back
    설명: 추천 여행 코스 좋아요 기록
    """

    __tablename__ = "likes_recommend"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(Integer, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_likes_recommend_course_user"),
    )

    # 관계 설정
    user = relationship("User")


class ReviewLike(Base):
    """
    리뷰 좋아요/싫어요 테이블
    사용처: weather-flick-back
    설명: 리뷰에 대한 좋아요/싫어요 기록
    """

    __tablename__ = "review_likes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reviews_recommend.id"),
        nullable=False,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    is_like = Column(Boolean, nullable=False)  # True=Like, False=Dislike
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "review_id", "user_id", "is_like", name="uq_review_like_user_type"
        ),
    )


class TravelCourseLike(Base):
    """
    여행 코스 좋아요 테이블
    사용처: weather-flick-back
    설명: 사용자가 좋아요한 여행 코스
    """

    __tablename__ = "travel_course_likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    title = Column(String(255), nullable=False)
    subtitle = Column(String(255))
    summary = Column(Text)
    description = Column(Text)
    region = Column(String(50))
    itinerary = Column(JSONB)


# ===========================================
# 기타 기능 테이블
# ===========================================


class Contact(Base):
    """
    문의사항 테이블
    사용처: weather-flick-back
    설명: 사용자 문의사항 관리
    """

    __tablename__ = "contact"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_private = Column(Boolean, default=False, nullable=False)
    approval_status = Column(
        SqlEnum("PENDING", "PROCESSING", "COMPLETE", name="approval_status"),
        default="PENDING",
        nullable=False,
    )
    password_hash = Column(String(128), nullable=True)
    views = Column(Integer, default=0, nullable=False)

    # 관계 설정
    answer = relationship("ContactAnswer", uselist=False, back_populates="contact")


class ContactAnswer(Base):
    """
    문의사항 답변 테이블
    사용처: weather-flick-admin-back (읽기전용으로 weather-flick-back에서도 사용)
    설명: 관리자의 문의사항 답변 관리
    """

    __tablename__ = "contact_answers"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contact.id"), nullable=False, unique=True)
    admin_id = Column(
        Integer, ForeignKey("admins.admin_id"), nullable=False
    )  # 답변한 관리자
    content = Column(Text, nullable=False)  # 답변 내용
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 관계 설정
    contact = relationship("Contact", back_populates="answer")
    admin = relationship("Admin")


class ChatMessage(Base):
    """
    챗봇 메시지 테이블
    사용처: weather-flick-back
    설명: AI 챗봇 대화 기록
    """

    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)  # 봇의 응답
    sender = Column(
        String(50), nullable=True, server_default="user"
    )  # 'user' 또는 'bot'
    context = Column(JSONB, nullable=True)  # 대화 컨텍스트 정보
    suggestions = Column(ARRAY(Text), nullable=True)  # 추천 질문 목록
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    user = relationship("User", back_populates="chat_messages")


class FavoritePlace(Base):
    """
    즐겨찾기 장소 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 사용자가 즐겨찾기한 장소 정보
    """

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


# ===========================================
# 로그 및 활동 기록 테이블
# ===========================================


class SystemLog(Base):
    """
    시스템 로그 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 시스템 전반의 로그 기록
    """

    __tablename__ = "system_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    level = Column(String, nullable=False)
    source = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    context = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())


class UserActivityLog(Base):
    """
    사용자 활동 로그 테이블
    사용처: weather-flick-admin-back
    설명: 사용자 활동 추적 및 분석
    """

    __tablename__ = "user_activity_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    activity_type = Column(String, nullable=False)
    activity_data = Column(JSONB)  # 실제 DB 컬럼명에 맞춤
    ip_address = Column(String)
    user_agent = Column(String)
    session_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    user = relationship("User", back_populates="activity_logs")


class AdminActivityLog(Base):
    """
    관리자 활동 로그 테이블
    사용처: weather-flick-admin-back
    설명: 관리자 활동 및 중요 작업 기록
    """

    __tablename__ = "admin_activity_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.admin_id"), nullable=False)
    action = Column(
        String, nullable=False
    )  # 수행된 작업 (예: USER_DELETE, USER_UPDATE)
    description = Column(Text, nullable=False)  # 작업 설명
    target_resource = Column(
        String, nullable=True
    )  # 대상 리소스 (예: user_id, plan_id)
    severity = Column(String, default="NORMAL")  # 심각도 (NORMAL, HIGH, CRITICAL)
    ip_address = Column(String, nullable=True)  # IP 주소
    user_agent = Column(String, nullable=True)  # 사용자 에이전트
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    admin = relationship("Admin", foreign_keys=[admin_id])


# ===========================================
# 배치 작업 관련 테이블
# ===========================================


class AdminBatchJob(Base):
    """
    관리자 배치 작업 테이블
    사용처: weather-flick-admin-back
    설명: 관리자가 실행한 배치 작업 기록
    """

    __tablename__ = "admin_batch_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    parameters = Column(JSONB, default={})
    progress = Column(Float, default=0.0)
    current_step = Column(String(255))
    total_steps = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("admins.admin_id"))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    result_summary = Column(JSONB)
    stopped_by = Column(Integer, ForeignKey("admins.admin_id"))
    priority = Column(Integer, default=5)
    notification_email = Column(String(255))

    # 관계 설정
    creator = relationship("Admin", foreign_keys=[created_by])
    stopper = relationship("Admin", foreign_keys=[stopped_by])
    logs = relationship(
        "AdminBatchJobDetail", back_populates="job", cascade="all, delete-orphan"
    )

    # 인덱스
    __table_args__ = (
        Index("idx_admin_batch_jobs_type_status", "job_type", "status"),
        Index("idx_admin_batch_jobs_created_at", "created_at"),
    )


class AdminBatchJobDetail(Base):
    """
    관리자 배치 작업 상세 로그 테이블
    사용처: weather-flick-admin-back
    설명: 배치 작업의 상세 실행 로그
    """

    __tablename__ = "admin_batch_job_details"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_batch_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    level = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    details = Column(JSONB)

    # 관계 설정
    job = relationship("AdminBatchJob", back_populates="logs")

    # 인덱스
    __table_args__ = (
        Index("idx_admin_batch_job_details_job_level", "job_id", "level"),
        Index("idx_admin_batch_job_details_timestamp", "timestamp"),
    )


# ===========================================
# 성능 최적화를 위한 인덱스들
# ===========================================

# 여행 계획 관련 인덱스
Index("idx_travel_plan_user_status", TravelPlan.user_id, TravelPlan.status)
Index("idx_travel_plan_dates", TravelPlan.start_date, TravelPlan.end_date)

# 날씨 데이터 관련 인덱스
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

# 리뷰 관련 인덱스
Index("idx_review_destination_date", Review.destination_id, Review.created_at)
Index("idx_review_user_rating", Review.user_id, Review.rating)

# 지역별 시설 정보 인덱스
Index(
    "idx_tourist_attractions_region_category",
    TouristAttraction.region_code,
    TouristAttraction.category_code,
)
Index(
    "idx_cultural_facilities_region_type",
    CulturalFacility.region_code,
    CulturalFacility.facility_type,
)
Index(
    "idx_festivals_events_region_dates",
    FestivalEvent.region_code,
    FestivalEvent.event_start_date,
    FestivalEvent.event_end_date,
)
Index("idx_restaurants_region_cuisine", Restaurant.region_code, Restaurant.cuisine_type)
Index(
    "idx_accommodations_region_type",
    Accommodation.region_code,
    Accommodation.accommodation_type,
)
Index("idx_shopping_region_type", Shopping.region_code, Shopping.shop_type)
Index("idx_pet_tour_info_content_id", PetTourInfo.content_id)


# ===========================================
# Pydantic 스키마 정의
# ===========================================


class WeatherRequest(BaseModel):
    """날씨 요청 스키마"""

    city: str
    country: str | None = None


class WeatherCondition(BaseModel):
    """날씨 상태 스키마"""

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


class CacheInfo(BaseModel):
    """캐시 정보 스키마"""

    is_cached: bool
    cache_key: str | None = None
    cached_at: float | None = None
    retrieved_at: float | None = None
    expires_in: int | None = None


class WeatherResponse(BaseModel):
    """날씨 응답 스키마"""

    city: str
    country: str
    current: WeatherCondition
    timezone: str
    local_time: str
    cache_info: CacheInfo | None = None


class ForecastDay(BaseModel):
    """일일 예보 스키마"""

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
    """예보 응답 스키마"""

    city: str
    country: str
    forecast: list[ForecastDay]
    timezone: str
    cache_info: CacheInfo | None = None


# 인증 관련 Pydantic 모델들
class TokenData(BaseModel):
    """토큰 데이터 스키마"""

    email: str | None = None
    role: str | None = None


class UserCreate(BaseModel):
    """사용자 생성 스키마"""

    email: str
    password: str
    nickname: str


class UserResponse(BaseModel):
    """사용자 응답 스키마"""

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
    """인증 토큰 스키마"""

    access_token: str
    token_type: str
    expires_in: int
    user_info: UserResponse


class UserUpdate(BaseModel):
    """사용자 정보 수정 스키마"""

    nickname: str | None = None
    profile_image: str | None = None
    preferences: list[str | None] = []
    preferred_region: str | None = None
    preferred_theme: str | None = None
    bio: str | None = None


class PasswordChange(BaseModel):
    """비밀번호 변경 스키마"""

    current_password: str
    new_password: str


class GoogleLoginRequest(BaseModel):
    """구글 로그인 요청 스키마"""

    code: str = Field(None, description="OAuth 인증 코드")
    redirect_uri: str = Field(None, description="리디렉션 URI")
    id_token: str = Field(None, description="Google ID 토큰")
    fcm_token: Optional[str] = Field(None, description="FCM 푸시 알림 토큰")
    device_type: Optional[str] = Field(
        None, description="디바이스 타입 (android, ios, web)"
    )
    device_id: Optional[str] = Field(None, description="디바이스 고유 식별자")
    device_name: Optional[str] = Field(None, description="디바이스 이름")


class GoogleLoginResponse(BaseModel):
    """구글 로그인 응답 스키마"""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user_info: UserResponse
    is_new_user: bool


class GoogleAuthUrlResponse(BaseModel):
    """구글 인증 URL 응답 스키마"""

    auth_url: str
    state: str


class GoogleAuthCodeRequest(BaseModel):
    """구글 인증 코드 요청 스키마"""

    auth_code: str
    fcm_token: Optional[str] = Field(None, description="FCM 푸시 알림 토큰")
    device_type: Optional[str] = Field(
        None, description="디바이스 타입 (android, ios, web)"
    )
    device_id: Optional[str] = Field(None, description="디바이스 고유 식별자")
    device_name: Optional[str] = Field(None, description="디바이스 이름")


class EmailVerificationRequest(BaseModel):
    """이메일 인증 요청 스키마"""

    email: str
    nickname: str


class EmailVerificationConfirm(BaseModel):
    """이메일 인증 확인 스키마"""

    email: str
    code: str


class EmailVerificationResponse(BaseModel):
    """이메일 인증 응답 스키마"""

    message: str
    success: bool


class ResendVerificationRequest(BaseModel):
    """이메일 재인증 요청 스키마"""

    email: str
    nickname: str


# 추천 및 여행 계획 관련 모델들
class StandardResponse(BaseModel):
    """표준 응답 스키마"""

    success: bool
    message: str
    data: dict[str, Any | None] = {}


class PaginationInfo(BaseModel):
    """페이지네이션 정보 스키마"""

    page: int
    page_size: int
    total_count: int
    total_pages: int


class RecommendationRequest(BaseModel):
    """추천 요청 스키마"""

    destination_types: list[str | None] = []
    budget_range: dict[str, float | None] = {}
    travel_dates: dict[str, str | None] = {}
    preferences: dict[str, Any | None] = {}


class RecommendationResponse(BaseModel):
    """추천 응답 스키마"""

    place_id: str  # 추가
    destination_name: str
    destinations: list[dict]
    total_count: int
    recommendation_score: float


class TravelPlanCreate(BaseModel):
    """여행 계획 생성 스키마"""

    title: str
    description: str | None = None
    start_date: str
    end_date: str
    budget: float | None = None
    itinerary: dict[str, list[dict[str, Any]]] | None = None
    participants: int | None = None
    transportation: str | None = None
    start_location: str | None = None  # 출발지 추가
    weather_info: dict[str, Any] | None = None  # 날씨 정보 추가
    theme: str | None = None  # 테마 추가
    status: str | None = None  # 상태 추가
    plan_type: str | None = None  # 여행 계획 타입 ('manual' 또는 'custom')


class TravelPlanUpdate(BaseModel):
    """여행 계획 수정 스키마"""

    title: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    budget: float | None = None
    status: str | None = None
    itinerary: dict[str, list[dict[str, Any]]] | None = None
    participants: int | None = None
    transportation: str | None = None
    start_location: str | None = None
    weather_info: dict[str, Any] | None = None


class TravelPlanResponse(BaseModel):
    """여행 계획 응답 스키마"""

    plan_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None = None
    start_date: date
    end_date: date
    budget: float | None = None
    status: str
    itinerary: dict[str, list[dict[str, Any]]] | None = None
    participants: int | None = None
    transportation: str | None = None
    start_location: str | None = None
    weather_info: dict[str, Any] | None = None
    plan_type: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# 지역 정보 관련 모델들
class SearchRequest(BaseModel):
    """검색 요청 스키마"""

    query: str
    category: str | None = None
    location: str | None = None
    limit: int | None = 10


class SearchResult(BaseModel):
    """검색 결과 스키마"""

    results: list[dict[str, Any]]
    total_count: int
    category: str


class RestaurantResponse(BaseModel):
    """음식점 응답 스키마"""

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
    """숙박시설 응답 스키마"""

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
    """교통수단 응답 스키마"""

    id: str
    name: str
    type: str  # bus, subway, taxi, etc.
    route: str | None = None
    schedule: dict[str, Any | None] = {}
    fare: str | None = None
    contact: str | None = None


class FavoritePlaceResponse(BaseModel):
    """즐겨찾기 장소 응답 스키마"""

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
    """리뷰 생성 스키마"""

    destination_id: uuid.UUID
    travel_plan_id: uuid.UUID | None = None
    rating: int
    content: str | None = None
    photos: list[str | None] = []


class ReviewResponse(BaseModel):
    """리뷰 응답 스키마"""

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


# 관광지 정보 관련 스키마
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


# 경로 정보 관련 Pydantic 스키마
class TravelRouteCreate(BaseModel):
    """여행 경로 생성 스키마"""

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
    """여행 경로 수정 스키마"""

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
    """여행 경로 응답 스키마"""

    # 프론트엔드 호환성을 위해 route_id 필드 유지
    route_id: uuid.UUID
    plan_id: uuid.UUID

    # 실제 DB 스키마 기반 필드들
    origin_place_id: str | None = None
    destination_place_id: str | None = None
    route_order: int | None = None
    transport_mode: str | None = None
    duration_minutes: int | None = None
    distance_km: float | None = None
    route_data: dict[str, Any] | None = None
    created_at: datetime

    # 프론트엔드에서 기대하는 추가 필드들 (매핑용)
    day: int | None = None
    sequence: int | None = None
    transport_type: str | None = None
    departure_name: str | None = None
    destination_name: str | None = None
    departure_lat: float | None = None
    departure_lng: float | None = None
    destination_lat: float | None = None
    destination_lng: float | None = None
    duration: int | None = None
    distance: float | None = None

    @classmethod
    def _calculate_day_from_route_order(cls, route_order: int) -> int:
        """루트 순서로부터 일차 계산 (기본적으로 3개 이동 당 1일차로 가정)"""
        if route_order is None:
            return 1
        # 루트 순서를 기반으로 일차 계산 (0,1,2 = 1일차, 3,4,5 = 2일차, ...)
        return (route_order // 3) + 1

    @classmethod
    def from_orm_with_mapping(cls, obj):
        """ORM 객체를 프론트엔드 호환 형식으로 변환"""
        return cls(
            route_id=obj.id,  # id -> route_id 매핑
            plan_id=obj.travel_plan_id,  # travel_plan_id -> plan_id 매핑
            origin_place_id=obj.origin_place_id,
            destination_place_id=obj.destination_place_id,
            route_order=obj.route_order,
            transport_mode=obj.transport_mode,
            duration_minutes=obj.duration_minutes,
            distance_km=obj.distance_km,
            route_data=obj.route_data,
            created_at=obj.created_at,
            # 프론트엔드 호환성을 위한 매핑
            day=cls._calculate_day_from_route_order(obj.route_order),
            sequence=obj.route_order,
            transport_type=obj.transport_mode,
            departure_name=obj.origin_place_id,
            destination_name=obj.destination_place_id,
            departure_lat=37.5665,  # 서울 기본 좌표 (추후 좌표 데이터 연동 필요)
            departure_lng=126.9780,
            destination_lat=37.5665,
            destination_lng=126.9780,
            duration=obj.duration_minutes,
            distance=obj.distance_km,
        )

    class Config:
        from_attributes = True


class TransportationDetailCreate(BaseModel):
    """교통수단 상세 정보 생성 스키마"""

    travel_route_id: uuid.UUID
    departure_time: datetime | None = None
    arrival_time: datetime | None = None
    cost: int | None = None
    booking_info: dict[str, Any] | None = None
    notes: str | None = None


class TransportationDetailResponse(BaseModel):
    """교통수단 상세 정보 응답 스키마"""

    id: uuid.UUID
    travel_route_id: uuid.UUID
    departure_time: datetime | None = None
    arrival_time: datetime | None = None
    cost: int | None = None
    booking_info: dict[str, Any] | None = None
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class RouteCalculationRequest(BaseModel):
    """경로 계산 요청 스키마"""

    departure_lat: float
    departure_lng: float
    destination_lat: float
    destination_lng: float
    transport_type: str = "walk"  # walk, car, transit


class RouteCalculationResponse(BaseModel):
    """경로 계산 응답 스키마"""

    success: bool
    duration: int | None = None  # 분
    distance: float | None = None  # km
    cost: float | None = None  # 원
    route_data: dict[str, Any] | None = None
    transport_type: str
    message: str | None = None


class RecommendReviewCreate(BaseModel):
    """추천 코스 리뷰 생성 스키마"""

    course_id: int
    rating: int = Field(..., ge=1, le=5)
    content: str
    nickname: str
    parent_id: uuid.UUID | None = None  # 답글용


class RecommendReviewResponse(BaseModel):
    """추천 코스 리뷰 응답 스키마"""

    id: uuid.UUID
    course_id: int
    user_id: uuid.UUID
    nickname: str
    rating: int
    content: str
    created_at: datetime
    parent_id: uuid.UUID | None = None  # 답글용
    children: list[RecommendReviewResponse] = []  # 트리 구조용
    likeCount: int = 0  # 추천수 필드 추가
    dislikeCount: int = 0  # 싫어요 수 필드 추가

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class RecommendLikeCreate(BaseModel):
    """추천 코스 좋아요 생성 스키마"""

    course_id: int


class RecommendLikeResponse(BaseModel):
    """추천 코스 좋아요 응답 스키마"""

    id: uuid.UUID
    course_id: int
    user_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class ReviewLikeCreate(BaseModel):
    """리뷰 좋아요/싫어요 생성 스키마"""

    review_id: uuid.UUID
    is_like: bool


class ReviewLikeResponse(BaseModel):
    """리뷰 좋아요/싫어요 응답 스키마"""

    id: uuid.UUID
    review_id: uuid.UUID
    user_id: uuid.UUID
    is_like: bool
    created_at: datetime

    class Config:
        from_attributes = True


# 임시 비밀번호 관련 스키마
class ForgotPasswordRequest(BaseModel):
    """비밀번호 찾기 요청"""

    email: str

    class Config:
        json_schema_extra = {"example": {"email": "user@example.com"}}


class ForgotPasswordResponse(BaseModel):
    """비밀번호 찾기 응답"""

    message: str
    success: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "message": "임시 비밀번호가 이메일로 전송되었습니다.",
                "success": True,
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
                "reason": "서비스 이용이 불필요해짐",
            }
        }


class WithdrawResponse(BaseModel):
    """회원탈퇴 응답"""

    message: str
    success: bool = True

    class Config:
        json_schema_extra = {
            "example": {"message": "회원탈퇴가 완료되었습니다.", "success": True}
        }


# 맞춤 일정 추천 관련 모델들
class CustomTravelRecommendationRequest(BaseModel):
    """맞춤 일정 추천 요청 모델"""

    region_code: str = Field(..., description="지역 코드")
    region_name: str = Field(..., description="지역 이름")
    period: str = Field(..., description="여행 기간 (당일치기, 1박2일 등)")
    days: int = Field(..., ge=1, le=7, description="여행 일수")
    who: str = Field(
        ...,
        description="동행자 유형 (solo, couple, family, friends, colleagues, group)",
    )
    styles: list[str] = Field(
        ...,
        description="여행 스타일 (activity, hotplace, nature, landmark, healing, culture, local, shopping, food, pet)",
    )
    schedule: str = Field(..., description="일정 유형 (packed, relaxed)")


class PlaceRecommendation(BaseModel):
    """추천 장소 모델"""

    id: str = Field(..., description="장소 ID")
    name: str = Field(..., description="장소 이름")
    time: str = Field(..., description="방문 시간 (예: 09:00-11:00)")
    tags: list[str] = Field(..., description="장소 태그")
    description: str = Field(..., description="장소 설명")
    rating: float = Field(..., ge=0, le=5, description="평점")
    image: str | None = Field(None, description="이미지 URL")
    address: str | None = Field(None, description="주소")
    latitude: float | None = Field(None, description="위도")
    longitude: float | None = Field(None, description="경도")
    pet_info: dict[str, str] | None = Field(None, description="반려동물 동반 정보")


class DayItinerary(BaseModel):
    """일별 여행 일정"""

    day: int = Field(..., description="일차")
    date: str | None = Field(None, description="날짜")
    places: list[PlaceRecommendation] = Field(..., description="추천 장소 목록")
    weather: dict | None = Field(None, description="날씨 정보")


class CustomTravelRecommendationResponse(BaseModel):
    """맞춤 일정 추천 응답 모델"""

    days: list[DayItinerary] = Field(..., description="일별 여행 일정")
    weather_summary: dict | None = Field(None, description="전체 날씨 요약")
    total_places: int = Field(..., description="총 추천 장소 수")
    recommendation_type: str = Field(..., description="추천 유형")
    created_at: datetime = Field(default_factory=lambda: datetime.now())


# ===========================================
# 데이터베이스에만 존재하는 누락된 테이블 모델들
# ===========================================

# 중복 정의 제거 - 이미 위에 정의되어 있음
# class Accommodation(Base):
#     """
#     숙박시설 정보 테이블
#     사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
#     설명: 한국관광공사 API 기반 숙박시설 정보
#     """
#
#     __tablename__ = "accommodations"
#     __table_args__ = {"extend_existing": True, "autoload_replace": False}
#
#     # Primary Key
#     content_id = Column(String(20), primary_key=True, index=True)
#
#     # Foreign Keys
#     region_code = Column(
#         String, ForeignKey("regions.region_code"), nullable=False, index=True
#     )
#     raw_data_id = Column(UUID(as_uuid=True), index=True)
#
#     # 기본 정보
#     accommodation_name = Column(String, nullable=False)
#     accommodation_type = Column(String, nullable=False)
#     address = Column(String, nullable=False)
#     tel = Column(String)
#
#     # 위치 정보
#     latitude = Column(Float)
#     longitude = Column(Float)
#
#     # 카테고리 정보
#     category_code = Column(String(10))
#     sub_category_code = Column(String(10))
#
#     # 시설 정보
#     parking = Column(String)
#
#     # 메타데이터
#     created_at = Column(DateTime, server_default=func.now())
#
#     # 기존 API 호환성을 위한 프로퍼티
#     @property
#     def id(self):
#         """기존 API 호환성을 위한 id 프로퍼티"""
#         return self.content_id
#
#     @property
#     def name(self):
#         """기존 API 호환성을 위한 name 프로퍼티"""
#         return self.accommodation_name
#
#     @property
#     def type(self):
#         """기존 API 호환성을 위한 type 프로퍼티"""
#         return self.accommodation_type
#
#     @property
#     def phone(self):
#         """기존 API 호환성을 위한 phone 프로퍼티"""
#         return self.tel


class TravelCourseSpot(Base):
    """
    여행 코스 구성 지점 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 여행 코스를 구성하는 개별 지점 정보
    """

    __tablename__ = "travel_course_spots"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    course_id = Column(
        String(20), ForeignKey("travel_courses.content_id"), nullable=False, index=True
    )
    spot_content_id = Column(String(20), index=True)  # 관광지/시설의 content_id

    # 순서 및 정보
    sequence = Column(Integer, nullable=False)  # 코스 내 순서
    spot_name = Column(String, nullable=False)
    spot_type = Column(String)  # 관광지, 식당, 숙박 등

    # 시간 정보
    recommended_duration = Column(Integer)  # 추천 체류 시간 (분)
    arrival_time = Column(String)  # 도착 시간
    departure_time = Column(String)  # 출발 시간

    # 교통 정보
    distance_from_previous = Column(Float)  # 이전 지점으로부터의 거리 (km)
    transport_to_next = Column(String)  # 다음 지점까지의 교통수단

    # 추가 정보
    description = Column(Text)
    tips = Column(Text)  # 팁이나 주의사항

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WeatherInfo(Base):
    """
    날씨 예보 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 단기/중기 날씨 예보 정보
    """

    __tablename__ = "weather_info"

    weather_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
    forecast_date = Column(Date, nullable=False, index=True)
    forecast_type = Column(String(20))  # 'short_term', 'mid_term'

    # 기온 정보
    temperature_high = Column(Float)
    temperature_low = Column(Float)

    # 날씨 상태
    weather_condition = Column(String)
    weather_description = Column(String)

    # 강수 정보
    precipitation_probability = Column(Integer)  # 강수 확률
    precipitation_amount = Column(Float)  # 예상 강수량

    # 기타 정보
    humidity = Column(Integer)
    wind_speed = Column(Float)
    wind_direction = Column(String)

    # 여행 적합도
    travel_score = Column(Integer)  # 1-10 여행 적합도 점수

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 인덱스
    __table_args__ = (
        UniqueConstraint(
            "region_code", "forecast_date", "forecast_type", name="uq_weather_forecast"
        ),
        Index("idx_weather_date", "forecast_date"),
    )


class WeatherForecastDetail(Base):
    """
    상세 날씨 예보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 시간별 상세 날씨 예보
    """

    __tablename__ = "weather_forecasts"

    forecast_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    region_code = Column(
        String, ForeignKey("regions.region_code"), nullable=False, index=True
    )
    forecast_datetime = Column(DateTime, nullable=False, index=True)

    # 기온 정보
    temperature = Column(Float)
    feels_like = Column(Float)

    # 날씨 상태
    weather_condition = Column(String)
    weather_icon = Column(String)

    # 강수 정보
    precipitation_type = Column(String)  # rain, snow, sleet
    precipitation_probability = Column(Integer)
    precipitation_amount = Column(Float)

    # 바람 정보
    wind_speed = Column(Float)
    wind_direction = Column(Integer)  # 각도
    wind_gust = Column(Float)  # 돌풍

    # 기타
    humidity = Column(Integer)
    pressure = Column(Float)  # 기압
    visibility = Column(Float)
    cloud_coverage = Column(Integer)

    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_forecast_region_datetime", "region_code", "forecast_datetime"),
    )


class RawApiData(Base):
    """
    원본 API 데이터 저장 테이블
    사용처: weather-flick-batch
    설명: 외부 API에서 수집한 원본 데이터 저장
    """

    __tablename__ = "raw_api_data"

    data_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    source_api = Column(String, nullable=False)  # tour_api, weather_api 등
    data_type = Column(String, nullable=False)  # attraction, weather_forecast 등
    content_id = Column(String, index=True)  # 원본 콘텐츠 ID

    # 원본 데이터
    raw_data = Column(JSONB, nullable=False)

    # 처리 상태
    is_processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)
    processing_error = Column(Text)

    # 메타데이터
    collected_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)  # 데이터 만료 시간

    # 인덱스
    __table_args__ = (
        Index("idx_raw_data_source_type", "source_api", "data_type"),
        Index("idx_raw_data_processed", "is_processed", "collected_at"),
    )


class ErrorLog(Base):
    """
    에러 로그 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 시스템 전체 에러 로그
    """

    __tablename__ = "error_logs"

    error_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    service_name = Column(String, nullable=False)  # weather-flick-back, admin-back 등
    error_type = Column(String, nullable=False)  # database, api, validation 등
    error_level = Column(String, nullable=False)  # error, warning, critical

    # 에러 정보
    error_message = Column(Text, nullable=False)
    error_trace = Column(Text)  # 스택 트레이스
    error_data = Column(JSONB)  # 추가 컨텍스트 데이터

    # 요청 정보
    request_method = Column(String)
    request_url = Column(Text)
    request_headers = Column(JSONB)
    request_body = Column(JSONB)

    # 사용자 정보
    user_id = Column(UUID(as_uuid=True))
    ip_address = Column(String(45))

    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_error_service_created", "service_name", "created_at"),
        Index("idx_error_type_level", "error_type", "error_level"),
    )


class EventLog(Base):
    """
    이벤트 로그 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 중요 시스템 이벤트 로그
    """

    __tablename__ = "event_logs"

    event_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    service_name = Column(String, nullable=False)
    event_type = Column(
        String, nullable=False
    )  # user_action, system_event, data_change 등
    event_name = Column(String, nullable=False)  # login, data_sync_completed 등

    # 이벤트 정보
    event_data = Column(JSONB)

    # 사용자 정보
    user_id = Column(UUID(as_uuid=True))
    admin_id = Column(Integer)

    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_event_service_type", "service_name", "event_type"),
        Index("idx_event_created", "created_at"),
        Index("idx_event_user", "user_id"),
        Index("idx_event_admin", "admin_id"),
    )


class SystemSettings(Base):
    """
    시스템 설정 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 시스템 전역 설정 값 저장
    """

    __tablename__ = "system_settings"

    setting_key = Column(String, primary_key=True)
    setting_value = Column(JSONB, nullable=False)
    setting_type = Column(String, nullable=False)  # string, number, boolean, json
    description = Column(Text)
    is_public = Column(Boolean, default=False)  # 클라이언트에 노출 가능 여부
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer)  # admin_id


class DataSyncStatus(Base):
    """
    데이터 동기화 상태 테이블
    사용처: weather-flick-batch
    설명: 외부 데이터 소스와의 동기화 상태 추적
    """

    __tablename__ = "data_sync_status"

    sync_id = Column(Integer, primary_key=True, index=True)
    data_source = Column(String, nullable=False)  # tour_api, weather_api 등
    sync_type = Column(String, nullable=False)  # full, incremental

    # 동기화 범위
    sync_target = Column(String)  # regions, attractions 등
    sync_filter = Column(JSONB)  # 동기화 필터 조건

    # 진행 상태
    status = Column(String, default="pending")  # pending, running, completed, failed
    progress_percent = Column(Float, default=0)
    current_page = Column(Integer)
    total_pages = Column(Integer)

    # 결과
    records_fetched = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_deleted = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)

    # 시간 정보
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    next_sync_at = Column(DateTime)

    # 에러 정보
    error_message = Column(Text)
    error_details = Column(JSONB)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 유니크 제약조건
    __table_args__ = (
        UniqueConstraint(
            "data_source", "sync_type", "sync_target", name="uq_sync_source_type_target"
        ),
    )


class SystemConfiguration(Base):
    """
    시스템 구성 정보 테이블
    사용처: weather-flick-admin-back
    설명: 시스템 구성 및 기능 플래그 관리
    """

    __tablename__ = "system_configurations"

    config_id = Column(Integer, primary_key=True, index=True)
    config_category = Column(String, nullable=False)  # feature, api, security 등
    config_key = Column(String, nullable=False)
    config_value = Column(JSONB, nullable=False)

    # 설정 정보
    is_active = Column(Boolean, default=True)
    requires_restart = Column(Boolean, default=False)  # 재시작 필요 여부

    # 설명
    description = Column(Text)
    allowed_values = Column(JSONB)  # 허용된 값 목록
    default_value = Column(JSONB)  # 기본값

    # 감사 정보
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer)  # admin_id
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer)  # admin_id

    # 유니크 제약조건
    __table_args__ = (
        UniqueConstraint(
            "config_category", "config_key", name="uq_config_category_key"
        ),
        Index("idx_config_category", "config_category", "is_active"),
    )


class TravelPlanDestination(Base):
    """
    여행 계획-여행지 연결 테이블
    사용처: weather-flick-back
    설명: 여행 계획에 포함된 여행지 정보
    """

    __tablename__ = "travel_plan_destinations"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(
        UUID(as_uuid=True), ForeignKey("travel_plans.plan_id"), nullable=False
    )
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    visit_date = Column(Date)
    visit_order = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    travel_plan = relationship("TravelPlan", back_populates="plan_destinations")
    destination = relationship("Destination", back_populates="plan_destinations")

    # 유니크 제약조건
    __table_args__ = (
        UniqueConstraint("plan_id", "destination_id", name="uq_plan_destination"),
    )


class DestinationImage(Base):
    """
    여행지 이미지 테이블
    사용처: weather-flick-admin-back
    설명: 여행지별 이미지 관리
    """

    __tablename__ = "destination_images"

    image_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    image_url = Column(String, nullable=False)
    is_main = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class DestinationRating(Base):
    """
    여행지 평점 테이블
    사용처: weather-flick-back, weather-flick-admin-back
    설명: 사용자별 여행지 평점 관리
    """

    __tablename__ = "destination_ratings"

    rating_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 평점
    created_at = Column(DateTime, server_default=func.now())

    # 유니크 제약조건: 한 사용자는 한 여행지에 하나의 평점만
    __table_args__ = (
        UniqueConstraint(
            "destination_id", "user_id", name="uq_destination_user_rating"
        ),
    )


class WeatherRecommendation(Base):
    """
    날씨 기반 여행지 추천 테이블
    사용처: weather-flick-back
    설명: 날씨 조건에 따른 여행지 추천 정보
    """

    __tablename__ = "weather_recommendations"

    recommendation_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    weather_condition = Column(String, nullable=False)  # sunny, rainy, snowy 등
    temperature_range = Column(String)  # cold, cool, warm, hot
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=False
    )
    recommendation_score = Column(Float)  # 추천 점수
    reason = Column(Text)  # 추천 이유
    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_weather_recommendation", "weather_condition", "temperature_range"),
    )


class ApiKey(Base):
    """
    API 키 관리 테이블
    사용처: weather-flick-batch
    설명: 외부 API 키 관리 및 사용량 추적
    """

    __tablename__ = "api_keys"

    key_id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, nullable=False)  # tour_api, weather_api 등
    api_key = Column(String, nullable=False)
    key_alias = Column(String)  # 키 별칭

    # 사용량 제한
    daily_limit = Column(Integer)
    monthly_limit = Column(Integer)

    # 현재 사용량
    daily_usage = Column(Integer, default=0)
    monthly_usage = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    usage_reset_at = Column(DateTime)

    # 상태
    is_active = Column(Boolean, default=True)
    error_count = Column(Integer, default=0)
    last_error_at = Column(DateTime)
    last_error_message = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 유니크 제약조건
    __table_args__ = (
        UniqueConstraint("service_name", "api_key", name="uq_service_api_key"),
        Index("idx_api_key_service", "service_name", "is_active"),
    )


class DataCollectionLog(Base):
    """
    데이터 수집 로그 테이블
    사용처: weather-flick-batch
    설명: 외부 API 데이터 수집 기록
    """

    __tablename__ = "data_collection_logs"

    log_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    api_key_id = Column(Integer, ForeignKey("api_keys.key_id"), nullable=False)
    collection_type = Column(String, nullable=False)  # tourist_attraction, weather 등

    # 수집 정보
    request_url = Column(Text)
    request_params = Column(JSONB)
    response_status = Column(Integer)
    response_time = Column(Float)  # 응답 시간 (초)

    # 결과
    records_collected = Column(Integer, default=0)
    records_processed = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)

    # 에러 정보
    error_message = Column(Text)

    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)

    # 인덱스
    __table_args__ = (
        Index("idx_collection_log_api", "api_key_id"),
        Index("idx_collection_log_type_started", "collection_type", "started_at"),
    )


class BatchJob(Base):
    """
    배치 작업 정의 테이블
    사용처: weather-flick-batch
    설명: 정기적으로 실행되는 배치 작업 정의
    """

    __tablename__ = "batch_jobs"

    job_id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String, unique=True, nullable=False)
    job_type = Column(String, nullable=False)  # data_collection, data_processing 등
    description = Column(Text)

    # 실행 설정
    is_active = Column(Boolean, default=True)
    schedule_cron = Column(String)  # 크론 표현식
    timeout_minutes = Column(Integer, default=60)
    retry_count = Column(Integer, default=3)

    # 마지막 실행 정보
    last_run_at = Column(DateTime)
    last_success_at = Column(DateTime)
    last_failure_at = Column(DateTime)
    last_error_message = Column(Text)

    # 실행 통계
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BatchJobSchedule(Base):
    """
    배치 작업 스케줄 테이블
    사용처: weather-flick-batch
    설명: 배치 작업의 실행 스케줄 관리
    """

    __tablename__ = "batch_job_schedules"

    schedule_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("batch_jobs.job_id"), nullable=False)

    # 스케줄 정보
    scheduled_time = Column(DateTime, nullable=False, index=True)
    priority = Column(Integer, default=5)  # 1-10, 높을수록 우선순위 높음

    # 실행 상태
    status = Column(
        String, default="pending"
    )  # pending, running, completed, failed, cancelled
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # 실행 결과
    result_summary = Column(JSONB)
    error_message = Column(Text)

    created_at = Column(DateTime, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_schedule_status_time", "status", "scheduled_time"),
        Index("idx_schedule_job", "job_id"),
    )


# ===========================================
# 알림 관련 테이블
# ===========================================


class NotificationStatus(enum.Enum):
    """알림 상태"""

    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"


class NotificationType(enum.Enum):
    """알림 유형"""

    WEATHER_ALERT = "WEATHER_ALERT"  # 날씨 변화 알림
    TRAVEL_PLAN_UPDATE = "TRAVEL_PLAN_UPDATE"  # 여행 계획 업데이트
    RECOMMENDATION = "RECOMMENDATION"  # 추천 알림
    MARKETING = "MARKETING"  # 마케팅 알림
    SYSTEM = "SYSTEM"  # 시스템 알림
    EMERGENCY = "EMERGENCY"  # 긴급 알림


class NotificationChannel(enum.Enum):
    """알림 채널"""

    PUSH = "PUSH"  # FCM 푸시 알림
    EMAIL = "EMAIL"  # 이메일 알림
    SMS = "SMS"  # SMS 알림
    IN_APP = "IN_APP"  # 인앱 알림


class UserNotificationSettings(Base):
    """
    사용자 알림 설정 테이블
    사용처: weather-flick-back
    설명: 사용자별 알림 설정 관리
    """

    __tablename__ = "user_notification_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # 알림 채널별 설정
    push_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=False)
    sms_enabled = Column(Boolean, default=False)
    in_app_enabled = Column(Boolean, default=True)

    # 알림 유형별 설정
    weather_alerts = Column(Boolean, default=True)
    travel_plan_updates = Column(Boolean, default=True)
    recommendation_updates = Column(Boolean, default=True)
    marketing_messages = Column(Boolean, default=False)
    system_messages = Column(Boolean, default=True)
    emergency_alerts = Column(Boolean, default=True)

    # 방해 금지 시간 설정
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(String(5))  # HH:MM 형식
    quiet_hours_end = Column(String(5))  # HH:MM 형식

    # 알림 빈도 설정
    digest_enabled = Column(Boolean, default=False)  # 요약 알림
    digest_frequency = Column(String(20), default="daily")  # daily, weekly

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    user = relationship("User", back_populates="notification_settings")

    # 인덱스
    __table_args__ = (Index("idx_user_notification_settings", "user_id"),)


class UserDeviceToken(Base):
    """
    사용자 디바이스 토큰 테이블
    사용처: weather-flick-back
    설명: FCM 푸시 알림을 위한 디바이스 토큰 관리
    """

    __tablename__ = "user_device_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # 디바이스 정보
    device_token = Column(String, nullable=False, unique=True, index=True)
    device_type = Column(String(20))  # android, ios, web
    device_id = Column(String)  # 디바이스 고유 ID
    device_name = Column(String)  # 사용자 지정 디바이스 이름

    # 토큰 상태
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime)

    # 메타데이터
    user_agent = Column(String)
    app_version = Column(String)
    os_version = Column(String)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    user = relationship("User", back_populates="device_tokens")

    # 인덱스
    __table_args__ = (
        Index("idx_device_token", "device_token"),
        Index("idx_user_device_tokens", "user_id", "is_active"),
    )


class Notification(Base):
    """
    알림 테이블
    사용처: weather-flick-back
    설명: 모든 알림 메시지 관리
    """

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # 수신자 정보
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )

    # 알림 기본 정보
    type = Column(Enum(NotificationType), nullable=False, index=True)
    channel = Column(Enum(NotificationChannel), nullable=False, index=True)
    status = Column(
        Enum(NotificationStatus), default=NotificationStatus.PENDING, index=True
    )

    # 알림 내용
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSONB)  # 추가 데이터 (딥링크, 액션 등)

    # 우선순위 및 만료
    priority = Column(Integer, default=5)  # 1-10, 높을수록 우선순위 높음
    expires_at = Column(DateTime)

    # 전송 관련
    scheduled_at = Column(DateTime)  # 예약 전송 시간
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    read_at = Column(DateTime)

    # 실패 관련
    failure_reason = Column(String)
    retry_count = Column(Integer, default=0)
    max_retry_count = Column(Integer, default=3)

    # 외부 서비스 응답
    external_id = Column(String)  # FCM 메시지 ID 등
    external_response = Column(JSONB)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    user = relationship("User", back_populates="notifications")

    # 인덱스
    __table_args__ = (
        Index("idx_notification_user_status", "user_id", "status"),
        Index("idx_notification_type_channel", "type", "channel"),
        Index("idx_notification_scheduled", "scheduled_at"),
        Index("idx_notification_created", "created_at"),
    )


class NotificationTemplate(Base):
    """
    알림 템플릿 테이블
    사용처: weather-flick-back
    설명: 알림 메시지 템플릿 관리
    """

    __tablename__ = "notification_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # 템플릿 정보
    name = Column(String(100), nullable=False, unique=True, index=True)
    type = Column(Enum(NotificationType), nullable=False, index=True)
    channel = Column(Enum(NotificationChannel), nullable=False, index=True)

    # 템플릿 내용
    title_template = Column(String(255), nullable=False)
    message_template = Column(Text, nullable=False)

    # 템플릿 설정
    variables = Column(JSONB)  # 템플릿 변수 정의
    is_active = Column(Boolean, default=True)

    # 메타데이터
    description = Column(Text)
    version = Column(String(10), default="1.0")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 인덱스
    __table_args__ = (
        Index("idx_template_type_channel", "type", "channel", "is_active"),
    )


class NotificationLog(Base):
    """
    알림 로그 테이블
    사용처: weather-flick-back
    설명: 알림 발송 및 처리 로그 관리
    """

    __tablename__ = "notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    notification_id = Column(
        UUID(as_uuid=True), ForeignKey("notifications.id"), nullable=False, index=True
    )

    # 로그 정보
    event_type = Column(
        String(50), nullable=False
    )  # sent, delivered, read, failed, etc.
    message = Column(Text)
    details = Column(JSONB)

    # 시간 정보
    timestamp = Column(DateTime, server_default=func.now(), index=True)

    # 관계 설정
    notification = relationship("Notification")

    # 인덱스
    __table_args__ = (
        Index("idx_notification_log_event", "notification_id", "event_type"),
        Index("idx_notification_log_timestamp", "timestamp"),
    )


# 중복 정의 제거 - 이미 위에 정의되어 있음
# class PetTourInfo(Base):
#     """
#     반려동물 동반 여행지 테이블
#     사용처: weather-flick-back, weather-flick-batch
#     설명: 한국관광공사 API 기반 반려동물 동반 가능 여행지 정보
#     """
#     __tablename__ = "pet_tour_info"
#
#     # Primary Key
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
#
#     # 콘텐츠 정보
#     content_id = Column(String(20), index=True)
#     content_type_id = Column(String(10))
#     title = Column(String(500))
#
#     # 위치 정보
#     address = Column(String(500))
#     latitude = Column(DECIMAL(10, 8))
#     longitude = Column(DECIMAL(11, 8))
#     area_code = Column(String(10))
#     sigungu_code = Column(String(10))
#
#     # 연락처 정보
#     tel = Column(String(100))
#     homepage = Column(Text)
#
#     # 설명 및 이미지
#     overview = Column(Text)
#     first_image = Column(Text)
#     first_image2 = Column(Text)
#
#     # 반려동물 정보
#     pet_acpt_abl = Column(String(500))  # 반려동물 동반 가능 정보
#     pet_info = Column(Text)             # 반려동물 관련 추가 정보
#
#     # 카테고리
#     cat1 = Column(String(10))
#     cat2 = Column(String(10))
#     cat3 = Column(String(10))
#
#     # 원본 데이터 참조
#     raw_data_id = Column(UUID(as_uuid=True))
#
#     # 메타데이터
#     data_quality_score = Column(DECIMAL(5, 2))
#     processing_status = Column(String(20), default="processed")
#     last_sync_at = Column(DateTime, server_default=func.now())
#     created_at = Column(DateTime, server_default=func.now())
#     updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class NotificationQueue(Base):
    """
    알림 큐 테이블
    사용처: weather-flick-back
    설명: 알림 발송 큐 관리 (배치 처리용)
    """

    __tablename__ = "notification_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    notification_id = Column(
        UUID(as_uuid=True), ForeignKey("notifications.id"), nullable=False, index=True
    )

    # 큐 정보
    queue_name = Column(String(50), nullable=False, index=True)  # high, normal, low
    priority = Column(Integer, default=5)

    # 처리 상태
    status = Column(
        String(20), default="pending"
    )  # pending, processing, completed, failed

    # 스케줄링
    scheduled_for = Column(DateTime, nullable=False, index=True)
    processed_at = Column(DateTime)

    # 재시도 정보
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    next_retry_at = Column(DateTime)

    # 처리 결과
    result = Column(JSONB)
    error_message = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    notification = relationship("Notification")

    # 인덱스
    __table_args__ = (
        Index("idx_queue_status_scheduled", "status", "scheduled_for"),
        Index("idx_queue_priority", "queue_name", "priority"),
        Index("idx_queue_retry", "next_retry_at"),
    )
