
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid


class Activity(BaseModel):
    time: str
    type: str
    place: str
    description: str
    address: str | None = None

class DayItinerary(BaseModel):
    day: int
    title: str
    activities: list[Activity]

class TravelCourseLikeCreate(BaseModel):
    user_id: int
    title: str
    subtitle: str | None = None
    summary: str | None = None
    description: str | None = None
    region: str | None = None
    itinerary: list[DayItinerary]

class TravelCourseLikeResponse(TravelCourseLikeCreate):
    id: int

    class Config:
        from_attributes = True


# ===========================================
# 알림 관련 스키마
# ===========================================

class NotificationTypeEnum(str, Enum):
    """알림 유형"""
    WEATHER_ALERT = "WEATHER_ALERT"
    TRAVEL_PLAN_UPDATE = "TRAVEL_PLAN_UPDATE"
    RECOMMENDATION = "RECOMMENDATION"
    MARKETING = "MARKETING"
    SYSTEM = "SYSTEM"
    EMERGENCY = "EMERGENCY"


class NotificationChannelEnum(str, Enum):
    """알림 채널"""
    PUSH = "PUSH"
    EMAIL = "EMAIL"
    SMS = "SMS"
    IN_APP = "IN_APP"


class NotificationStatusEnum(str, Enum):
    """알림 상태"""
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"


class UserNotificationSettingsBase(BaseModel):
    """사용자 알림 설정 기본 스키마"""
    # 알림 채널별 설정
    push_enabled: bool = True
    email_enabled: bool = False
    sms_enabled: bool = False
    in_app_enabled: bool = True
    
    # 알림 유형별 설정
    weather_alerts: bool = True
    travel_plan_updates: bool = True
    recommendation_updates: bool = True
    marketing_messages: bool = False
    system_messages: bool = True
    emergency_alerts: bool = True
    
    # 방해 금지 시간 설정
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None  # HH:MM 형식
    quiet_hours_end: Optional[str] = None    # HH:MM 형식
    
    # 알림 빈도 설정
    digest_enabled: bool = False
    digest_frequency: str = "daily"  # daily, weekly


class UserNotificationSettingsCreate(UserNotificationSettingsBase):
    """사용자 알림 설정 생성 스키마"""
    pass


class UserNotificationSettingsUpdate(BaseModel):
    """사용자 알림 설정 업데이트 스키마"""
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    
    weather_alerts: Optional[bool] = None
    travel_plan_updates: Optional[bool] = None
    recommendation_updates: Optional[bool] = None
    marketing_messages: Optional[bool] = None
    system_messages: Optional[bool] = None
    emergency_alerts: Optional[bool] = None
    
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    
    digest_enabled: Optional[bool] = None
    digest_frequency: Optional[str] = None


class UserNotificationSettingsResponse(UserNotificationSettingsBase):
    """사용자 알림 설정 응답 스키마"""
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserDeviceTokenBase(BaseModel):
    """사용자 디바이스 토큰 기본 스키마"""
    device_token: str
    device_type: Optional[str] = None  # android, ios, web
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    user_agent: Optional[str] = None
    app_version: Optional[str] = None
    os_version: Optional[str] = None


class UserDeviceTokenCreate(UserDeviceTokenBase):
    """사용자 디바이스 토큰 생성 스키마"""
    pass


class UserDeviceTokenUpdate(BaseModel):
    """사용자 디바이스 토큰 업데이트 스키마"""
    device_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserDeviceTokenResponse(UserDeviceTokenBase):
    """사용자 디바이스 토큰 응답 스키마"""
    id: uuid.UUID
    user_id: uuid.UUID
    is_active: bool
    last_used: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationBase(BaseModel):
    """알림 기본 스키마"""
    type: NotificationTypeEnum
    channel: NotificationChannelEnum
    title: str = Field(..., max_length=255)
    message: str
    data: Optional[dict] = None
    priority: int = Field(default=5, ge=1, le=10)
    expires_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None


class NotificationCreate(NotificationBase):
    """알림 생성 스키마"""
    user_id: uuid.UUID


class NotificationUpdate(BaseModel):
    """알림 업데이트 스키마"""
    status: Optional[NotificationStatusEnum] = None
    read_at: Optional[datetime] = None


class NotificationResponse(NotificationBase):
    """알림 응답 스키마"""
    id: uuid.UUID
    user_id: uuid.UUID
    status: NotificationStatusEnum
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    retry_count: int
    external_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """알림 목록 응답 스키마"""
    notifications: list[NotificationResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class NotificationTemplateBase(BaseModel):
    """알림 템플릿 기본 스키마"""
    name: str = Field(..., max_length=100)
    type: NotificationTypeEnum
    channel: NotificationChannelEnum
    title_template: str = Field(..., max_length=255)
    message_template: str
    variables: Optional[dict] = None
    description: Optional[str] = None
    version: str = "1.0"


class NotificationTemplateCreate(NotificationTemplateBase):
    """알림 템플릿 생성 스키마"""
    pass


class NotificationTemplateUpdate(BaseModel):
    """알림 템플릿 업데이트 스키마"""
    title_template: Optional[str] = None
    message_template: Optional[str] = None
    variables: Optional[dict] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationTemplateResponse(NotificationTemplateBase):
    """알림 템플릿 응답 스키마"""
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationStatsResponse(BaseModel):
    """알림 통계 응답 스키마"""
    total_notifications: int
    unread_count: int
    by_type: dict[str, int]
    by_status: dict[str, int]
    recent_notifications: list[NotificationResponse]


class SendNotificationRequest(BaseModel):
    """알림 발송 요청 스키마"""
    user_ids: list[uuid.UUID]
    type: NotificationTypeEnum
    channels: list[NotificationChannelEnum]
    title: str = Field(..., max_length=255)
    message: str
    data: Optional[dict] = None
    priority: int = Field(default=5, ge=1, le=10)
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class BulkNotificationResponse(BaseModel):
    """대량 알림 발송 응답 스키마"""
    success: bool
    message: str
    queued_count: int
    failed_count: int
    notification_ids: list[uuid.UUID]
