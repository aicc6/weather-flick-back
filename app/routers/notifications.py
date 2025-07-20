"""
알림 관련 API 라우터
사용자 알림 설정, 디바이스 토큰, 알림 발송 등을 관리하는 엔드포인트들

[재활성화 날짜: 2025-07-20]
[재활성화 사유: 문의 답변 알림 기능 추가를 위해 재활성화]
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime

from app.database import get_db
from app.models import (
    User, 
    UserNotificationSettings, 
    UserDeviceToken, 
    Notification, 
    NotificationTemplate,
    NotificationStatus,
    NotificationType,
    NotificationChannel
)
from app.schemas import (
    UserNotificationSettingsResponse,
    UserNotificationSettingsCreate,
    UserNotificationSettingsUpdate,
    UserDeviceTokenResponse,
    UserDeviceTokenCreate,
    UserDeviceTokenUpdate,
    NotificationResponse,
    NotificationListResponse,
    NotificationStatsResponse,
    SendNotificationRequest,
    BulkNotificationResponse
)
from app.auth import get_current_active_user
from app.services.fcm_service import FCMService
from app.services.notification_service import NotificationService
from sqlalchemy.sql import func, text

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ===========================================
# 알림 설정 관련 엔드포인트
# ===========================================

@router.get("/settings", response_model=UserNotificationSettingsResponse)
async def get_notification_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    "사용자 알림 설정 조회"
    settings = db.query(UserNotificationSettings).filter(
        UserNotificationSettings.user_id == current_user.user_id
    ).first()
    
    if not settings:
        # 기본 설정 생성
        settings = UserNotificationSettings(
            user_id=current_user.user_id
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings


@router.put("/settings", response_model=UserNotificationSettingsResponse)
async def update_notification_settings(
    settings_update: UserNotificationSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    "사용자 알림 설정 업데이트"
    settings = db.query(UserNotificationSettings).filter(
        UserNotificationSettings.user_id == current_user.user_id
    ).first()
    
    if not settings:
        # 기본 설정 생성
        settings = UserNotificationSettings(
            user_id=current_user.user_id
        )
        db.add(settings)
        db.flush()
    
    # 설정 업데이트
    for field, value in settings_update.dict(exclude_unset=True).items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    return settings


# ===========================================
# 디바이스 토큰 관련 엔드포인트
# ===========================================

@router.post("/device-tokens", response_model=UserDeviceTokenResponse)
async def register_device_token(
    token_data: UserDeviceTokenCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    "FCM 디바이스 토큰 등록"
    # 기존 토큰 확인
    existing_token = db.query(UserDeviceToken).filter(
        UserDeviceToken.device_token == token_data.device_token
    ).first()
    
    if existing_token:
        # 기존 토큰 업데이트
        existing_token.user_id = current_user.user_id
        existing_token.is_active = True
        for field, value in token_data.dict(exclude_unset=True).items():
            setattr(existing_token, field, value)
        db.commit()
        db.refresh(existing_token)
        return existing_token
    
    # 새 토큰 생성
    device_token = UserDeviceToken(
        user_id=current_user.user_id,
        **token_data.dict()
    )
    db.add(device_token)
    db.commit()
    db.refresh(device_token)
    
    return device_token


@router.get("/device-tokens", response_model=List[UserDeviceTokenResponse])
async def get_device_tokens(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    "사용자 디바이스 토큰 목록 조회"
    tokens = db.query(UserDeviceToken).filter(
        UserDeviceToken.user_id == current_user.user_id,
        UserDeviceToken.is_active == True
    ).all()
    
    return tokens


@router.put("/device-tokens/{token_id}", response_model=UserDeviceTokenResponse)
async def update_device_token(
    token_id: uuid.UUID,
    token_update: UserDeviceTokenUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    "디바이스 토큰 업데이트"
    token = db.query(UserDeviceToken).filter(
        UserDeviceToken.id == token_id,
        UserDeviceToken.user_id == current_user.user_id
    ).first()
    
    if not token:
        raise HTTPException(status_code=404, detail="Device token not found")
    
    for field, value in token_update.dict(exclude_unset=True).items():
        setattr(token, field, value)
    
    db.commit()
    db.refresh(token)
    
    return token


@router.delete("/device-tokens/{token_id}")
async def delete_device_token(
    token_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    "디바이스 토큰 삭제"
    token = db.query(UserDeviceToken).filter(
        UserDeviceToken.id == token_id,
        UserDeviceToken.user_id == current_user.user_id
    ).first()
    
    if not token:
        raise HTTPException(status_code=404, detail="Device token not found")
    
    token.is_active = False
    db.commit()
    
    return {"message": "Device token deactivated"}


# ===========================================
# 알림 조회 관련 엔드포인트
# ===========================================

@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    "사용자 알림 목록 조회"
    query = db.query(Notification).filter(
        Notification.user_id == current_user.user_id
    )
    
    if status:
        query = query.filter(Notification.status == status)
    
    if type:
        query = query.filter(Notification.type == type)
    
    # 전체 개수
    total = query.count()
    
    # 페이지네이션
    notifications = query.order_by(Notification.created_at.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    
    return NotificationListResponse(
        notifications=notifications,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    "특정 알림 조회"
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.user_id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return notification


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    "알림 읽음 처리"
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.user_id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.status = NotificationStatus.READ
    notification.read_at = func.now()
    db.commit()
    
    return {"message": "Notification marked as read"}


@router.patch("/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    "모든 알림 읽음 처리"
    db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
        Notification.status != NotificationStatus.READ
    ).update({
        "status": NotificationStatus.READ,
        "read_at": func.now()
    })
    db.commit()
    
    return {"message": "All notifications marked as read"}


@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    "알림 통계 조회"
    # 전체 알림 수
    total_notifications = db.query(Notification).filter(
        Notification.user_id == current_user.user_id
    ).count()
    
    # 읽지 않은 알림 수
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
        Notification.status != NotificationStatus.READ
    ).count()
    
    # 유형별 통계
    by_type = {}
    for notification_type in NotificationType:
        count = db.query(Notification).filter(
            Notification.user_id == current_user.user_id,
            Notification.type == notification_type
        ).count()
        by_type[notification_type.value] = count
    
    # 상태별 통계
    by_status = {}
    for status in NotificationStatus:
        count = db.query(Notification).filter(
            Notification.user_id == current_user.user_id,
            Notification.status == status
        ).count()
        by_status[status.value] = count
    
    # 최근 알림
    recent_notifications = db.query(Notification).filter(
        Notification.user_id == current_user.user_id
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    return NotificationStatsResponse(
        total_notifications=total_notifications,
        unread_count=unread_count,
        by_type=by_type,
        by_status=by_status,
        recent_notifications=recent_notifications
    )


# ===========================================
# 알림 발송 관련 엔드포인트 (관리자용)
# ===========================================

@router.post("/send", response_model=BulkNotificationResponse)
async def send_notifications(
    request: SendNotificationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    "대량 알림 발송 (관리자용)"
    # 관리자 권한 확인
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    notification_service = NotificationService(db)
    
    try:
        result = await notification_service.send_bulk_notifications(
            user_ids=request.user_ids,
            notification_type=request.type,
            channels=request.channels,
            title=request.title,
            message=request.message,
            data=request.data,
            priority=request.priority,
            scheduled_at=request.scheduled_at,
            expires_at=request.expires_at
        )
        
        return BulkNotificationResponse(
            success=True,
            message="Notifications queued successfully",
            queued_count=result["queued_count"],
            failed_count=result["failed_count"],
            notification_ids=result["notification_ids"]
        )
    except Exception as e:
        return BulkNotificationResponse(
            success=False,
            message=f"Failed to send notifications: {str(e)}",
            queued_count=0,
            failed_count=len(request.user_ids),
            notification_ids=[]
        )
