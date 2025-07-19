"""
프롬프트 템플릿 관리 시스템
재사용 가능한 프롬프트 템플릿을 중앙 관리
"""

from typing import Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PromptTemplate(Enum):
    """프롬프트 템플릿 타입"""
    PERSONA_ANALYSIS = "persona_analysis"
    ITINERARY_ANALYSIS = "itinerary_analysis"
    ITINERARY_STRATEGY = "itinerary_strategy"
    ITINERARY_GENERATION = "itinerary_generation"
    PLACE_DESCRIPTION = "place_description"
    WEATHER_ADAPTATION = "weather_adaptation"
    FEEDBACK_LEARNING = "feedback_learning"


class PromptTemplateManager:
    """프롬프트 템플릿 관리자"""
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[PromptTemplate, str]:
        """프롬프트 템플릿 로드"""
        
        return {
            PromptTemplate.PERSONA_ANALYSIS: """
사용자의 여행 선호도와 행동 패턴을 분석하여 페르소나를 도출하세요.

입력 정보:
- 여행 스타일: {travel_styles}
- 동행자: {companions}
- 일정 유형: {schedule_type}
- 과거 여행 기록: {past_trips}

분석 항목:
1. 주요 관심사 (Primary Interest)
2. 보조 관심사 (Secondary Interest)
3. 여행 페이스 선호도
4. 예산 민감도
5. 활동성 수준
6. 문화적 관심도

JSON 형식으로 페르소나 프로필을 생성하세요:
{{
    "primary_persona": "타입",
    "secondary_persona": "타입",
    "characteristics": [],
    "preferences": {{}},
    "constraints": []
}}
""",

            PromptTemplate.ITINERARY_ANALYSIS: """
다음 여행 요청을 심층 분석하세요.

여행 정보:
- 목적지: {destination}
- 기간: {duration}일
- 여행 스타일: {styles}
- 동행자: {companions}
- 교통수단: {transportation}

사용자 페르소나:
{persona_info}

여행 컨텍스트:
- 계절: {season}
- 날씨: {weather}
- 지역 이벤트: {local_events}
- 예상 혼잡도: {crowd_levels}

다음 관점에서 분석하세요:
1. 핵심 여행 목표
2. 페르소나 기반 우선순위
3. 시간 배분 전략
4. 잠재적 제약사항
5. 최적화 기회

분석 결과를 구조화된 JSON으로 제공하세요.
""",

            PromptTemplate.ITINERARY_STRATEGY: """
분석 결과를 바탕으로 {days}일 여행 전략을 수립하세요.

분석 결과:
{analysis_result}

사용 가능한 장소:
{available_places}

전략 수립 지침:
1. 일별 테마 설정
   - 페르소나에 맞는 테마 선정
   - 날씨와 계절 고려
   - 체력 배분 고려

2. 동선 최적화
   - 지리적 근접성
   - 이동 효율성
   - 교통수단 활용

3. 시간 관리
   - 적정 체류 시간
   - 이동 시간 고려
   - 식사 시간 확보
   - 휴식 시간 배치

4. 유연성 확보
   - 날씨 대안
   - 혼잡도 대응
   - 선택적 일정

각 날짜별 전략을 JSON으로 작성하세요:
{{
    "day_strategies": [
        {{
            "day": 1,
            "theme": "",
            "focus_areas": [],
            "time_allocation": {{}},
            "key_places": [],
            "backup_plans": []
        }}
    ],
    "overall_approach": "",
    "optimization_priorities": []
}}
""",

            PromptTemplate.ITINERARY_GENERATION: """
수립된 전략에 따라 구체적인 {days}일 여행 일정을 생성하세요.

전략:
{strategy}

장소 정보:
{places_detail}

일정 생성 규칙:
1. 시간 배치
   - 오전: 주요 관광지 (체력 필요한 곳)
   - 점심: 12:00-14:00 사이
   - 오후: 실내/가벼운 활동
   - 저녁: 18:00-20:00 사이
   - 야간: 선택적 활동

2. 이동 고려
   - 도보 20분 이내 우선
   - 대중교통 활용 시 환승 최소화
   - 피크 시간 회피

3. 체험 다양성
   - 문화/자연/음식/쇼핑 균형
   - 실내/실외 적절히 배치
   - 휴식 시간 확보

구체적 일정을 JSON으로 생성하세요:
{{
    "itinerary": [
        {{
            "day": 1,
            "date": "{start_date}",
            "theme": "",
            "places": [
                {{
                    "place_id": "",
                    "name": "",
                    "arrival_time": "HH:MM",
                    "departure_time": "HH:MM",
                    "duration_minutes": 0,
                    "activity_type": "",
                    "meal_included": false,
                    "transport_to_next": {{
                        "mode": "",
                        "duration_minutes": 0,
                        "cost": 0
                    }},
                    "tips": [],
                    "weather_alternatives": []
                }}
            ],
            "daily_tips": [],
            "total_cost_estimate": 0
        }}
    ],
    "general_recommendations": []
}}
""",

            PromptTemplate.PLACE_DESCRIPTION: """
{persona_type} 페르소나를 위한 장소 설명을 생성하세요.

장소 정보:
- 이름: {place_name}
- 유형: {place_type}
- 태그: {tags}
- 평점: {rating}
- 기본 설명: {base_description}

페르소나 특성:
- 주요 관심사: {interests}
- 여행 스타일: {travel_style}

다음을 포함한 맞춤 설명을 작성하세요:
1. 페르소나에게 어필할 포인트
2. 추천 활동이나 경험
3. 최적 방문 시간
4. 실용적 팁
5. 주변 연계 장소

50-100단어로 간결하게 작성하세요.
""",

            PromptTemplate.WEATHER_ADAPTATION: """
날씨 조건에 따른 일정 조정안을 제시하세요.

현재 일정:
{current_itinerary}

날씨 예보:
{weather_forecast}

조정 지침:
1. 우천 시
   - 실외 → 실내 대체
   - 도보 이동 최소화
   - 우산/우비 준비 안내

2. 폭염/한파 시
   - 실외 활동 시간 단축
   - 실내 휴식 공간 추가
   - 적절한 복장 안내

3. 미세먼지 시
   - 실외 활동 제한
   - 마스크 착용 권고
   - 실내 대안 제시

조정된 일정과 주의사항을 JSON으로 제공하세요.
""",

            PromptTemplate.FEEDBACK_LEARNING: """
사용자 피드백을 분석하여 개선 사항을 도출하세요.

원본 일정:
{original_itinerary}

사용자 피드백:
{user_feedback}

실제 여행 데이터:
- 방문한 장소: {visited_places}
- 건너뛴 장소: {skipped_places}
- 추가한 장소: {added_places}
- 체류 시간 변화: {duration_changes}

분석 항목:
1. 선호도 패턴
2. 시간 배분 적정성
3. 동선 효율성
4. 페르소나 정확도
5. 개선 제안사항

학습 결과를 JSON으로 정리하세요:
{{
    "preference_updates": {{}},
    "timing_adjustments": {{}},
    "persona_refinements": {{}},
    "recommendations": []
}}
"""
        }
    
    def get_template(self, template_type: PromptTemplate) -> str:
        """템플릿 가져오기"""
        return self.templates.get(template_type, "")
    
    def fill_template(self, template_type: PromptTemplate, **kwargs) -> str:
        """템플릿에 값 채우기"""
        template = self.get_template(template_type)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"템플릿 채우기 실패 - 누락된 키: {e}")
            return template
    
    def create_custom_template(self, base_template: PromptTemplate, modifications: Dict[str, str]) -> str:
        """기존 템플릿을 수정하여 커스텀 템플릿 생성"""
        template = self.get_template(base_template)
        
        for key, value in modifications.items():
            template = template.replace(f"{{{key}}}", value)
        
        return template
    
    def combine_templates(self, templates: List[PromptTemplate], separator: str = "\n\n---\n\n") -> str:
        """여러 템플릿을 결합"""
        combined = []
        for template_type in templates:
            combined.append(self.get_template(template_type))
        
        return separator.join(combined)


# 싱글톤 인스턴스
prompt_manager = PromptTemplateManager()


def get_prompt_template(template_type: PromptTemplate, **kwargs) -> str:
    """프롬프트 템플릿 가져오기 헬퍼 함수"""
    return prompt_manager.fill_template(template_type, **kwargs)


def create_few_shot_prompt(examples: List[Dict[str, Any]], task_description: str) -> str:
    """Few-shot 학습을 위한 프롬프트 생성"""
    
    prompt = f"{task_description}\n\n"
    prompt += "다음은 참고할 수 있는 예시들입니다:\n\n"
    
    for i, example in enumerate(examples, 1):
        prompt += f"예시 {i}:\n"
        prompt += f"입력: {example.get('input', '')}\n"
        prompt += f"출력: {example.get('output', '')}\n"
        if 'explanation' in example:
            prompt += f"설명: {example['explanation']}\n"
        prompt += "\n"
    
    prompt += "위 예시를 참고하여 작업을 수행하세요.\n"
    
    return prompt


def create_chain_of_thought_prompt(task: str, steps: List[str]) -> str:
    """Chain of Thought 프롬프트 생성"""
    
    prompt = f"다음 작업을 단계별로 수행하세요: {task}\n\n"
    prompt += "추론 과정:\n"
    
    for i, step in enumerate(steps, 1):
        prompt += f"단계 {i}: {step}\n"
    
    prompt += "\n각 단계별로 추론 과정을 명시하고, 최종 결과를 제시하세요.\n"
    
    return prompt