"""OpenAI integration service for Weather Flick."""

import logging
from typing import Dict, List, Optional, Any
import openai
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
            self.client = OpenAI(api_key=settings.openai_api_key)
            logger.info("OpenAI client initialized successfully")

    async def generate_travel_recommendation(
        self,
        user_preferences: Dict[str, Any],
        weather_data: Dict[str, Any],
        destination_info: Dict[str, Any]
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
        interests: List[str],
        weather_forecast: List[Dict[str, Any]]
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
        conversation_history: List[Dict[str, str]] = None
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
                    다음 역할을 수행해주세요:
                    1. 날씨 기반 여행 추천
                    2. 여행 계획 도움
                    3. 관광지 정보 제공
                    4. 여행 팁 공유

                    항상 친근하고 도움이 되는 톤으로 한국어로 응답해주세요."""
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
        user_preferences: Dict[str, Any],
        weather_data: Dict[str, Any],
        destination_info: Dict[str, Any]
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
        interests: List[str],
        weather_forecast: List[Dict[str, Any]]
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

# OpenAI 서비스 인스턴스
openai_service = OpenAIService()
