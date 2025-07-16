import logging
from typing import Any
from datetime import datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    ChatMessage, User, TravelPlan,
    UserActivityLog
)
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)

class EnhancedChatbotService:
    """개인화된 챗봇 서비스 - 사용자 맞춤 응답"""

    def __init__(self, db: Session):
        self.db = db

    async def generate_response(
        self,
        user_id: Any | None,
        message: str,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        사용자 맞춤형 챗봇 응답을 생성합니다.
        
        개인화 요소:
        - 사용자 선호 지역/테마
        - 과거 여행 계획
        - 최근 검색 기록
        - 대화 기록
        """
        try:
            # 사용자 정보 로드 (로그인한 경우)
            user_profile = None
            if user_id:
                user_profile = await self._get_user_profile(user_id)
            
            # OpenAI 응답 시도
            if openai_service.client:
                # 대화 기록 가져오기
                conversation_history = []
                if user_id:
                    conversation_history = await self._get_conversation_history(user_id)
                
                # 개인화된 시스템 프롬프트 생성
                system_prompt = self._generate_personalized_prompt(user_profile)
                
                # OpenAI 응답 생성
                ai_response = await openai_service.generate_personalized_response(
                    user_message=message,
                    conversation_history=conversation_history,
                    system_prompt=system_prompt,
                    user_context=user_profile
                )
                
                if ai_response and "오류" not in ai_response:
                    # 개인화된 추천 질문 생성
                    suggestions = await self._generate_personalized_suggestions(
                        user_id, message, user_profile
                    )
                    
                    return {
                        "response": ai_response,
                        "suggestions": suggestions,
                        "intent": self._analyze_intent(message),
                        "source": "openai_personalized",
                        "personalized": True
                    }
            
            # Fallback: 규칙 기반 개인화 응답
            return await self._generate_personalized_rule_based_response(
                user_id, message, context, user_profile
            )
            
        except Exception as e:
            logger.error(f"챗봇 응답 생성 실패: {e}")
            return await self._generate_fallback_response()

    async def _get_user_profile(self, user_id: Any) -> dict[str, Any]:
        """사용자 프로필 및 활동 정보 조회"""
        try:
            # 사용자 기본 정보
            user = self.db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return {}
            
            # 최근 여행 계획
            recent_plans = self.db.query(TravelPlan).filter(
                TravelPlan.user_id == user_id
            ).order_by(desc(TravelPlan.created_at)).limit(3).all()
            
            # 최근 활동 로그 (검색, 조회 등)
            recent_activities = self.db.query(UserActivityLog).filter(
                UserActivityLog.user_id == user_id
            ).order_by(desc(UserActivityLog.created_at)).limit(10).all()
            
            # 선호하는 여행 코스 (좋아요 기준)
            # TODO: 좋아요 테이블과 조인하여 선호 코스 가져오기
            
            return {
                "nickname": user.nickname,
                "preferred_region": user.preferred_region,
                "preferred_theme": user.preferred_theme,
                "preferences": user.preferences or {},
                "recent_plans": [
                    {
                        "title": plan.title,
                        "destination": plan.title,  # title을 destination으로 사용
                        "start_date": plan.start_date.isoformat() if plan.start_date else None
                    }
                    for plan in recent_plans
                ],
                "recent_searches": self._extract_search_activities(recent_activities),
                "member_since": user.created_at.isoformat(),
                "is_active_user": user.login_count > 5  # 활발한 사용자 판단
            }
            
        except Exception as e:
            logger.error(f"사용자 프로필 조회 실패: {e}")
            return {}

    def _extract_search_activities(self, activities: list[UserActivityLog]) -> list[str]:
        """활동 로그에서 검색 키워드 추출"""
        searches = []
        for activity in activities:
            if activity.activity_type in ["SEARCH", "VIEW_DESTINATION"]:
                if activity.activity_data and "keyword" in activity.activity_data:
                    searches.append(activity.activity_data["keyword"])
        return searches[:5]  # 최근 5개만

    def _generate_personalized_prompt(self, user_profile: dict[str, Any] | None) -> str:
        """개인화된 시스템 프롬프트 생성"""
        base_prompt = """당신은 Weather Flick의 AI 여행 도우미입니다. 
        날씨 정보와 여행 추천을 전문으로 하며, 친근하고 도움이 되는 답변을 제공합니다."""
        
        if not user_profile:
            return base_prompt
        
        personalized_parts = []
        
        # 사용자 이름으로 인사
        if user_profile.get("nickname"):
            personalized_parts.append(
                f"사용자의 닉네임은 '{user_profile['nickname']}'입니다. "
                f"적절한 경우 이름을 부르며 친근하게 대화하세요."
            )
        
        # 선호 지역/테마 반영
        if user_profile.get("preferred_region"):
            personalized_parts.append(
                f"사용자는 '{user_profile['preferred_region']}' 지역을 선호합니다."
            )
        
        if user_profile.get("preferred_theme"):
            personalized_parts.append(
                f"사용자는 '{user_profile['preferred_theme']}' 테마의 여행을 좋아합니다."
            )
        
        # 최근 여행 계획 참고
        if user_profile.get("recent_plans"):
            recent_destinations = [p["destination"] for p in user_profile["recent_plans"][:2]]
            personalized_parts.append(
                f"최근에 {', '.join(recent_destinations)} 여행을 계획했습니다."
            )
        
        # 활발한 사용자 구분
        if user_profile.get("is_active_user"):
            personalized_parts.append(
                "자주 이용하는 사용자이므로 더 상세하고 전문적인 정보를 제공하세요."
            )
        
        if personalized_parts:
            return base_prompt + "\n\n사용자 정보:\n" + "\n".join(personalized_parts)
        
        return base_prompt

    async def _generate_personalized_suggestions(
        self,
        user_id: Any,
        message: str,
        user_profile: dict[str, Any] | None
    ) -> list[str]:
        """개인화된 추천 질문 생성"""
        suggestions = []
        
        # 기본 의도 분석
        intent = self._analyze_intent(message)
        
        if user_profile:
            # 선호 지역 기반 추천
            if user_profile.get("preferred_region"):
                region = user_profile["preferred_region"]
                suggestions.append(f"{region} 날씨는 어때요?")
                suggestions.append(f"{region}의 숨은 명소 알려주세요")
            
            # 선호 테마 기반 추천
            if user_profile.get("preferred_theme"):
                theme = user_profile["preferred_theme"]
                if theme == "자연":
                    suggestions.extend([
                        "산악 트레킹 코스 추천해주세요",
                        "바다가 보이는 캠핑장은?"
                    ])
                elif theme == "문화":
                    suggestions.extend([
                        "박물관 투어 일정 짜주세요",
                        "전통 문화 체험 프로그램은?"
                    ])
                elif theme == "음식":
                    suggestions.extend([
                        "미슐랭 맛집 추천해주세요",
                        "현지인이 가는 숨은 맛집은?"
                    ])
            
            # 최근 여행 계획 기반
            if user_profile.get("recent_plans"):
                last_plan = user_profile["recent_plans"][0]
                if last_plan.get("start_date"):
                    # 여행 날짜가 다가오면
                    start_date = datetime.fromisoformat(last_plan["start_date"])
                    if start_date - datetime.now() < timedelta(days=7):
                        suggestions.append(f"{last_plan['destination']} 여행 준비 팁")
                        suggestions.append(f"{last_plan['destination']} 일주일 날씨 예보")
        
        # 현재 메시지 기반 추천
        if "날씨" in message:
            suggestions.append("여행하기 좋은 날씨인가요?")
        elif "추천" in message:
            suggestions.append("더 자세한 조건을 알려주세요")
        
        # 중복 제거 및 상위 3개 선택
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:3]

    async def _generate_personalized_rule_based_response(
        self,
        user_id: Any | None,
        message: str,
        context: dict[str, Any] | None,
        user_profile: dict[str, Any] | None
    ) -> dict[str, Any]:
        """규칙 기반 개인화 응답"""
        intent = self._analyze_intent(message)
        
        # 기본 응답 생성
        base_response = await self._generate_response_by_intent(intent, message, context)
        
        # 개인화 요소 추가
        if user_profile and user_profile.get("nickname"):
            # 이름 추가
            personalized_response = f"{user_profile['nickname']}님, " + base_response
            
            # 선호도 기반 추가 정보
            if intent == "travel" and user_profile.get("preferred_theme"):
                theme = user_profile["preferred_theme"]
                personalized_response += f"\n\n특히 {theme} 테마를 좋아하시는 것으로 알고 있어요! "
                personalized_response += f"{theme} 관련 추천을 원하시면 말씀해주세요."
            
            elif intent == "weather" and user_profile.get("preferred_region"):
                region = user_profile["preferred_region"]
                personalized_response += f"\n\n평소 {region} 지역을 선호하시는데, "
                personalized_response += f"{region}의 날씨 정보도 함께 확인해드릴까요?"
        else:
            personalized_response = base_response
        
        suggestions = await self._generate_personalized_suggestions(
            user_id, message, user_profile
        )
        
        return {
            "response": personalized_response,
            "suggestions": suggestions,
            "intent": intent,
            "source": "rule_based_personalized",
            "personalized": bool(user_profile)
        }

    # 기존 메서드들 (변경 없음)
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
        
        # 숙박 관련
        accommodation_keywords = ['숙박', '호텔', '펜션', '리조트', '게스트하우스']
        if any(keyword in message for keyword in accommodation_keywords):
            return "accommodation"
        
        # 음식 관련
        food_keywords = ['맛집', '음식', '요리', '식당', '카페', '먹거리']
        if any(keyword in message for keyword in food_keywords):
            return "food"
        
        # 인사 관련
        greeting_keywords = ['안녕', '하이', '반가워', '처음']
        if any(keyword in message for keyword in greeting_keywords):
            return "greeting"
        
        # 도움말 관련
        help_keywords = ['도움', '도와', '어떻게', '무엇', '뭐', '사용법']
        if any(keyword in message for keyword in help_keywords):
            return "help"
        
        return "general"

    async def _generate_response_by_intent(
        self,
        intent: str,
        message: str,
        context: dict[str, Any] | None = None
    ) -> str:
        """의도에 따른 기본 응답 생성"""
        responses = {
            "weather": (
                "🌤️ 현재 날씨 정보를 확인해드릴게요! "
                "어느 지역의 날씨를 알고 싶으신가요?"
            ),
            "travel": (
                "✈️ 멋진 여행지 추천을 도와드릴게요! "
                "어떤 종류의 여행을 계획하고 계신가요?"
            ),
            "accommodation": (
                "🏨 숙박시설 정보를 도와드릴게요! "
                "어느 지역의 숙박을 찾고 계신가요?"
            ),
            "food": (
                "🍽️ 맛있는 맛집 정보를 찾아드릴게요! "
                "어느 지역의 맛집을 찾고 계신가요?"
            ),
            "greeting": (
                "안녕하세요! 🌟 Weather Flick 여행 도우미입니다! "
                "날씨 정보와 여행 추천을 도와드려요."
            ),
            "help": (
                "🆘 Weather Flick 사용법을 안내해드릴게요!\n"
                "• 실시간 날씨 정보 조회\n"
                "• 날씨 기반 여행지 추천\n"
                "• 여행 일정 계획 도움"
            )
        }
        
        return responses.get(intent, (
            "무엇을 도와드릴까요? "
            "날씨, 여행지, 맛집, 숙박 정보 등을 물어보세요!"
        ))

    async def _generate_fallback_response(self) -> dict[str, Any]:
        """오류 시 기본 응답"""
        return {
            "response": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "suggestions": ["날씨 정보", "여행지 추천", "도움말"],
            "intent": "error",
            "source": "fallback",
            "personalized": False
        }

    async def _get_conversation_history(self, user_id: Any, limit: int = 5) -> list[dict[str, str]]:
        """최근 대화 기록 조회"""
        try:
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.user_id == user_id)
                .order_by(desc(ChatMessage.created_at))
                .limit(limit * 2)
            )
            
            messages = self.db.execute(stmt).scalars().all()
            messages = list(messages)
            messages.reverse()
            
            # 기존 테이블 구조에 맞게 수정 (message: 사용자 메시지, response: 봇 응답)
            conversation = []
            for msg in messages:
                # 사용자 메시지 추가
                conversation.append({
                    "role": "user",
                    "content": msg.message
                })
                # 봇 응답 추가
                if msg.response:
                    conversation.append({
                        "role": "assistant",
                        "content": msg.response
                    })
            
            return conversation[-10:]
            
        except Exception as e:
            logger.warning(f"대화 기록 조회 실패: {e}")
            return []