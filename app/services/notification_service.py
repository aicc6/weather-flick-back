"""
알림 서비스
알림 생성, 전송, 큐 관리 등을 담당하는 서비스 클래스
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import asyncio
import logging

from app.models import (
    User,
    UserNotificationSettings,
    UserDeviceToken,
    Notification,
    NotificationQueue,
    NotificationLog,
    NotificationTemplate,
    NotificationStatus,
    NotificationType,
    NotificationChannel
)
from app.services.fcm_service import FCMService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class NotificationService:
    """알림 서비스 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.fcm_service = FCMService()
        self.email_service = EmailService()
    
    async def create_notification(
        self,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        channel: NotificationChannel,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        scheduled_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None
    ) -> Notification:
        """알림 생성"""
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            channel=channel,
            title=title,
            message=message,
            data=data or {},
            priority=priority,
            scheduled_at=scheduled_at,
            expires_at=expires_at
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        # 로그 기록
        self._log_notification_event(notification.id, "created", "Notification created")
        
        return notification
    
    async def send_notification(self, notification: Notification) -> bool:
        """개별 알림 전송"""
        try:
            # 사용자 알림 설정 확인
            if not await self._check_user_notification_settings(notification):
                self._log_notification_event(
                    notification.id, 
                    "skipped", 
                    "User notification settings disabled"
                )
                return False
            
            # 방해금지 시간 확인
            if await self._is_quiet_hours(notification.user_id):
                # 나중에 다시 시도하도록 큐에 추가
                await self._reschedule_notification(notification)
                return False
            
            # 채널별 전송
            success = False
            if notification.channel == NotificationChannel.PUSH:
                success = await self._send_push_notification(notification)
            elif notification.channel == NotificationChannel.EMAIL:
                success = await self._send_email_notification(notification)
            elif notification.channel == NotificationChannel.SMS:
                success = await self._send_sms_notification(notification)
            elif notification.channel == NotificationChannel.IN_APP:
                success = await self._send_in_app_notification(notification)
            
            if success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = func.now()
                self._log_notification_event(notification.id, "sent", "Notification sent successfully")
            else:
                notification.status = NotificationStatus.FAILED
                notification.retry_count += 1
                self._log_notification_event(notification.id, "failed", "Failed to send notification")
            
            self.db.commit()
            return success
            
        except Exception as e:
            logger.error(f"Error sending notification {notification.id}: {str(e)}")
            notification.status = NotificationStatus.FAILED
            notification.failure_reason = str(e)
            notification.retry_count += 1
            self.db.commit()
            
            self._log_notification_event(notification.id, "error", f"Error: {str(e)}")
            return False
    
    async def send_bulk_notifications(
        self,
        user_ids: List[uuid.UUID],
        notification_type: NotificationType,
        channels: List[NotificationChannel],
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        scheduled_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """대량 알림 발송"""
        notification_ids = []
        queued_count = 0
        failed_count = 0
        
        for user_id in user_ids:
            try:
                # 사용자 존재 확인
                user = self.db.query(User).filter(User.user_id == user_id).first()
                if not user:
                    failed_count += 1
                    continue
                
                # 각 채널별로 알림 생성
                for channel in channels:
                    notification = await self.create_notification(
                        user_id=user_id,
                        notification_type=notification_type,
                        channel=channel,
                        title=title,
                        message=message,
                        data=data,
                        priority=priority,
                        scheduled_at=scheduled_at,
                        expires_at=expires_at
                    )
                    
                    notification_ids.append(notification.id)
                    
                    # 큐에 추가
                    await self._add_to_queue(notification)
                    queued_count += 1
                    
            except Exception as e:
                logger.error(f"Error creating notification for user {user_id}: {str(e)}")
                failed_count += 1
        
        return {
            "notification_ids": notification_ids,
            "queued_count": queued_count,
            "failed_count": failed_count
        }
    
    async def process_notification_queue(self, queue_name: str = "normal", limit: int = 100):
        """알림 큐 처리"""
        # 처리 대기 중인 알림 조회
        queue_items = self.db.query(NotificationQueue).filter(
            NotificationQueue.queue_name == queue_name,
            NotificationQueue.status == "pending",
            NotificationQueue.scheduled_for <= func.now()
        ).order_by(
            NotificationQueue.priority.desc(),
            NotificationQueue.scheduled_for.asc()
        ).limit(limit).all()
        
        processed_count = 0
        
        for queue_item in queue_items:
            try:
                # 상태 업데이트
                queue_item.status = "processing"
                self.db.commit()
                
                # 알림 조회
                notification = self.db.query(Notification).filter(
                    Notification.id == queue_item.notification_id
                ).first()
                
                if not notification:
                    queue_item.status = "failed"
                    queue_item.error_message = "Notification not found"
                    self.db.commit()
                    continue
                
                # 만료 확인
                if notification.expires_at and notification.expires_at < datetime.now():
                    queue_item.status = "completed"
                    queue_item.result = {"expired": True}
                    notification.status = NotificationStatus.FAILED
                    notification.failure_reason = "Expired"
                    self.db.commit()
                    continue
                
                # 알림 전송
                success = await self.send_notification(notification)
                
                if success:
                    queue_item.status = "completed"
                    queue_item.result = {"success": True}
                    queue_item.processed_at = func.now()
                else:
                    # 재시도 로직
                    if queue_item.attempt_count < queue_item.max_attempts:
                        queue_item.attempt_count += 1
                        queue_item.next_retry_at = func.now() + timedelta(minutes=5 * queue_item.attempt_count)
                        queue_item.status = "pending"
                    else:
                        queue_item.status = "failed"
                        queue_item.error_message = "Max retry attempts reached"
                
                self.db.commit()
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing queue item {queue_item.id}: {str(e)}")
                queue_item.status = "failed"
                queue_item.error_message = str(e)
                self.db.commit()
        
        return processed_count
    
    async def _check_user_notification_settings(self, notification: Notification) -> bool:
        """사용자 알림 설정 확인"""
        settings = self.db.query(UserNotificationSettings).filter(
            UserNotificationSettings.user_id == notification.user_id
        ).first()
        
        if not settings:
            return True  # 설정이 없으면 기본값으로 허용
        
        # 채널별 설정 확인
        if notification.channel == NotificationChannel.PUSH and not settings.push_enabled:
            return False
        if notification.channel == NotificationChannel.EMAIL and not settings.email_enabled:
            return False
        if notification.channel == NotificationChannel.SMS and not settings.sms_enabled:
            return False
        if notification.channel == NotificationChannel.IN_APP and not settings.in_app_enabled:
            return False
        
        # 유형별 설정 확인
        if notification.type == NotificationType.WEATHER_ALERT and not settings.weather_alerts:
            return False
        if notification.type == NotificationType.TRAVEL_PLAN_UPDATE and not settings.travel_plan_updates:
            return False
        if notification.type == NotificationType.RECOMMENDATION and not settings.recommendation_updates:
            return False
        if notification.type == NotificationType.MARKETING and not settings.marketing_messages:
            return False
        if notification.type == NotificationType.SYSTEM and not settings.system_messages:
            return False
        if notification.type == NotificationType.EMERGENCY and not settings.emergency_alerts:
            return False
        
        return True
    
    async def _is_quiet_hours(self, user_id: uuid.UUID) -> bool:
        """방해금지 시간 확인"""
        settings = self.db.query(UserNotificationSettings).filter(
            UserNotificationSettings.user_id == user_id
        ).first()
        
        if not settings or not settings.quiet_hours_enabled:
            return False
        
        if not settings.quiet_hours_start or not settings.quiet_hours_end:
            return False
        
        now = datetime.now().time()
        start_time = datetime.strptime(settings.quiet_hours_start, "%H:%M").time()
        end_time = datetime.strptime(settings.quiet_hours_end, "%H:%M").time()
        
        if start_time <= end_time:
            return start_time <= now <= end_time
        else:
            return now >= start_time or now <= end_time
    
    async def _send_push_notification(self, notification: Notification) -> bool:
        """푸시 알림 전송"""
        # 사용자 디바이스 토큰 조회
        tokens = self.db.query(UserDeviceToken).filter(
            UserDeviceToken.user_id == notification.user_id,
            UserDeviceToken.is_active == True
        ).all()
        
        if not tokens:
            return False
        
        success_count = 0
        
        for token in tokens:
            try:
                result = await self.fcm_service.send_notification(
                    token=token.device_token,
                    title=notification.title,
                    body=notification.message,
                    data=notification.data
                )
                
                if result:
                    success_count += 1
                    token.last_used = func.now()
                    
            except Exception as e:
                logger.error(f"Error sending push notification to token {token.id}: {str(e)}")
                # 토큰이 유효하지 않으면 비활성화
                if "invalid" in str(e).lower() or "not registered" in str(e).lower():
                    token.is_active = False
        
        self.db.commit()
        return success_count > 0
    
    async def _send_email_notification(self, notification: Notification) -> bool:
        """이메일 알림 전송"""
        # 사용자 이메일 조회
        user = self.db.query(User).filter(User.user_id == notification.user_id).first()
        if not user:
            return False
        
        try:
            return await self.email_service.send_notification_email(
                to_email=user.email,
                subject=notification.title,
                content=notification.message,
                template_data=notification.data
            )
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False
    
    async def _send_sms_notification(self, notification: Notification) -> bool:
        """SMS 알림 전송 (추후 구현)"""
        # SMS 서비스 구현 필요
        return False
    
    async def _send_in_app_notification(self, notification: Notification) -> bool:
        """인앱 알림 전송"""
        # 인앱 알림은 데이터베이스에 저장하는 것으로 처리
        notification.status = NotificationStatus.DELIVERED
        notification.delivered_at = func.now()
        return True
    
    async def _add_to_queue(self, notification: Notification):
        """알림을 큐에 추가"""
        queue_name = "high" if notification.priority >= 8 else "normal" if notification.priority >= 5 else "low"
        
        queue_item = NotificationQueue(
            notification_id=notification.id,
            queue_name=queue_name,
            priority=notification.priority,
            scheduled_for=notification.scheduled_at or func.now()
        )
        
        self.db.add(queue_item)
        self.db.commit()
    
    async def _reschedule_notification(self, notification: Notification):
        """알림 재스케줄링"""
        # 방해금지 시간이 끝난 후로 스케줄링
        settings = self.db.query(UserNotificationSettings).filter(
            UserNotificationSettings.user_id == notification.user_id
        ).first()
        
        if settings and settings.quiet_hours_end:
            next_time = datetime.strptime(settings.quiet_hours_end, "%H:%M").time()
            next_datetime = datetime.combine(datetime.now().date(), next_time)
            
            if next_datetime <= datetime.now():
                next_datetime += timedelta(days=1)
            
            notification.scheduled_at = next_datetime
            self.db.commit()
    
    def _log_notification_event(
        self, 
        notification_id: uuid.UUID, 
        event_type: str, 
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """알림 이벤트 로깅"""
        log = NotificationLog(
            notification_id=notification_id,
            event_type=event_type,
            message=message,
            details=details or {}
        )
        
        self.db.add(log)
        self.db.commit()