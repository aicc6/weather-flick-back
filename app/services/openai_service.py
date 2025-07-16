"""OpenAI integration service for Weather Flick."""

import logging
from typing import Any

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

class OpenAIService:
    """OpenAI API 통합 서비스"""

    def __init__(self):
        """OpenAI 클라이언트 초기화"""
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured")
            self.client = None
        else:
            # Python 3.13 호환성 문제 해결을 위해 프록시 환경 변수 제거
            import os
            for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
                os.environ.pop(proxy_var, None)
            
            try:
                self.client = OpenAI(api_key=settings.openai_api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None

    async def generate_travel_recommendation(
        self,
        user_preferences: dict[str, Any],
        weather_data: dict[str, Any],
        destination_info: dict[str, Any]
    ) -> str:
        """
        사용자 선호도와 날씨 정보를 기반으로 여행 추천 생성

        Args:
            user_preferences: 사용자 선호도 정보
            weather_data: 날씨 정보
            destination_info: 목적지 정보

        Returns:
            str: 생성된 여행 추천 텍스트
        """
        if not self.client:
            return "OpenAI 서비스가 설정되지 않았습니다."

        try:
            # 프롬프트 구성
            prompt = self._build_recommendation_prompt(
                user_preferences, weather_data, destination_info
            )

            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 날씨 기반 여행 추천 전문가입니다. 한국어로 친근하고 유용한 여행 조언을 제공해주세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=settings.openai_max_tokens,
                temperature=settings.openai_temperature,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"OpenAI API 호출 실패: {e}")
            return f"추천 생성 중 오류가 발생했습니다: {str(e)}"

    async def generate_travel_itinerary(
        self,
        destination: str,
        duration: int,
        interests: list[str],
        weather_forecast: list[dict[str, Any]]
    ) -> str:
        """
        여행 일정 생성

        Args:
            destination: 목적지
            duration: 여행 기간 (일)
            interests: 관심사 목록
            weather_forecast: 날씨 예보 정보

        Returns:
            str: 생성된 여행 일정
        """
        if not self.client:
            return "OpenAI 서비스가 설정되지 않았습니다."

        try:
            prompt = self._build_itinerary_prompt(
                destination, duration, interests, weather_forecast
            )

            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 전문 여행 플래너입니다. 날씨를 고려한 상세한 일정을 한국어로 작성해주세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=settings.openai_max_tokens,
                temperature=settings.openai_temperature,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"일정 생성 실패: {e}")
            return f"일정 생성 중 오류가 발생했습니다: {str(e)}"

    async def generate_chatbot_response(
        self,
        user_message: str,
        conversation_history: list[dict[str, str]] = None
    ) -> str:
        """
        챗봇 응답 생성

        Args:
            user_message: 사용자 메시지
            conversation_history: 대화 기록

        Returns:
            str: 챗봇 응답
        """
        if not self.client:
            return "죄송합니다. 현재 챗봇 서비스를 이용할 수 없습니다."

        try:
            # 시스템 메시지
            messages = [
                {
                    "role": "system",
                    "content": """당신은 Weather Flick의 여행 도우미 챗봇입니다.

                    【중요 규칙 - 반드시 준수】
                    사용자의 질문을 받으면 먼저 다음을 판단하세요:
                    
                    1. 허용된 주제인가?
                       ✅ 허용: 여행, 날씨, 관광지, 숙박, 교통, 맛집, 여행 준비, 챗봇 자신, Weather Flick 서비스
                       ❌ 금지: 위에 없는 모든 주제 (수학, 과학, 일반 상식, 프로그래밍, 요리, 정치, 경제 등)
                    
                    2. 금지된 주제라면 반드시 이 메시지만 답하세요:
                       "죄송합니다. 저는 여행과 날씨에 관한 도움만 드릴 수 있습니다. 여행 계획이나 날씨 기반 추천이 필요하시면 언제든 물어보세요! 😊"
                    
                    【자기소개】
                    안녕하세요! 저는 Weather Flick의 AI 여행 도우미입니다. 🌤️
                    날씨를 기반으로 최적의 여행 계획을 세울 수 있도록 도와드리는 챗봇이에요.

                    【주요 기능】
                    1. 날씨 기반 여행 추천
                    2. 여행 계획 수립 지원
                    3. 관광지 정보 제공
                    4. 여행 팁 및 조언
                    5. 날씨에 따른 여행지 추천
                    6. 챗봇 사용법 안내

                    【응답 방식】
                    - 허용된 주제에만 답변하세요
                    - 챗봇에 대해 물어보면 친절하게 자기소개와 가능한 도움을 설명하세요
                    - 항상 친근하고 도움이 되는 톤을 유지하세요
                    - 이모지를 적절히 사용하여 친근함을 표현하세요
                    - 모든 응답은 한국어로 작성하세요
                    
                    【주의사항】
                    - 여행/날씨와 관련이 없는 질문에는 절대 답변하지 마세요
                    - 계산, 코딩, 번역, 일반 지식 등의 질문은 모두 거절하세요
                    - 거절 시 위의 정해진 문구만 사용하세요"""
                }
            ]

            # 대화 기록 추가
            if conversation_history:
                messages.extend(conversation_history)

            # 현재 사용자 메시지 추가
            messages.append({
                "role": "user",
                "content": user_message
            })

            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                max_tokens=settings.openai_max_tokens,
                temperature=settings.openai_temperature,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"챗봇 응답 생성 실패: {e}")
            return "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

    def _build_recommendation_prompt(
        self,
        user_preferences: dict[str, Any],
        weather_data: dict[str, Any],
        destination_info: dict[str, Any]
    ) -> str:
        """여행 추천 프롬프트 구성"""

        prompt = f"""
다음 정보를 바탕으로 개인화된 여행 추천을 해주세요:

**사용자 선호도:**
- 선호 지역: {user_preferences.get('region', '미지정')}
- 여행 테마: {user_preferences.get('theme', '미지정')}
- 동행자: {user_preferences.get('companions', '미지정')}
- 예산: {user_preferences.get('budget', '미지정')}

**현재 날씨 정보:**
- 온도: {weather_data.get('temperature', 'N/A')}°C
- 날씨: {weather_data.get('condition', 'N/A')}
- 습도: {weather_data.get('humidity', 'N/A')}%
- 강수확률: {weather_data.get('precipitation_chance', 'N/A')}%

**목적지 정보:**
- 지역: {destination_info.get('name', 'N/A')}
- 특징: {destination_info.get('description', 'N/A')}

위 정보를 종합하여 다음을 포함한 추천을 작성해주세요:
1. 현재 날씨에 적합한 활동
2. 사용자 선호도에 맞는 장소
3. 준비물 및 주의사항
4. 추천 시간대

200-300단어로 작성해주세요.
        """

        return prompt.strip()

    def _build_itinerary_prompt(
        self,
        destination: str,
        duration: int,
        interests: list[str],
        weather_forecast: list[dict[str, Any]]
    ) -> str:
        """여행 일정 프롬프트 구성"""

        interests_str = ", ".join(interests) if interests else "일반 관광"

        weather_info = ""
        for i, forecast in enumerate(weather_forecast[:duration]):
            weather_info += f"- {i+1}일차: {forecast.get('condition', 'N/A')}, {forecast.get('temperature', 'N/A')}°C\n"

        prompt = f"""
다음 조건에 맞는 {duration}일 여행 일정을 작성해주세요:

**목적지:** {destination}
**여행 기간:** {duration}일
**관심사:** {interests_str}

**날씨 예보:**
{weather_info}

각 일차별로 다음을 포함해주세요:
1. 오전/오후/저녁 활동
2. 추천 장소와 이유
3. 날씨를 고려한 실내/실외 활동 균형
4. 이동 경로 및 소요 시간
5. 식사 추천

날씨에 따른 대안 활동도 제시해주세요.
        """

        return prompt.strip()

    async def generate_personalized_response(
        self,
        user_message: str,
        conversation_history: list[dict[str, str]],
        system_prompt: str,
        user_context: dict[str, Any] | None = None
    ) -> str:
        """
        사용자 맞춤형 챗봇 응답 생성

        Args:
            user_message: 사용자 메시지
            conversation_history: 대화 기록
            system_prompt: 개인화된 시스템 프롬프트
            user_context: 사용자 컨텍스트 정보

        Returns:
            str: 생성된 응답
        """
        if not self.client:
            return await self.generate_chatbot_response(user_message, conversation_history)

        try:
            # 메시지 구성
            messages = [{"role": "system", "content": system_prompt}]
            
            # 대화 기록 추가
            messages.extend(conversation_history)
            
            # 현재 메시지 추가
            current_message = user_message
            
            # 사용자 컨텍스트가 있으면 메시지에 포함
            if user_context and user_context.get("recent_searches"):
                current_message += f"\n\n[최근 검색: {', '.join(user_context['recent_searches'][:3])}]"
            
            messages.append({"role": "user", "content": current_message})

            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=0.8,
                max_tokens=300,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"개인화된 챗봇 응답 생성 실패: {e}")
            # Fallback to regular response
            return await self.generate_chatbot_response(user_message, conversation_history)

# OpenAI 서비스 인스턴스
openai_service = OpenAIService()
