"""
FCM (Firebase Cloud Messaging) 서비스 v2
Firebase Admin SDK를 사용하여 FCM HTTP v1 API로 푸시 알림 전송
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.messaging import Message, Notification, AndroidConfig, APNSConfig, WebpushConfig

logger = logging.getLogger(__name__)


class FCMService:
    """FCM 푸시 알림 서비스 (HTTP v1 API)"""

    def __init__(self):
        # Firebase Admin SDK 초기화
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Firebase Admin SDK 초기화"""
        try:
            # 이미 초기화되어 있는지 확인
            if not firebase_admin._apps:
                # 서비스 계정 키 파일 경로
                cred_path = os.path.join(
                    os.path.dirname(__file__), 
                    "..", "..", "config", "firebase-service-account.json"
                )
                
                if not os.path.exists(cred_path):
                    logger.error(f"Firebase service account file not found: {cred_path}")
                    raise FileNotFoundError(f"Firebase service account file not found: {cred_path}")
                
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                logger.info("Firebase Admin SDK already initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
            raise

    async def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image: Optional[str] = None,
        badge: Optional[int] = None,
        sound: str = "default",
        priority: str = "high",
    ) -> bool:
        """단일 디바이스에 푸시 알림 전송"""
        
        try:
            # 입력 값 검증 및 정규화
            if not token or not isinstance(token, str):
                logger.error(f"Invalid FCM token: {token}")
                return False
            
            # 제목과 본문 길이 제한 및 정규화
            title = str(title).strip() if title else "\uc54c\ub9bc"
            body = str(body).strip() if body else ""
            
            # FCM 제한사항: 제목 최대 200자, 본문 최대 4000자
            if len(title) > 200:
                title = title[:197] + "..."
            if len(body) > 4000:
                body = body[:3997] + "..."
            
            # 데이터 페이로드 준비 (모든 값은 문자열이어야 함)
            data_payload = {}
            if data:
                for k, v in data.items():
                    # 키와 값 모두 문자열로 변환
                    key = str(k).strip()
                    if v is None:
                        value = ""
                    elif isinstance(v, (list, dict)):
                        # 복잡한 객체는 JSON 문자열로 변환
                        import json
                        try:
                            value = json.dumps(v, ensure_ascii=False)
                        except:
                            value = str(v)
                    else:
                        value = str(v)
                    
                    # FCM 데이터 페이로드 키와 값 길이 제한
                    if len(key) > 1024:
                        key = key[:1024]
                    if len(value) > 1024:
                        value = value[:1021] + "..."
                    
                    data_payload[key] = value
            
            logger.debug(f"Sending FCM notification: title='{title[:50]}...', token='{token[:20]}...'")

            # FCM 메시지 생성 - Firefox 호환성 개선
            message = Message(
                token=token,
                notification=Notification(
                    title=title,
                    body=body,
                    image=image
                ),
                data=data_payload,
                android=AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        sound=sound,
                        notification_count=badge
                    )
                ),
                apns=APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound=sound,
                            badge=badge
                        )
                    )
                ),
                webpush=WebpushConfig(
                    notification=messaging.WebpushNotification(
                        title=title,
                        body=body,
                        icon=image or '/pwa-192x192.png',
                        badge='/pwa-64x64.png',
                        tag=data_payload.get('notification_id', str(int(datetime.now().timestamp()))),
                        require_interaction=False,
                        silent=False,
                        data=data_payload  # Firefox를 위해 데이터도 포함
                    ),
                    headers={
                        'TTL': '86400',  # 24시간
                        'Urgency': 'high' if priority == 'high' else 'normal'
                    },
                    data=data_payload  # 데이터 페이로드도 웹푸시에 포함
                )
            )

            # 메시지 전송
            response = messaging.send(message)
            logger.info(f"FCM notification sent successfully: {response}")
            return True

        except messaging.UnregisteredError:
            logger.error(f"FCM token is not registered: {token[:20]}...")
            return False
        except ValueError as e:
            logger.error(f"Invalid FCM message arguments: {str(e)}")
            logger.error(f"Title: '{title}', Body: '{body[:100]}...', Data: {data_payload}")
            return False
        except Exception as e:
            logger.error(f"Error sending FCM notification: {str(e)}")
            logger.error(f"Token: {token[:20]}..., Title: '{title}', Data keys: {list(data_payload.keys()) if data_payload else []}")
            return False

    async def send_multicast_notification(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image: Optional[str] = None,
        badge: Optional[int] = None,
        sound: str = "default",
        priority: str = "high",
    ) -> Dict[str, Any]:
        """다중 디바이스에 푸시 알림 전송"""
        
        if not tokens:
            return {"success": 0, "failure": 0, "results": []}

        try:
            # 데이터 페이로드 준비
            if data:
                data_payload = {k: str(v) for k, v in data.items()}
            else:
                data_payload = {}

            # MulticastMessage 생성 - Firefox 호환성 개선
            message = messaging.MulticastMessage(
                tokens=tokens,
                notification=Notification(
                    title=title,
                    body=body,
                    image=image
                ),
                data=data_payload,
                android=AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        sound=sound,
                        notification_count=badge
                    )
                ),
                apns=APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound=sound,
                            badge=badge
                        )
                    )
                ),
                webpush=WebpushConfig(
                    notification=messaging.WebpushNotification(
                        title=title,
                        body=body,
                        icon=image or '/pwa-192x192.png',
                        badge='/pwa-64x64.png',
                        tag=data_payload.get('notification_id', str(int(datetime.now().timestamp()))),
                        require_interaction=False,
                        silent=False,
                        data=data_payload
                    ),
                    headers={
                        'TTL': '86400',
                        'Urgency': 'high' if priority == 'high' else 'normal'
                    },
                    data=data_payload
                )
            )

            # 멀티캐스트 메시지 전송
            batch_response = messaging.send_each_for_multicast(message)
            
            success_count = batch_response.success_count
            failure_count = batch_response.failure_count
            
            # 결과 처리
            results = []
            for i, response in enumerate(batch_response.responses):
                if response.success:
                    results.append({
                        "token": tokens[i][:20] + "...",
                        "success": True,
                        "message_id": response.message_id
                    })
                else:
                    results.append({
                        "token": tokens[i][:20] + "...",
                        "success": False,
                        "error": str(response.exception)
                    })
            
            logger.info(
                f"FCM multicast sent: {success_count} success, {failure_count} failure"
            )
            
            return {
                "success": success_count,
                "failure": failure_count,
                "results": results
            }

        except Exception as e:
            logger.error(f"Error sending FCM multicast notification: {str(e)}")
            return {"success": 0, "failure": len(tokens), "results": []}

    async def send_topic_notification(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image: Optional[str] = None,
        badge: Optional[int] = None,
        sound: str = "default",
        priority: str = "high",
    ) -> bool:
        """토픽 구독자들에게 푸시 알림 전송"""
        
        try:
            # 데이터 페이로드 준비
            if data:
                data_payload = {k: str(v) for k, v in data.items()}
            else:
                data_payload = {}

            # 토픽 메시지 생성
            message = Message(
                topic=topic,
                notification=Notification(
                    title=title,
                    body=body,
                    image=image
                ),
                data=data_payload,
                android=AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        sound=sound,
                        notification_count=badge
                    )
                ),
                apns=APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound=sound,
                            badge=badge
                        )
                    )
                ),
                webpush=WebpushConfig(
                    notification=messaging.WebpushNotification(
                        title=title,
                        body=body,
                        icon=image,
                        badge=str(badge) if badge else None
                    )
                )
            )

            # 메시지 전송
            response = messaging.send(message)
            logger.info(f"FCM topic notification sent successfully to {topic}: {response}")
            return True

        except Exception as e:
            logger.error(f"Error sending FCM topic notification: {str(e)}")
            return False

    async def subscribe_to_topic(self, tokens: List[str], topic: str) -> Dict[str, Any]:
        """토픽 구독"""
        try:
            response = messaging.subscribe_to_topic(tokens, topic)
            
            success_count = response.success_count
            failure_count = response.failure_count
            
            logger.info(
                f"Topic subscription: {success_count} success, {failure_count} failure for topic {topic}"
            )
            
            return {
                "success": True,
                "success_count": success_count,
                "failure_count": failure_count,
                "errors": response.errors if hasattr(response, 'errors') else []
            }
            
        except Exception as e:
            logger.error(f"Error subscribing to FCM topic: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def unsubscribe_from_topic(self, tokens: List[str], topic: str) -> Dict[str, Any]:
        """토픽 구독 해제"""
        try:
            response = messaging.unsubscribe_from_topic(tokens, topic)
            
            success_count = response.success_count
            failure_count = response.failure_count
            
            logger.info(
                f"Topic unsubscription: {success_count} success, {failure_count} failure for topic {topic}"
            )
            
            return {
                "success": True,
                "success_count": success_count,
                "failure_count": failure_count,
                "errors": response.errors if hasattr(response, 'errors') else []
            }
            
        except Exception as e:
            logger.error(f"Error unsubscribing from FCM topic: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    # 기존 헬퍼 메서드들은 그대로 유지
    def create_weather_notification(
        self,
        location: str,
        weather_condition: str,
        temperature: int,
        alert_type: str = "weather_change",
    ) -> Dict[str, Any]:
        """날씨 알림 템플릿"""
        title = f"🌤️ {location} 날씨 알림"

        if alert_type == "weather_change":
            body = f"현재 {weather_condition}, 기온 {temperature}°C"
        elif alert_type == "rain_alert":
            body = f"비 예보가 있습니다. 우산을 준비하세요!"
        elif alert_type == "extreme_weather":
            body = f"⚠️ 악천후 경보: {weather_condition}"
        else:
            body = f"날씨 정보: {weather_condition}, {temperature}°C"

        return {
            "title": title,
            "body": body,
            "data": {
                "type": "weather_alert",
                "location": location,
                "condition": weather_condition,
                "temperature": str(temperature),
                "alert_type": alert_type,
            },
            "icon": "weather_icon",
            "sound": "default",
        }

    def create_travel_notification(
        self, plan_title: str, message: str, notification_type: str = "travel_update"
    ) -> Dict[str, Any]:
        """여행 계획 알림 템플릿"""
        title = f"✈️ {plan_title}"

        return {
            "title": title,
            "body": message,
            "data": {
                "type": "travel_plan",
                "plan_title": plan_title,
                "notification_type": notification_type,
            },
            "icon": "travel_icon",
            "sound": "default",
        }

    def create_marketing_notification(
        self, title: str, message: str, campaign_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """마케팅 알림 템플릿"""
        return {
            "title": title,
            "body": message,
            "data": {
                "type": "marketing",
                "campaign_id": campaign_id or "",
                "timestamp": datetime.now().isoformat(),
            },
            "icon": "marketing_icon",
            "sound": "default",
        }

    @staticmethod
    def upsert_device_token(
        db,
        user_id,  # UUID 타입
        fcm_token: str,
        device_type: Optional[str] = None,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
        user_agent: Optional[str] = None,
        app_version: Optional[str] = None,
        os_version: Optional[str] = None,
    ) -> Optional[Any]:
        """
        FCM 디바이스 토큰 업서트 (삽입 또는 업데이트)
        로그인 시 FCM 토큰을 자동으로 등록/업데이트하는 헬퍼 함수
        """
        try:
            from ..models import UserDeviceToken

            # 기존 토큰 확인 (같은 사용자의 같은 디바이스 ID 또는 FCM 토큰)
            existing_token = None

            # 디바이스 ID가 있는 경우 우선 확인
            if device_id:
                existing_token = (
                    db.query(UserDeviceToken)
                    .filter(
                        UserDeviceToken.user_id == user_id,
                        UserDeviceToken.device_id == device_id,
                    )
                    .first()
                )

            # 디바이스 ID로 찾지 못한 경우 FCM 토큰으로 확인
            if not existing_token:
                existing_token = (
                    db.query(UserDeviceToken)
                    .filter(UserDeviceToken.device_token == fcm_token)
                    .first()
                )

            if existing_token:
                # 기존 토큰 업데이트
                existing_token.user_id = user_id
                existing_token.device_token = fcm_token
                existing_token.is_active = True
                existing_token.updated_at = datetime.now()

                # 제공된 값들만 업데이트
                if device_type:
                    existing_token.device_type = device_type
                if device_id:
                    existing_token.device_id = device_id
                if device_name:
                    existing_token.device_name = device_name
                if user_agent:
                    existing_token.user_agent = user_agent
                if app_version:
                    existing_token.app_version = app_version
                if os_version:
                    existing_token.os_version = os_version

                db.commit()
                db.refresh(existing_token)
                logger.info(f"Updated FCM token for user {user_id}")
                return existing_token

            else:
                # 새 토큰 생성
                new_token = UserDeviceToken(
                    user_id=user_id,
                    device_token=fcm_token,
                    device_type=device_type,
                    device_id=device_id,
                    device_name=device_name,
                    user_agent=user_agent,
                    app_version=app_version,
                    os_version=os_version,
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                db.add(new_token)
                db.commit()
                db.refresh(new_token)
                logger.info(f"Created new FCM token for user {user_id}")
                return new_token

        except Exception as e:
            logger.error(f"Error upserting FCM token: {str(e)}")
            db.rollback()
            return None