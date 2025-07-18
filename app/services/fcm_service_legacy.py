"""
FCM (Firebase Cloud Messaging) 서비스
푸시 알림 전송을 담당하는 서비스 클래스
"""

import json
import logging
from typing import Dict, Any, Optional
import asyncio
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


class FCMService:
    """FCM 푸시 알림 서비스"""

    def __init__(self):
        self.server_key = self._get_server_key()
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"

    def _get_server_key(self) -> str:
        """FCM 서버 키 조회"""
        # 환경 변수 또는 설정 파일에서 FCM 서버 키를 가져옴
        import os

        return os.getenv("FCM_SERVER_KEY", "")

    async def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        click_action: Optional[str] = None,
        icon: Optional[str] = None,
        sound: str = "default",
        badge: Optional[int] = None,
        priority: str = "high",
    ) -> bool:
        """단일 디바이스에 푸시 알림 전송"""

        if not self.server_key:
            logger.error("FCM server key not configured")
            return False
        
        logger.info(f"FCM URL: {self.fcm_url}")
        logger.info(f"FCM server key length: {len(self.server_key)}")

        payload = {
            "to": token,
            "notification": {
                "title": title,
                "body": body,
                "sound": sound,
                "priority": priority,
            },
            "data": data or {},
        }

        # 선택적 속성 추가
        if click_action:
            payload["notification"]["click_action"] = click_action
        if icon:
            payload["notification"]["icon"] = icon
        if badge:
            payload["notification"]["badge"] = badge

        headers = {
            "Authorization": f"key={self.server_key}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.fcm_url, json=payload, headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        if result.get("success", 0) > 0:
                            logger.info(
                                f"FCM notification sent successfully to {token[:20]}..."
                            )
                            return True
                        else:
                            error = result.get("results", [{}])[0].get(
                                "error", "Unknown error"
                            )
                            logger.error(f"FCM notification failed: {error}")
                            return False
                    else:
                        error_text = await response.text()
                        logger.error(f"FCM API error: {response.status}, Response: {error_text}")
                        return False

        except Exception as e:
            logger.error(f"Error sending FCM notification: {str(e)}")
            return False

    async def send_multicast_notification(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        click_action: Optional[str] = None,
        icon: Optional[str] = None,
        sound: str = "default",
        badge: Optional[int] = None,
        priority: str = "high",
    ) -> Dict[str, Any]:
        """다중 디바이스에 푸시 알림 전송"""

        if not self.server_key:
            logger.error("FCM server key not configured")
            return {"success": 0, "failure": len(tokens), "results": []}

        if not tokens:
            return {"success": 0, "failure": 0, "results": []}

        payload = {
            "registration_ids": tokens,
            "notification": {
                "title": title,
                "body": body,
                "sound": sound,
                "priority": priority,
            },
            "data": data or {},
        }

        # 선택적 속성 추가
        if click_action:
            payload["notification"]["click_action"] = click_action
        if icon:
            payload["notification"]["icon"] = icon
        if badge:
            payload["notification"]["badge"] = badge

        headers = {
            "Authorization": f"key={self.server_key}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.fcm_url, json=payload, headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        success_count = result.get("success", 0)
                        failure_count = result.get("failure", 0)

                        logger.info(
                            f"FCM multicast sent: {success_count} success, {failure_count} failure"
                        )

                        return {
                            "success": success_count,
                            "failure": failure_count,
                            "results": result.get("results", []),
                        }
                    else:
                        logger.error(f"FCM API error: {response.status}")
                        return {"success": 0, "failure": len(tokens), "results": []}

        except Exception as e:
            logger.error(f"Error sending FCM multicast notification: {str(e)}")
            return {"success": 0, "failure": len(tokens), "results": []}

    async def send_topic_notification(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        click_action: Optional[str] = None,
        icon: Optional[str] = None,
        sound: str = "default",
        badge: Optional[int] = None,
        priority: str = "high",
    ) -> bool:
        """토픽 구독자들에게 푸시 알림 전송"""

        if not self.server_key:
            logger.error("FCM server key not configured")
            return False

        payload = {
            "to": f"/topics/{topic}",
            "notification": {
                "title": title,
                "body": body,
                "sound": sound,
                "priority": priority,
            },
            "data": data or {},
        }

        # 선택적 속성 추가
        if click_action:
            payload["notification"]["click_action"] = click_action
        if icon:
            payload["notification"]["icon"] = icon
        if badge:
            payload["notification"]["badge"] = badge

        headers = {
            "Authorization": f"key={self.server_key}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.fcm_url, json=payload, headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        if result.get("message_id"):
                            logger.info(
                                f"FCM topic notification sent successfully to {topic}"
                            )
                            return True
                        else:
                            logger.error(f"FCM topic notification failed: {result}")
                            return False
                    else:
                        error_text = await response.text()
                        logger.error(f"FCM API error: {response.status}, Response: {error_text}")
                        return False

        except Exception as e:
            logger.error(f"Error sending FCM topic notification: {str(e)}")
            return False

    async def subscribe_to_topic(self, tokens: list[str], topic: str) -> Dict[str, Any]:
        """토픽 구독"""
        if not self.server_key:
            logger.error("FCM server key not configured")
            return {"success": False, "error": "Server key not configured"}

        url = f"https://iid.googleapis.com/iid/v1:batchAdd"

        payload = {"to": f"/topics/{topic}", "registration_tokens": tokens}

        headers = {
            "Authorization": f"key={self.server_key}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(
                            f"Successfully subscribed {len(tokens)} tokens to topic {topic}"
                        )
                        return {"success": True, "result": result}
                    else:
                        logger.error(f"FCM topic subscription error: {response.status}")
                        return {"success": False, "error": f"HTTP {response.status}"}

        except Exception as e:
            logger.error(f"Error subscribing to FCM topic: {str(e)}")
            return {"success": False, "error": str(e)}

    async def unsubscribe_from_topic(
        self, tokens: list[str], topic: str
    ) -> Dict[str, Any]:
        """토픽 구독 해제"""
        if not self.server_key:
            logger.error("FCM server key not configured")
            return {"success": False, "error": "Server key not configured"}

        url = f"https://iid.googleapis.com/iid/v1:batchRemove"

        payload = {"to": f"/topics/{topic}", "registration_tokens": tokens}

        headers = {
            "Authorization": f"key={self.server_key}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(
                            f"Successfully unsubscribed {len(tokens)} tokens from topic {topic}"
                        )
                        return {"success": True, "result": result}
                    else:
                        logger.error(
                            f"FCM topic unsubscription error: {response.status}"
                        )
                        return {"success": False, "error": f"HTTP {response.status}"}

        except Exception as e:
            logger.error(f"Error unsubscribing from FCM topic: {str(e)}")
            return {"success": False, "error": str(e)}

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
