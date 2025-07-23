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
        try:
            # 데이터 검증 및 정규화
            if data:
                # 지역 정보가 있는 경우 특수 문자 처리
                if 'location' in data and data['location']:
                    data['location'] = str(data['location']).strip()
                    logger.info(f"Creating notification for location: {data['location']}")
                
                # 모든 데이터 값을 문자열로 변환하여 JSON 직렬화 문제 방지
                for key, value in data.items():
                    if value is not None and not isinstance(value, (str, int, float, bool, list, dict)):
                        data[key] = str(value)
            
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
            log_details = {
                "user_id": str(user_id),
                "type": notification_type.value,
                "channel": channel.value,
                "data": data
            }
            self._log_notification_event(
                notification.id, 
                "created", 
                "Notification created",
                log_details
            )
            
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification for user {user_id}: {str(e)}")
            logger.error(f"Notification data: type={notification_type}, channel={channel}, data={data}")
            # 트랜잭션 롤백
            self.db.rollback()
            raise
    
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
                    logger.warning(f"User not found: {user_id}")
                    failed_count += 1
                    continue
                
                # 데이터 검증
                validated_data = data.copy() if data else {}
                
                # 각 채널별로 알림 생성
                for channel in channels:
                    try:
                        notification = await self.create_notification(
                            user_id=user_id,
                            notification_type=notification_type,
                            channel=channel,
                            title=title,
                            message=message,
                            data=validated_data,
                            priority=priority,
                            scheduled_at=scheduled_at,
                            expires_at=expires_at
                        )
                        
                        notification_ids.append(notification.id)
                        
                        # 큐에 추가
                        await self._add_to_queue(notification)
                        queued_count += 1
                        
                    except Exception as channel_error:
                        logger.error(f"Error creating {channel.value} notification for user {user_id}: {str(channel_error)}")
                        logger.error(f"Notification details: title='{title}', message='{message}', data={validated_data}")
                        failed_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing notifications for user {user_id}: {str(e)}")
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
            logger.info(f"No active tokens found for user {notification.user_id}")
            return False
        
        logger.info(f"Found {len(tokens)} active tokens for user {notification.user_id}")
        success_count = 0
        failure_details = []
        
        # 데이터 검증 및 정리
        safe_data = {}
        if notification.data:
            for key, value in notification.data.items():
                # None 값 제거 및 문자열 변환
                if value is not None:
                    safe_data[key] = str(value) if not isinstance(value, (str, int, float, bool, list, dict)) else value
        
        # 알림 ID 추가 (Firefox 태그용)
        safe_data['notification_id'] = str(notification.id)
        
        logger.info(f"Sending push notification: title='{notification.title}', data={safe_data}")
        
        for token in tokens:
            try:
                logger.debug(f"Attempting to send to token {token.id}: device={token.device_name}, type={token.device_type}")
                
                # 브라우저 타입 확인 (Firefox 특별 처리)
                is_firefox = token.user_agent and 'firefox' in token.user_agent.lower()
                if is_firefox:
                    logger.debug(f"Firefox browser detected for token {token.id}")
                
                result = await self.fcm_service.send_notification(
                    token=token.device_token,
                    title=notification.title,
                    body=notification.message,
                    data=safe_data,
                    badge=1  # Firefox를 위한 배지 추가
                )
                
                if result:
                    success_count += 1
                    token.last_used = func.now()
                    logger.info(f"✅ Successfully sent push notification to token {token.id} (device: {token.device_name})")
                else:
                    logger.warning(f"❌ Failed to send push notification to token {token.id}")
                    failure_details.append({
                        'token_id': token.id,
                        'device': token.device_name,
                        'reason': 'FCM returned false'
                    })
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Error sending push notification to token {token.id}: {error_msg}")
                logger.error(f"Token details: device_type={token.device_type}, device_name={token.device_name}, created_at={token.created_at}")
                
                failure_details.append({
                    'token_id': token.id,
                    'device': token.device_name,
                    'error': error_msg
                })
                
                # 토큰이 유효하지 않으면 비활성화
                if any(keyword in error_msg.lower() for keyword in ["invalid", "not registered", "unregistered"]):
                    logger.info(f"Deactivating invalid token {token.id}")
                    token.is_active = False
        
        self.db.commit()
        
        # 전송 결과 로깅
        logger.info(f"Push notification summary: {success_count}/{len(tokens)} successful")
        if failure_details:
            logger.warning(f"Failed tokens: {failure_details}")
        
        return success_count > 0
    
    async def _send_email_notification(self, notification: Notification) -> bool:
        """이메일 알림 전송"""
        # 사용자 이메일 조회
        user = self.db.query(User).filter(User.user_id == notification.user_id).first()
        if not user:
            logger.warning(f"User not found for email notification: {notification.user_id}")
            return False
        
        if not user.email:
            logger.warning(f"User {notification.user_id} has no email address")
            return False
        
        try:
            # 데이터 검증 및 정리
            safe_data = {}
            if notification.data:
                for key, value in notification.data.items():
                    if value is not None:
                        # 특수 문자 처리
                        if isinstance(value, str):
                            safe_data[key] = value.strip()
                        else:
                            safe_data[key] = value
            
            logger.info(f"Sending email notification to {user.email}: type={notification.type.value}")
            
            # 문의 답변 알림인 경우 특별 처리
            if notification.type == NotificationType.CONTACT_ANSWER:
                return await self.email_service.send_contact_answer_email(
                    to_email=user.email,
                    contact_title=safe_data.get('contact_title', ''),
                    answer_content=notification.message,
                    contact_id=safe_data.get('contact_id', 0)
                )
            # 날씨 알림인 경우
            elif notification.type == NotificationType.WEATHER_ALERT:
                location = safe_data.get('location', '알 수 없음')
                weather_condition = safe_data.get('condition', '')
                temperature = safe_data.get('temperature', '')
                
                return await self.email_service.send_weather_alert_email(
                    to_email=user.email,
                    location=location,
                    weather_condition=weather_condition,
                    temperature=temperature,
                    alert_type=safe_data.get('alert_type', 'weather_change')
                )
            else:
                # 일반 알림 이메일 전송
                return await self.email_service.send_notification_email(
                    to_email=user.email,
                    subject=notification.title,
                    content=notification.message,
                    template_data=safe_data
                )
        except Exception as e:
            logger.error(f"Error sending email notification to {user.email}: {str(e)}")
            logger.error(f"Notification details: id={notification.id}, type={notification.type.value}, data={notification.data}")
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
        try:
            queue_name = "high" if notification.priority >= 8 else "normal" if notification.priority >= 5 else "low"
            
            queue_item = NotificationQueue(
                notification_id=notification.id,
                queue_name=queue_name,
                priority=notification.priority,
                scheduled_for=notification.scheduled_at or func.now()
            )
            
            self.db.add(queue_item)
            self.db.commit()
            
            logger.debug(f"Added notification {notification.id} to {queue_name} queue")
            
        except Exception as e:
            logger.error(f"Error adding notification {notification.id} to queue: {str(e)}")
            self.db.rollback()
            raise
    
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