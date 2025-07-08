from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List, Dict, Any, Optional
import logging
import re

from app.models import ChatMessage

logger = logging.getLogger(__name__)

class ChatbotService:
    """챗봇 비즈니스 로직 서비스"""

    def __init__(self, db: Session):
        self.db = db

    async def generate_response(
        self,
        user_id: int,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        사용자 메시지에 대한 챗봇 응답을 생성합니다.

        Args:
            user_id: 사용자 ID
            message: 사용자 메시지
            context: 대화 컨텍스트

        Returns:
            Dict[str, Any]: 챗봇 응답과 추천 질문
        """
        try:
            # 메시지 전처리
            processed_message = self._preprocess_message(message)

            # 의도 분석
            intent = self._analyze_intent(processed_message)

            # 응답 생성
            response = await self._generate_response_by_intent(intent, processed_message, context)

            # 추천 질문 생성
            suggestions = self._generate_suggestions(intent, context)

            logger.info(f"챗봇 응답 생성 완료 - 사용자: {user_id}, 의도: {intent}")

            return {
                "response": response,
                "suggestions": suggestions,
                "intent": intent
            }

        except Exception as e:
            logger.error(f"챗봇 응답 생성 실패: {e}, 사용자: {user_id}")
            return {
                "response": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                "suggestions": ["날씨 정보를 알려주세요", "여행지를 추천해주세요"],
                "intent": "error"
            }

    def _preprocess_message(self, message: str) -> str:
        """메시지 전처리"""
        # 공백 정리
        message = re.sub(r'\s+', ' ', message.strip())
        # 특수문자 처리
        message = re.sub(r'[^\w\s가-힣]', '', message)
        return message.lower()

    def _analyze_intent(self, message: str) -> str:
        """메시지 의도 분석"""
        # 날씨 관련 키워드
        weather_keywords = ['날씨', '기온', '온도', '비', '눈', '맑음', '흐림', '습도', '바람']
        if any(keyword in message for keyword in weather_keywords):
            return "weather"

        # 여행 관련 키워드
        travel_keywords = ['여행', '추천', '관광', '명소', '여행지', '가볼곳', '추천해']
        if any(keyword in message for keyword in travel_keywords):
            return "travel"

        # 인사 관련 키워드
        greeting_keywords = ['안녕', '하이', '반가워', '처음', '시작']
        if any(keyword in message for keyword in greeting_keywords):
            return "greeting"

        # 도움말 관련 키워드
        help_keywords = ['도움', '도와', '어떻게', '무엇', '뭐']
        if any(keyword in message for keyword in help_keywords):
            return "help"

        return "general"

    async def _generate_response_by_intent(
        self,
        intent: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """의도에 따른 응답 생성"""

        if intent == "weather":
            return (
                "현재 날씨 정보를 확인해드릴게요! "
                "어느 지역의 날씨를 알고 싶으신가요? "
                "도시명이나 지역명을 알려주시면 상세한 날씨 정보를 제공해드립니다."
            )

        elif intent == "travel":
            return (
                "여행지 추천을 도와드릴게요! "
                "어떤 종류의 여행을 계획하고 계신가요? "
                "자연 관광, 문화 체험, 맛집 탐방 등 선호하시는 여행 스타일을 알려주세요."
            )

        elif intent == "greeting":
            return (
                "안녕하세요! Weather Flick 챗봇입니다. "
                "날씨 정보와 여행 추천을 도와드릴 수 있어요. "
                "무엇을 도와드릴까요?"
            )

        elif intent == "help":
            return (
                "Weather Flick에서 다음과 같은 서비스를 이용하실 수 있습니다:\n"
                "• 실시간 날씨 정보 조회\n"
                "• 여행지 추천 및 계획\n"
                "• 지역별 관광 정보\n"
                "• 여행 일정 관리\n\n"
                "어떤 서비스에 대해 궁금하신가요?"
            )

        else:
            return (
                "죄송합니다. 질문을 정확히 이해하지 못했어요. "
                "날씨 정보나 여행 추천에 대해 물어보시거나, "
                "'도움말'이라고 말씀해주시면 더 자세히 안내해드릴게요."
            )

    def _generate_suggestions(self, intent: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """의도에 따른 추천 질문 생성"""

        if intent == "weather":
            return [
                "서울 날씨는 어때요?",
                "부산 날씨 알려주세요",
                "주말 날씨는 어떨까요?"
            ]

        elif intent == "travel":
            return [
                "자연 관광지 추천해주세요",
                "문화재 관람 추천",
                "맛집이 많은 여행지는?"
            ]

        elif intent == "greeting":
            return [
                "오늘 날씨 어때요?",
                "여행지 추천해주세요",
                "도움말을 보여주세요"
            ]

        else:
            return [
                "날씨 정보를 알려주세요",
                "여행지를 추천해주세요",
                "도움말을 보여주세요"
            ]

    async def get_chat_history(self, user_id: int, limit: int = 50) -> List[ChatMessage]:
        """
        사용자의 챗봇 대화 히스토리를 조회합니다.

        Args:
            user_id: 사용자 ID
            limit: 조회할 메시지 개수

        Returns:
            List[ChatMessage]: 대화 히스토리
        """
        try:
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.user_id == user_id)
                .order_by(desc(ChatMessage.created_at))
                .limit(limit)
            )

            result = self.db.execute(stmt)
            messages = list(result.scalars().all())

            # 시간순 정렬 (최신순)
            messages.reverse()

            return messages

        except Exception as e:
            logger.error(f"챗봇 히스토리 조회 실패: {e}, 사용자: {user_id}")
            return []

    async def get_initial_message(self) -> Dict[str, Any]:
        """챗봇 초기 메시지를 반환합니다."""
        return {
            "message": (
                "안녕하세요! Weather Flick 챗봇입니다. "
                "날씨 정보와 여행 추천을 도와드릴 수 있어요. "
                "무엇을 도와드릴까요?"
            ),
            "suggestions": [
                "오늘 날씨 어때요?",
                "여행지 추천해주세요",
                "도움말을 보여주세요"
            ]
        }

    async def get_config(self) -> Dict[str, Any]:
        """챗봇 설정을 반환합니다."""
        return {
            "welcome_delay": 1000,  # 1초
            "typing_delay": 500,    # 0.5초
            "max_context_length": 10,
            "max_suggestions": 3
        }
