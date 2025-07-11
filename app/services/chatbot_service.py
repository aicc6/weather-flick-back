from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List, Dict, Any, Optional
import logging
import re

from app.models import ChatMessage
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)

class ChatbotService:
    """챗봇 비즈니스 로직 서비스 - OpenAI 통합"""

    def __init__(self, db: Session):
        self.db = db

    async def generate_response(
        self,
        user_id: Optional[int],
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        사용자 메시지에 대한 챗봇 응답을 생성합니다.
        OpenAI를 우선 사용하고, 실패 시 규칙 기반 응답으로 fallback

        Args:
            user_id: 사용자 ID (익명 사용자의 경우 None)
            message: 사용자 메시지
            context: 대화 컨텍스트

        Returns:
            Dict[str, Any]: 챗봇 응답과 추천 질문
        """
        try:
            # 먼저 OpenAI로 응답 시도
            if openai_service.client:
                # 대화 기록 가져오기 (인증된 사용자만)
                conversation_history = []
                if user_id:
                    conversation_history = await self._get_conversation_history(user_id)

                # OpenAI 응답 생성
                ai_response = await openai_service.generate_chatbot_response(
                    user_message=message,
                    conversation_history=conversation_history
                )

                # 응답이 성공적으로 생성되었다면 사용
                if ai_response and "오류" not in ai_response:
                    # 거절 메시지인지 확인
                    rejection_keywords = [
                        "죄송합니다. 저는 여행과 날씨에 관한 도움만",
                        "여행 계획이나 날씨 기반 추천이 필요하시면"
                    ]
                    
                    is_rejection = any(keyword in ai_response for keyword in rejection_keywords)
                    
                    if is_rejection:
                        # 거절 메시지인 경우, 여행 관련 추천 질문만 제공
                        suggestions = [
                            "오늘 날씨 어때요?",
                            "여행지 추천해주세요",
                            "날씨 좋은 관광지 알려주세요"
                        ]
                        intent = "rejection"
                    else:
                        # 정상 응답인 경우
                        intent = self._analyze_intent(message)
                        suggestions = self._generate_smart_suggestions(intent, message, context)

                    user_info = f"사용자: {user_id}" if user_id else "익명 사용자"
                    logger.info(f"OpenAI 챗봇 응답 생성 완료 - {user_info}")

                    return {
                        "response": ai_response,
                        "suggestions": suggestions,
                        "intent": intent,
                        "source": "openai"
                    }

            # OpenAI 실패 시 또는 설정되지 않은 경우 규칙 기반 응답
            return await self._generate_rule_based_response(user_id, message, context)

        except Exception as e:
            user_info = f"사용자: {user_id}" if user_id else "익명 사용자"
            logger.error(f"챗봇 응답 생성 실패: {e}, {user_info}")
            return await self._generate_fallback_response()

    async def _get_conversation_history(self, user_id: int, limit: int = 5) -> List[Dict[str, str]]:
        """최근 대화 기록을 OpenAI 형식으로 변환"""
        try:
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.user_id == user_id)
                .order_by(desc(ChatMessage.created_at))
                .limit(limit * 2)  # user와 bot 메시지 쌍
            )

            result = self.db.execute(stmt)
            messages = list(result.scalars().all())
            messages.reverse()  # 시간순 정렬

            # OpenAI 형식으로 변환
            conversation = []
            for msg in messages:
                role = "user" if msg.sender == "user" else "assistant"
                conversation.append({
                    "role": role,
                    "content": msg.message
                })

            return conversation[-10:]  # 최근 10개 메시지만

        except Exception as e:
            logger.warning(f"대화 기록 조회 실패: {e}")
            return []

    async def _generate_rule_based_response(
        self,
        user_id: Optional[int],
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """규칙 기반 응답 생성 (기존 로직)"""
        try:
            # 메시지 전처리
            processed_message = self._preprocess_message(message)

            # 의도 분석
            intent = self._analyze_intent(processed_message)

            # 응답 생성
            response = await self._generate_response_by_intent(intent, processed_message, context)

            # 추천 질문 생성
            suggestions = self._generate_suggestions(intent, context)

            user_info = f"사용자: {user_id}" if user_id else "익명 사용자"
            logger.info(f"규칙 기반 챗봇 응답 생성 완료 - {user_info}, 의도: {intent}")

            return {
                "response": response,
                "suggestions": suggestions,
                "intent": intent,
                "source": "rule_based"
            }

        except Exception as e:
            logger.error(f"규칙 기반 응답 생성 실패: {e}")
            return await self._generate_fallback_response()

    async def _generate_fallback_response(self) -> Dict[str, Any]:
        """최종 fallback 응답"""
        return {
            "response": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "suggestions": ["날씨 정보를 알려주세요", "여행지를 추천해주세요", "도움말을 보여주세요"],
            "intent": "error",
            "source": "fallback"
        }

    def _generate_smart_suggestions(
        self,
        intent: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """컨텍스트를 고려한 스마트 추천 질문 생성"""

        # 기본 추천에서 시작
        base_suggestions = self._generate_suggestions(intent, context)

        # 메시지 내용에 따른 동적 추천 추가
        smart_suggestions = []

        if "날씨" in message:
            if "서울" in message:
                smart_suggestions.extend(["부산 날씨는 어때요?", "제주도 날씨 알려주세요"])
            else:
                smart_suggestions.extend(["서울 날씨는 어때요?", "내일 날씨는 어떨까요?"])

        elif "여행" in message or "추천" in message:
            if "자연" in message:
                smart_suggestions.extend(["산 여행지 추천해주세요", "바다 근처 여행지는?"])
            elif "문화" in message:
                smart_suggestions.extend(["역사 문화재 추천", "박물관이 있는 여행지는?"])
            else:
                smart_suggestions.extend(["자연 관광지 추천", "문화 체험 여행지는?"])

        # 중복 제거하고 최대 3개까지
        all_suggestions = list(set(base_suggestions + smart_suggestions))
        return all_suggestions[:3]

    def _preprocess_message(self, message: str) -> str:
        """메시지 전처리"""
        # 공백 정리
        message = re.sub(r'\s+', ' ', message.strip())
        # 특수문자 처리
        message = re.sub(r'[^\w\s가-힣]', '', message)
        return message.lower()

    def _analyze_intent(self, message: str) -> str:
        """메시지 의도 분석 (개선된 버전)"""
        # 날씨 관련 키워드 (확장)
        weather_keywords = ['날씨', '기온', '온도', '비', '눈', '맑음', '흐림', '습도', '바람',
                          '기상', '예보', '강수', '태풍', '미세먼지']
        if any(keyword in message for keyword in weather_keywords):
            return "weather"

        # 여행 관련 키워드 (확장)
        travel_keywords = ['여행', '추천', '관광', '명소', '여행지', '가볼곳', '추천해',
                          '여행코스', '일정', '계획', '투어', '관광지']
        if any(keyword in message for keyword in travel_keywords):
            return "travel"

        # 숙박 관련
        accommodation_keywords = ['숙박', '호텔', '펜션', '리조트', '게스트하우스', '민박']
        if any(keyword in message for keyword in accommodation_keywords):
            return "accommodation"

        # 교통 관련
        transport_keywords = ['교통', '버스', '지하철', '기차', '항공', '렌터카', '택시']
        if any(keyword in message for keyword in transport_keywords):
            return "transport"

        # 음식 관련
        food_keywords = ['맛집', '음식', '요리', '식당', '카페', '먹거리', '특산물']
        if any(keyword in message for keyword in food_keywords):
            return "food"

        # 인사 관련 키워드
        greeting_keywords = ['안녕', '하이', '반가워', '처음', '시작', '헬로']
        if any(keyword in message for keyword in greeting_keywords):
            return "greeting"

        # 도움말 관련 키워드
        help_keywords = ['도움', '도와', '어떻게', '무엇', '뭐', '사용법', '기능']
        if any(keyword in message for keyword in help_keywords):
            return "help"

        return "general"

    async def _generate_response_by_intent(
        self,
        intent: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """의도에 따른 응답 생성 (개선된 버전)"""

        if intent == "weather":
            return (
                "🌤️ 현재 날씨 정보를 확인해드릴게요! "
                "어느 지역의 날씨를 알고 싶으신가요? "
                "도시명이나 지역명을 알려주시면 상세한 날씨 정보와 여행 적합도를 제공해드립니다."
            )

        elif intent == "travel":
            return (
                "✈️ 멋진 여행지 추천을 도와드릴게요! "
                "어떤 종류의 여행을 계획하고 계신가요? "
                "자연 관광, 문화 체험, 맛집 탐방, 액티비티 등 선호하시는 여행 스타일을 알려주세요. "
                "날씨까지 고려한 완벽한 추천을 해드립니다!"
            )

        elif intent == "accommodation":
            return (
                "🏨 숙박시설 정보를 도와드릴게요! "
                "어느 지역의 숙박을 찾고 계신가요? "
                "호텔, 펜션, 리조트 등 원하시는 숙박 타입과 예산대를 알려주시면 "
                "날씨와 주변 관광지를 고려한 추천을 해드립니다."
            )

        elif intent == "transport":
            return (
                "🚗 교통편 정보를 안내해드릴게요! "
                "어디에서 어디로 이동하시나요? "
                "대중교통, 렌터카, 항공편 등 다양한 교통수단 정보와 "
                "날씨를 고려한 최적의 이동 방법을 추천해드립니다."
            )

        elif intent == "food":
            return (
                "🍽️ 맛있는 맛집 정보를 찾아드릴게요! "
                "어느 지역의 맛집을 찾고 계신가요? "
                "한식, 양식, 카페 등 원하시는 음식 종류를 알려주시면 "
                "현지 날씨까지 고려한 맛집을 추천해드립니다."
            )

        elif intent == "greeting":
            return (
                "안녕하세요! 🌟 Weather Flick 여행 도우미입니다! "
                "날씨 정보와 여행 추천을 전문으로 도와드려요. "
                "다음과 같은 서비스를 이용하실 수 있습니다:\n"
                "• 실시간 날씨 정보 & 여행 적합도\n"
                "• 개인화된 여행지 추천\n"
                "• 숙박 & 교통 정보\n"
                "• 맛집 & 관광 코스 안내\n\n"
                "무엇을 도와드릴까요? 😊"
            )

        elif intent == "help":
            return (
                "🆘 Weather Flick 사용법을 안내해드릴게요!\n\n"
                "📱 **주요 기능:**\n"
                "• 실시간 날씨 정보 조회\n"
                "• 날씨 기반 여행지 추천\n"
                "• 여행 일정 계획 도움\n"
                "• 지역별 관광 정보\n"
                "• 숙박 & 교통 안내\n"
                "• 맛집 & 특산물 추천\n\n"
                "💬 **사용 팁:**\n"
                "구체적으로 질문하시면 더 정확한 답변을 드릴 수 있어요!\n"
                "예: '제주도 내일 날씨와 추천 관광지 알려주세요'"
            )

        else:
            return (
                "🤔 질문을 정확히 이해하지 못했어요. "
                "다음과 같이 질문해보세요:\n"
                "• '서울 날씨 어때요?'\n"
                "• '부산 여행지 추천해주세요'\n"
                "• '제주도 맛집 알려주세요'\n"
                "• '도움말'이라고 말씀해주시면 더 자세히 안내해드릴게요! 😊"
            )

    def _generate_suggestions(self, intent: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """의도에 따른 추천 질문 생성 (개선된 버전)"""

        if intent == "weather":
            return [
                "서울 날씨는 어때요?",
                "부산 주말 날씨 알려주세요",
                "제주도 여행하기 좋은 날씨인가요?"
            ]

        elif intent == "travel":
            return [
                "자연 관광지 추천해주세요",
                "문화재 관람 코스 알려주세요",
                "가족 여행지 추천해주세요"
            ]

        elif intent == "accommodation":
            return [
                "제주도 펜션 추천해주세요",
                "서울 호텔 정보 알려주세요",
                "강릉 리조트 어때요?"
            ]

        elif intent == "food":
            return [
                "부산 해산물 맛집 추천",
                "제주도 특산물 알려주세요",
                "전주 한정식 맛집은?"
            ]

        elif intent == "greeting":
            return [
                "오늘 날씨 어때요?",
                "여행지 추천해주세요",
                "맛집 정보 알려주세요"
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
