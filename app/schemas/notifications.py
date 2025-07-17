"""
알림 관련 Pydantic 스키마
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.models import NotificationStatus, NotificationType, NotificationChannel


# ===========================================
# 사용자 알림 설정 스키마
# ===========================================

class UserNotificationSettingsBase(BaseModel):
    """사용자 알림 설정 베이스 스키마"""
    push_enabled: bool = True
    email_enabled: bool = True
    sms_enabled: bool = False
    in_app_enabled: bool = True
    
    # 알림 유형별 설정
    weather_alerts: bool = True
    travel_plan_updates: bool = True
    recommendation_updates: bool = True
    marketing_messages: bool = False
    system_messages: bool = True
    emergency_alerts: bool = True
    
    # 다이제스트 설정
    digest_enabled: bool = False
    digest_frequency: str = "daily"  # daily, weekly, monthly
    digest_time: str = "09:00"
    
    # 방해금지 설정
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    
    # 위치 기반 설정
    location_based_notifications: bool = True
    preferred_language: str = "ko"


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
    
    digest_enabled: Optional[bool] = None
    digest_frequency: Optional[str] = None
    digest_time: Optional[str] = None
    
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    
    location_based_notifications: Optional[bool] = None
    preferred_language: Optional[str] = None


class UserNotificationSettingsResponse(UserNotificationSettingsBase):
    """사용자 알림 설정 응답 스키마"""
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ===========================================
# 디바이스 토큰 스키마
# ===========================================

class UserDeviceTokenBase(BaseModel):
    """디바이스 토큰 베이스 스키마"""
    device_token: str = Field(..., description="FCM 디바이스 토큰")
    device_type: str = Field(..., description="디바이스 유형 (android, ios, web)")
    device_name: Optional[str] = Field(None, description="디바이스 이름")
    app_version: Optional[str] = Field(None, description="앱 버전")
    os_version: Optional[str] = Field(None, description="OS 버전")


class UserDeviceTokenCreate(UserDeviceTokenBase):
    """디바이스 토큰 생성 스키마"""
    pass


class UserDeviceTokenUpdate(BaseModel):
    """디바이스 토큰 업데이트 스키마"""
    device_name: Optional[str] = None
    app_version: Optional[str] = None
    os_version: Optional[str] = None
    is_active: Optional[bool] = None


class UserDeviceTokenResponse(UserDeviceTokenBase):
    """디바이스 토큰 응답 스키마"""
    id: uuid.UUID
    user_id: uuid.UUID
    is_active: bool
    last_used: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ===========================================
# 알림 스키마
# ===========================================

class NotificationBase(BaseModel):
    """알림 베이스 스키마"""
    type: NotificationType
    channel: NotificationChannel
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=1000)
    data: Optional[Dict[str, Any]] = None
    priority: int = Field(default=5, ge=1, le=10)


class NotificationCreate(NotificationBase):
    """알림 생성 스키마"""
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class NotificationResponse(NotificationBase):
    """알림 응답 스키마"""
    id: uuid.UUID
    user_id: uuid.UUID
    status: NotificationStatus
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    failure_reason: Optional[str] = None
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """알림 목록 응답 스키마"""
    notifications: List[NotificationResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class NotificationStatsResponse(BaseModel):
    """알림 통계 응답 스키마"""
    total_notifications: int
    unread_count: int
    by_type: Dict[str, int]
    by_status: Dict[str, int]
    recent_notifications: List[NotificationResponse]


# ===========================================
# 대량 알림 발송 스키마
# ===========================================

class SendNotificationRequest(BaseModel):
    """대량 알림 발송 요청 스키마"""
    user_ids: List[uuid.UUID] = Field(..., description="수신자 사용자 ID 목록")
    type: NotificationType = Field(..., description="알림 유형")
    channels: List[NotificationChannel] = Field(..., description="발송 채널 목록")
    title: str = Field(..., max_length=200, description="알림 제목")
    message: str = Field(..., max_length=1000, description="알림 내용")
    data: Optional[Dict[str, Any]] = Field(None, description="추가 데이터")
    priority: int = Field(default=5, ge=1, le=10, description="우선순위")
    scheduled_at: Optional[datetime] = Field(None, description="예약 발송 시간")
    expires_at: Optional[datetime] = Field(None, description="만료 시간")


class BulkNotificationResponse(BaseModel):
    """대량 알림 발송 응답 스키마"""
    success: bool
    message: str
    queued_count: int
    failed_count: int
    notification_ids: List[uuid.UUID]


# ===========================================
# 알림 템플릿 스키마
# ===========================================

class NotificationTemplateBase(BaseModel):
    """알림 템플릿 베이스 스키마"""
    name: str = Field(..., max_length=100)
    type: NotificationType
    channel: NotificationChannel
    title_template: str = Field(..., max_length=200)
    message_template: str = Field(..., max_length=1000)
    data_template: Optional[Dict[str, Any]] = None
    is_active: bool = True


class NotificationTemplateCreate(NotificationTemplateBase):
    """알림 템플릿 생성 스키마"""
    pass


class NotificationTemplateUpdate(BaseModel):
    """알림 템플릿 업데이트 스키마"""
    name: Optional[str] = None
    title_template: Optional[str] = None
    message_template: Optional[str] = None
    data_template: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class NotificationTemplateResponse(NotificationTemplateBase):
    """알림 템플릿 응답 스키마"""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True