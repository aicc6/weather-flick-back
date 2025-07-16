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
from typing import Any

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
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
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

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # OAuth 사용자는 비밀번호가 없을 수 있음
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
    travel_plans = relationship("TravelPlan", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("UserActivityLog", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user")


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

    plan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
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


class TravelRoute(Base):
    """
    여행 경로 정보 테이블
    사용처: weather-flick-back
    설명: 여행 계획의 상세 경로 및 교통 정보
    """
    __tablename__ = "travel_routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    travel_plan_id = Column(UUID(as_uuid=True), ForeignKey("travel_plans.plan_id"), nullable=False)
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
    travel_route_id = Column(UUID(as_uuid=True), ForeignKey("travel_routes.id"), nullable=False)

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

    destination_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
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
    region_code = Column(String, ForeignKey("regions.region_code"), nullable=False, index=True)
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
    """
    축제/행사 정보 테이블
    사용처: weather-flick-back, weather-flick-admin-back, weather-flick-batch
    설명: 지역 축제 및 행사 정보
    """
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
    region_code = Column(String, ForeignKey("regions.region_code"), nullable=False, index=True)
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

    weather_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    destination_id = Column(UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=True)

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
    api_provider = Column(String(50), nullable=False)  # 'tourapi', 'kma', 'google_maps' 등
    endpoint = Column(String(200), nullable=False)
    request_method = Column(String(10), default='GET')
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
        Index('idx_historical_weather_region_date', 'region_code', 'weather_date'),
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
        Index('idx_weather_forecast_region_date', 'region_code', 'forecast_date'),
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

    review_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    destination_id = Column(UUID(as_uuid=True), ForeignKey("destinations.destination_id"), nullable=True)
    travel_plan_id = Column(UUID(as_uuid=True), ForeignKey("travel_plans.plan_id"), nullable=True)
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
    parent_id = Column(UUID(as_uuid=True), ForeignKey("reviews_recommend.id"), nullable=True)  # 답글용

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

    __table_args__ = (UniqueConstraint('course_id', 'user_id', name='uq_likes_recommend_course_user'),)

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
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews_recommend.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    is_like = Column(Boolean, nullable=False)  # True=Like, False=Dislike
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('review_id', 'user_id', 'is_like', name='uq_review_like_user_type'),
    )


class TravelCourseLike(Base):
    """
    여행 코스 좋아요 테이블
    사용처: weather-flick-back
    설명: 사용자가 좋아요한 여행 코스
    """
    __tablename__ = "travel_course_likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
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
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)
    approval_status = Column(SqlEnum('PENDING', 'PROCESSING', 'COMPLETE', name='approval_status'), default='PENDING', nullable=False)
    password_hash = Column(String(128), nullable=True)
    views = Column(Integer, default=0, nullable=False)


class ChatMessage(Base):
    """
    챗봇 메시지 테이블
    사용처: weather-flick-back
    설명: AI 챗봇 대화 기록
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    message = Column(Text, nullable=False)
    sender = Column(String, nullable=False)  # 'user' 또는 'bot'
    context = Column(JSONB, nullable=True)  # 대화 컨텍스트
    suggestions = Column(JSONB, nullable=True)  # 추천 질문 목록
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

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    activity_type = Column(String, nullable=False)
    resource_type = Column(String)
    details = Column(JSONB)
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
    action = Column(String, nullable=False)  # 수행된 작업 (예: USER_DELETE, USER_UPDATE)
    description = Column(Text, nullable=False)  # 작업 설명
    target_resource = Column(String, nullable=True)  # 대상 리소스 (예: user_id, plan_id)
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
    logs = relationship("AdminBatchJobDetail", back_populates="job", cascade="all, delete-orphan")

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
    job_id = Column(UUID(as_uuid=True), ForeignKey("admin_batch_jobs.id", ondelete="CASCADE"), nullable=False)
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
Index("idx_weather_forecast_location", WeatherData.forecast_date, WeatherData.grid_x, WeatherData.grid_y)
Index("idx_weather_destination_date", WeatherData.destination_id, WeatherData.forecast_date)

# 리뷰 관련 인덱스
Index("idx_review_destination_date", Review.destination_id, Review.created_at)
Index("idx_review_user_rating", Review.user_id, Review.rating)

# 지역별 시설 정보 인덱스
Index("idx_tourist_attractions_region_category", TouristAttraction.region_code, TouristAttraction.category_code)
Index("idx_cultural_facilities_region_type", CulturalFacility.region_code, CulturalFacility.facility_type)
Index("idx_festivals_events_region_dates", FestivalEvent.region_code, FestivalEvent.event_start_date, FestivalEvent.event_end_date)
Index("idx_restaurants_region_cuisine", Restaurant.region_code, Restaurant.cuisine_type)
Index("idx_accommodations_region_type", Accommodation.region_code, Accommodation.accommodation_type)
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


class WeatherResponse(BaseModel):
    """날씨 응답 스키마"""
    city: str
    country: str
    current: WeatherCondition
    timezone: str
    local_time: str


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
    code: str
    redirect_uri: str


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


# 맞춤 일정 추천 관련 모델들
class CustomTravelRecommendationRequest(BaseModel):
    """맞춤 일정 추천 요청 모델"""
    region_code: str = Field(..., description="지역 코드")
    region_name: str = Field(..., description="지역 이름")
    period: str = Field(..., description="여행 기간 (당일치기, 1박2일 등)")
    days: int = Field(..., ge=1, le=7, description="여행 일수")
    who: str = Field(..., description="동행자 유형 (solo, couple, family, friends, colleagues, group)")
    styles: list[str] = Field(..., description="여행 스타일 (activity, hotplace, nature, landmark, healing, culture, local, shopping, food, pet)")
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
