"""
고도화된 AI 기반 여행 추천 서비스
- 향상된 프롬프트 엔지니어링
- 사용자 페르소나 기반 추천
- Chain of Thought 추론
- 이동 시간 및 체류 시간 최적화
- 스마트 캐싱 및 비용 최적화
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from openai import OpenAI
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models import (
    CustomTravelRecommendationRequest,
    DayItinerary,
    PlaceRecommendation,
    User,
)
from app.config import settings

logger = logging.getLogger(__name__)

# Redis를 선택적으로 import
try:
    import redis
except ImportError:
    redis = None
    logger.warning("Redis not installed - caching disabled")


class PersonaType(Enum):
    """사용자 페르소나 타입"""
    ADVENTURER = "adventurer"  # 모험가형
    CULTURAL = "cultural"      # 문화탐방형
    FOODIE = "foodie"         # 미식가형
    RELAXER = "relaxer"       # 휴식추구형
    SHOPPER = "shopper"       # 쇼핑매니아형
    FAMILY = "family"         # 가족여행형
    BUDGET = "budget"         # 예산절약형
    LUXURY = "luxury"         # 럭셔리형


@dataclass
class UserPersona:
    """사용자 페르소나 정보"""
    primary_type: PersonaType
    secondary_type: Optional[PersonaType]
    travel_pace: str  # "packed", "moderate", "relaxed"
    budget_level: str  # "budget", "moderate", "luxury"
    preferences: Dict[str, float]  # 선호도 점수
    constraints: List[str]  # 제약사항
    past_behaviors: Dict[str, Any]  # 과거 행동 패턴


@dataclass
class TravelContext:
    """여행 컨텍스트 정보"""
    season: str
    weather_conditions: Dict[str, Any]
    local_events: List[str]
    crowd_levels: Dict[str, str]  # 장소별 혼잡도
    transport_conditions: Dict[str, Any]
    conversation_history: List[Dict[str, str]]


@dataclass
class OptimizedPlace:
    """최적화된 장소 정보"""
    place: PlaceRecommendation
    arrival_time: str
    departure_time: str
    duration_minutes: int
    transport_to_next: Optional[Dict[str, Any]]
    weather_suitable: bool
    crowd_level: str
    alternatives: List[PlaceRecommendation]


class AdvancedAIRecommendationService:
    """고도화된 AI 추천 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # RouteOptimizer를 선택적으로 초기화
        try:
            from app.services.route_optimizer import RouteOptimizer
            self.route_optimizer = RouteOptimizer()  # db 파라미터 제거
        except ImportError:
            logger.warning("RouteOptimizer not available - route optimization disabled")
            self.route_optimizer = None
        
        # Redis 캐시 초기화
        if redis:
            try:
                self.cache = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    decode_responses=True
                )
                # 연결 테스트
                self.cache.ping()
            except Exception as e:
                logger.warning(f"Redis 연결 실패 - 캐싱 비활성화: {str(e)}")
                self.cache = None
        else:
            self.cache = None
        
        # OpenAI 클라이언트 초기화
        # Python 3.13 호환성 문제 해결을 위해 프록시 환경 변수 제거
        import os
        for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy']:
            os.environ.pop(proxy_var, None)
        
        # OpenAI v1.x에서는 proxies 파라미터를 지원하지 않음
        self.client = OpenAI(api_key=settings.openai_api_key)
        
        # 모델 선택 전략 (설정에서 가져오기)
        self.model_strategy = {
            "simple": settings.ai_model_simple,      # 간단한 요청
            "standard": settings.ai_model_standard,  # 표준 요청
            "complex": settings.ai_model_complex,    # 복잡한 요청
            "premium": settings.ai_model_premium     # 프리미엄 요청
        }
    
    async def generate_advanced_itinerary(
        self,
        user: User,
        request: CustomTravelRecommendationRequest,
        places: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[DayItinerary]:
        """고급 AI 기반 여행 일정 생성"""
        
        logger.info(f"고급 AI 일정 생성 시작 - 사용자: {user.id}, 지역: {request.region_name}")
        
        # 1. 사용자 페르소나 분석
        user_persona = await self._analyze_user_persona(user, request)
        
        # 2. 여행 컨텍스트 수집
        travel_context = await self._gather_travel_context(
            request, conversation_history
        )
        
        # 3. 캐시 확인
        cache_key = self._generate_cache_key(user, request, user_persona)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            logger.info("캐시된 결과 사용")
            return cached_result
        
        # 4. 모델 선택
        model = self._select_model(request, user_persona)
        
        # 5. 향상된 프롬프트 생성
        prompt_data = self._create_advanced_prompt(
            request, places, user_persona, travel_context
        )
        
        try:
            # 6. AI 추론 (Chain of Thought)
            reasoning_result = await self._chain_of_thought_reasoning(
                prompt_data, model
            )
            
            # 7. 일정 생성 및 최적화
            optimized_itinerary = await self._generate_and_optimize_itinerary(
                reasoning_result, places, request, user_persona, travel_context
            )
            
            # 8. 결과 캐싱
            if optimized_itinerary and self.cache:
                self._cache_result(cache_key, optimized_itinerary)
            
            return optimized_itinerary
            
        except Exception as e:
            logger.error(f"고급 AI 추천 생성 실패: {str(e)}")
            # 폴백 전략
            return await self._fallback_generation(request, places)
    
    async def _analyze_user_persona(
        self, user: User, request: CustomTravelRecommendationRequest
    ) -> UserPersona:
        """사용자 페르소나 분석"""
        
        # 여행 스타일 기반 주요 페르소나 결정
        style_persona_map = {
            "adventure": PersonaType.ADVENTURER,
            "culture": PersonaType.CULTURAL,
            "food": PersonaType.FOODIE,
            "relax": PersonaType.RELAXER,
            "shopping": PersonaType.SHOPPER,
            "family": PersonaType.FAMILY,
        }
        
        primary_type = PersonaType.CULTURAL  # 기본값
        secondary_type = None
        
        # 사용자의 여행 스타일 분석
        if request.styles:
            for style in request.styles[:2]:  # 상위 2개 스타일
                if style in style_persona_map:
                    if not primary_type:
                        primary_type = style_persona_map[style]
                    else:
                        secondary_type = style_persona_map[style]
        
        # 선호도 점수 계산
        preferences = self._calculate_preferences(user, request)
        
        # 제약사항 분석
        constraints = []
        if request.who == "family":
            constraints.append("아이 친화적인 장소 필요")
        if request.who == "elderly":
            constraints.append("이동 거리 최소화")
            constraints.append("계단이 적은 장소 선호")
        
        # 과거 행동 패턴 (실제로는 DB에서 조회)
        past_behaviors = {
            "avg_places_per_day": 4,
            "preferred_start_time": "10:00",
            "lunch_duration": 90,
            "favorite_categories": ["culture", "food"],
        }
        
        return UserPersona(
            primary_type=primary_type,
            secondary_type=secondary_type,
            travel_pace=request.schedule,
            budget_level=self._analyze_budget_level(request),
            preferences=preferences,
            constraints=constraints,
            past_behaviors=past_behaviors
        )
    
    def _calculate_preferences(
        self, user: User, request: CustomTravelRecommendationRequest
    ) -> Dict[str, float]:
        """사용자 선호도 점수 계산"""
        
        preferences = {
            "culture": 0.5,
            "nature": 0.5,
            "food": 0.5,
            "shopping": 0.5,
            "activity": 0.5,
            "relaxation": 0.5,
        }
        
        # 스타일 기반 가중치
        style_weights = {
            "adventure": {"nature": 0.8, "activity": 0.9},
            "culture": {"culture": 0.9},
            "food": {"food": 0.9},
            "relax": {"relaxation": 0.9, "nature": 0.6},
            "shopping": {"shopping": 0.9},
        }
        
        for style in request.styles:
            if style in style_weights:
                for pref, weight in style_weights[style].items():
                    preferences[pref] = min(1.0, preferences[pref] + weight * 0.3)
        
        return preferences
    
    def _analyze_budget_level(self, request: CustomTravelRecommendationRequest) -> str:
        """예산 수준 분석"""
        # 실제로는 더 복잡한 로직이 필요
        if hasattr(request, 'budget'):
            if request.budget < 100000:
                return "budget"
            elif request.budget > 500000:
                return "luxury"
        return "moderate"
    
    async def _gather_travel_context(
        self,
        request: CustomTravelRecommendationRequest,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> TravelContext:
        """여행 컨텍스트 수집"""
        
        # 현재 날짜 기준 계절 판단
        current_date = datetime.now()
        month = current_date.month
        
        if month in [3, 4, 5]:
            season = "spring"
        elif month in [6, 7, 8]:
            season = "summer"
        elif month in [9, 10, 11]:
            season = "autumn"
        else:
            season = "winter"
        
        # 날씨 정보 (실제로는 날씨 API 호출)
        weather_conditions = {
            "temperature_range": "15-25°C",
            "precipitation_chance": 20,
            "conditions": ["partly_cloudy"],
        }
        
        # 지역 이벤트 (실제로는 이벤트 DB 조회)
        local_events = []
        if season == "spring":
            local_events.append("벚꽃 축제")
        elif season == "autumn":
            local_events.append("단풍 축제")
        
        # 혼잡도 예측 (실제로는 빅데이터 분석)
        crowd_levels = {
            "popular_spots": "high" if request.days in ["weekend", "holiday"] else "moderate",
            "restaurants": "high" if "lunch" in str(datetime.now().hour) else "moderate",
        }
        
        # 교통 상황
        transport_conditions = {
            "traffic_level": "moderate",
            "public_transport_status": "normal",
        }
        
        return TravelContext(
            season=season,
            weather_conditions=weather_conditions,
            local_events=local_events,
            crowd_levels=crowd_levels,
            transport_conditions=transport_conditions,
            conversation_history=conversation_history or []
        )
    
    def _generate_cache_key(
        self, user: User, request: CustomTravelRecommendationRequest, persona: UserPersona
    ) -> str:
        """캐시 키 생성"""
        
        key_data = {
            "user_id": user.id,
            "region": request.region_name,
            "days": request.days,
            "styles": sorted(request.styles),
            "who": request.who,
            "schedule": request.schedule,
            "persona": persona.primary_type.value,
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return f"ai_itinerary:{hashlib.md5(key_str.encode()).hexdigest()}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[List[DayItinerary]]:
        """캐시된 결과 조회"""
        if not self.cache:
            return None
        
        try:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"캐시 조회 실패: {str(e)}")
        
        return None
    
    def _cache_result(self, cache_key: str, result: List[DayItinerary], ttl: int = 3600):
        """결과 캐싱"""
        if not self.cache:
            return
        
        try:
            # DayItinerary 객체를 직렬화 가능한 형태로 변환
            serializable_result = []
            for day in result:
                day_data = {
                    "day": day.day,
                    "places": [asdict(place) for place in day.places],
                    "weather": day.weather
                }
                serializable_result.append(day_data)
            
            self.cache.setex(cache_key, ttl, json.dumps(serializable_result))
        except Exception as e:
            logger.error(f"캐시 저장 실패: {str(e)}")
    
    def _select_model(
        self, request: CustomTravelRecommendationRequest, persona: UserPersona
    ) -> str:
        """요청 복잡도에 따른 모델 선택"""
        
        # 복잡도 점수 계산
        complexity_score = 0
        
        # 일정 길이
        complexity_score += request.days * 0.5
        
        # 여행 스타일 다양성
        complexity_score += len(request.styles) * 0.3
        
        # 제약사항
        complexity_score += len(persona.constraints) * 0.4
        
        # 페르소나 복잡도
        if persona.secondary_type:
            complexity_score += 1
        
        # 모델 선택
        if complexity_score < 2:
            return self.model_strategy["simple"]
        elif complexity_score < 4:
            return self.model_strategy["standard"]
        elif complexity_score < 6:
            return self.model_strategy["complex"]
        else:
            return self.model_strategy["premium"]
    
    def _create_advanced_prompt(
        self,
        request: CustomTravelRecommendationRequest,
        places: List[Dict[str, Any]],
        persona: UserPersona,
        context: TravelContext
    ) -> Dict[str, Any]:
        """향상된 프롬프트 생성"""
        
        # 프롬프트 템플릿 사용
        from app.services.prompt_templates import prompt_manager, PromptTemplate
        
        # 장소 정보 구조화
        categorized_places = self._categorize_places(places)
        
        # Few-shot 예시
        few_shot_examples = self._get_few_shot_examples(persona.primary_type)
        
        prompt_data = {
            "request": {
                "destination": request.region_name,
                "duration": request.days,
                "travel_party": request.who,
                "schedule_preference": request.schedule,
                "styles": request.styles,
                "transportation": request.transportation,
            },
            "user_persona": {
                "primary_type": persona.primary_type.value,
                "secondary_type": persona.secondary_type.value if persona.secondary_type else None,
                "preferences": persona.preferences,
                "constraints": persona.constraints,
                "past_behaviors": persona.past_behaviors,
            },
            "context": {
                "season": context.season,
                "weather": context.weather_conditions,
                "local_events": context.local_events,
                "crowd_levels": context.crowd_levels,
            },
            "available_places": categorized_places,
            "optimization_goals": [
                "이동 거리 최소화",
                "체류 시간 최적화",
                "식사 시간 고려",
                "휴식 시간 확보",
                "날씨 조건 반영",
            ],
            "few_shot_examples": few_shot_examples,
            "output_format": {
                "type": "structured_json",
                "schema": self._get_output_schema(),
            }
        }
        
        return prompt_data
    
    def _categorize_places(self, places: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """장소를 카테고리별로 분류"""
        
        categories = {
            "must_visit": [],      # 필수 방문 명소
            "cultural": [],        # 문화 시설
            "nature": [],          # 자연 관광지
            "food": [],           # 맛집
            "shopping": [],       # 쇼핑
            "activity": [],       # 액티비티
            "accommodation": [],  # 숙박
            "hidden_gems": [],    # 숨은 명소
        }
        
        for place in places:
            # 평점과 리뷰 수 기반 필수 방문지 선정
            if place.get("rating", 0) >= 4.5 and place.get("review_count", 0) > 100:
                categories["must_visit"].append(self._simplify_place_info(place))
            
            # 타입별 분류
            place_type = self._determine_place_category(place)
            if place_type in categories:
                categories[place_type].append(self._simplify_place_info(place))
        
        # 각 카테고리별 상위 10개만 유지 (토큰 절약)
        for category in categories:
            categories[category] = categories[category][:10]
        
        return categories
    
    def _simplify_place_info(self, place: Dict[str, Any]) -> Dict[str, Any]:
        """장소 정보 간소화"""
        return {
            "id": place["id"],
            "name": place["name"],
            "type": place.get("type", "attraction"),
            "rating": place.get("rating", 4.0),
            "tags": place.get("tags", [])[:5],
            "coordinates": {
                "lat": place.get("latitude"),
                "lng": place.get("longitude")
            },
            "typical_duration": self._estimate_typical_duration(place),
            "best_time": self._estimate_best_visit_time(place),
        }
    
    def _determine_place_category(self, place: Dict[str, Any]) -> str:
        """장소 카테고리 결정"""
        place_type = place.get("type", "").lower()
        tags = " ".join(place.get("tags", [])).lower()
        
        if place_type == "accommodation" or "숙박" in tags:
            return "accommodation"
        elif place_type == "restaurant" or any(food in tags for food in ["맛집", "음식", "카페"]):
            return "food"
        elif any(culture in tags for culture in ["박물관", "미술관", "전시", "문화"]):
            return "cultural"
        elif any(nature in tags for nature in ["공원", "산", "해변", "자연"]):
            return "nature"
        elif any(shop in tags for shop in ["쇼핑", "시장", "백화점"]):
            return "shopping"
        elif any(activity in tags for activity in ["체험", "액티비티", "레저"]):
            return "activity"
        elif place.get("rating", 0) < 4.0 and place.get("review_count", 0) < 50:
            return "hidden_gems"
        
        return "must_visit"
    
    def _estimate_typical_duration(self, place: Dict[str, Any]) -> int:
        """장소별 일반적인 체류 시간 추정 (분)"""
        place_type = self._determine_place_category(place)
        
        duration_map = {
            "food": 90,
            "cultural": 120,
            "nature": 150,
            "shopping": 120,
            "activity": 180,
            "must_visit": 120,
            "hidden_gems": 60,
            "accommodation": 720,  # 12시간 (숙박)
        }
        
        return duration_map.get(place_type, 90)
    
    def _estimate_best_visit_time(self, place: Dict[str, Any]) -> str:
        """최적 방문 시간대 추정"""
        place_type = self._determine_place_category(place)
        tags = " ".join(place.get("tags", [])).lower()
        
        if place_type == "food":
            if "아침" in tags or "브런치" in tags:
                return "morning"
            elif "점심" in tags:
                return "lunch"
            elif "저녁" in tags or "디너" in tags:
                return "dinner"
            return "anytime"
        
        elif place_type == "nature":
            if "일출" in tags:
                return "early_morning"
            elif "일몰" in tags or "야경" in tags:
                return "evening"
            return "morning"
        
        elif place_type == "shopping":
            return "afternoon"
        
        elif place_type == "cultural":
            return "morning"
        
        return "anytime"
    
    def _get_few_shot_examples(self, persona_type: PersonaType) -> List[Dict[str, Any]]:
        """페르소나별 Few-shot 예시"""
        
        examples = {
            PersonaType.ADVENTURER: [
                {
                    "input": "2일 액티비티 중심 여행",
                    "reasoning": "활동적인 체험을 선호하므로 등산, 수상스포츠 등을 중심으로 구성",
                    "output": {
                        "day1": ["오전: 산악 트레킹", "점심: 산장 식사", "오후: 패러글라이딩", "저녁: 로컬 맛집"],
                        "day2": ["오전: 래프팅", "점심: 강변 식당", "오후: 집라인", "저녁: 캠프파이어"]
                    }
                }
            ],
            PersonaType.CULTURAL: [
                {
                    "input": "3일 문화 탐방 여행",
                    "reasoning": "역사와 문화에 관심이 많으므로 박물관, 전통 마을 등을 포함",
                    "output": {
                        "day1": ["오전: 국립박물관", "점심: 전통 한정식", "오후: 고궁 투어", "저녁: 전통 공연 관람"],
                        "day2": ["오전: 전통 마을", "점심: 향토 음식", "오후: 미술관", "저녁: 한옥 카페"],
                        "day3": ["오전: 사찰 방문", "점심: 사찰음식", "오후: 전통 공예 체험", "저녁: 전통주 시음"]
                    }
                }
            ],
            PersonaType.FOODIE: [
                {
                    "input": "2일 미식 여행",
                    "reasoning": "음식이 주목적이므로 유명 맛집과 로컬 푸드를 중심으로 일정 구성",
                    "output": {
                        "day1": ["오전: 전통시장 투어", "브런치: 유명 브런치 카페", "오후: 디저트 카페 투어", "저녁: 미슐랭 레스토랑"],
                        "day2": ["오전: 로컬 아침식사", "점심: 향토 맛집", "오후: 와이너리 방문", "저녁: 야시장 투어"]
                    }
                }
            ]
        }
        
        return examples.get(persona_type, [])
    
    def _get_output_schema(self) -> Dict[str, Any]:
        """출력 JSON 스키마"""
        return {
            "itinerary": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "day": {"type": "integer"},
                        "theme": {"type": "string"},
                        "places": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "place_id": {"type": "string"},
                                    "arrival_time": {"type": "string"},
                                    "departure_time": {"type": "string"},
                                    "duration_minutes": {"type": "integer"},
                                    "meal_type": {"type": "string", "nullable": True},
                                    "transport_to_next": {
                                        "type": "object",
                                        "properties": {
                                            "mode": {"type": "string"},
                                            "duration_minutes": {"type": "integer"},
                                            "distance_km": {"type": "number"}
                                        }
                                    },
                                    "weather_plan": {"type": "string"},
                                    "alternatives": {"type": "array", "items": {"type": "string"}}
                                }
                            }
                        },
                        "tips": {"type": "array", "items": {"type": "string"}},
                        "total_distance_km": {"type": "number"},
                        "walking_time_minutes": {"type": "integer"}
                    }
                }
            },
            "reasoning": {
                "type": "object",
                "properties": {
                    "persona_considerations": {"type": "array", "items": {"type": "string"}},
                    "optimization_decisions": {"type": "array", "items": {"type": "string"}},
                    "trade_offs": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _chain_of_thought_reasoning(
        self, prompt_data: Dict[str, Any], model: str
    ) -> Dict[str, Any]:
        """Chain of Thought 추론"""
        
        from app.services.prompt_templates import prompt_manager, PromptTemplate
        
        # Step 1: 초기 분석 (템플릿 사용)
        analysis_prompt = prompt_manager.fill_template(
            PromptTemplate.ITINERARY_ANALYSIS,
            destination=prompt_data['request']['destination'],
            duration=prompt_data['request']['duration'],
            styles=', '.join(prompt_data['request']['styles']),
            companions=prompt_data['request']['travel_party'],
            transportation=prompt_data['request'].get('transportation', '대중교통'),
            persona_info=json.dumps(prompt_data['user_persona'], ensure_ascii=False, indent=2),
            season=prompt_data['context']['season'],
            weather=json.dumps(prompt_data['context']['weather'], ensure_ascii=False),
            local_events=', '.join(prompt_data['context']['local_events']),
            crowd_levels=json.dumps(prompt_data['context']['crowd_levels'], ensure_ascii=False)
        )
        
        analysis_response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "당신은 여행 계획 분석 전문가입니다."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        analysis = json.loads(analysis_response.choices[0].message.content)
        
        # Step 2: 일정 구성 전략
        strategy_prompt = f"""
분석 결과를 바탕으로 {prompt_data['request']['duration']}일 여행 일정 구성 전략을 수립하세요.

분석 결과:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

사용 가능한 장소:
{json.dumps(prompt_data['available_places'], ensure_ascii=False, indent=2)}

각 날짜별로 다음을 결정하세요:
1. 일별 테마 (예: "문화탐방의 날", "자연과 휴식의 날")
2. 방문 장소 선정 기준
3. 최적 동선 계획
4. 식사 장소와 시간
5. 이동 수단과 경로
6. 날씨 대응 계획
7. 대안 장소

Few-shot 예시를 참고하세요:
{json.dumps(prompt_data['few_shot_examples'], ensure_ascii=False, indent=2)}

JSON 형식으로 전략을 수립하세요.
        """
        
        strategy_response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "당신은 여행 일정 전략 수립 전문가입니다."},
                {"role": "user", "content": strategy_prompt}
            ],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        strategy = json.loads(strategy_response.choices[0].message.content)
        
        # Step 3: 상세 일정 생성
        detailed_prompt = f"""
수립된 전략에 따라 상세한 여행 일정을 생성하세요.

전략:
{json.dumps(strategy, ensure_ascii=False, indent=2)}

다음 스키마에 맞춰 JSON을 생성하세요:
{json.dumps(prompt_data['output_format']['schema'], ensure_ascii=False, indent=2)}

주의사항:
- 실제 place_id를 사용하세요
- 이동 시간은 실제 거리를 고려하세요
- 식사 시간은 적절히 배치하세요 (점심 12-14시, 저녁 18-20시)
- 체류 시간은 장소 특성에 맞게 설정하세요
- 각 장소마다 날씨 대응 계획을 포함하세요
- 대안 장소는 근처의 유사한 장소로 선정하세요
        """
        
        detailed_response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "당신은 상세 여행 일정 생성 전문가입니다."},
                {"role": "user", "content": detailed_prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        detailed_itinerary = json.loads(detailed_response.choices[0].message.content)
        
        # 토큰 사용량 로깅
        total_tokens = (
            analysis_response.usage.total_tokens +
            strategy_response.usage.total_tokens +
            detailed_response.usage.total_tokens
        )
        logger.info(f"Chain of Thought 총 토큰 사용량: {total_tokens}")
        
        return {
            "analysis": analysis,
            "strategy": strategy,
            "itinerary": detailed_itinerary,
            "token_usage": total_tokens
        }
    
    async def _generate_and_optimize_itinerary(
        self,
        reasoning_result: Dict[str, Any],
        places: List[Dict[str, Any]],
        request: CustomTravelRecommendationRequest,
        persona: UserPersona,
        context: TravelContext
    ) -> List[DayItinerary]:
        """일정 생성 및 최적화"""
        
        itinerary_data = reasoning_result["itinerary"]
        optimized_days = []
        
        # 장소 ID 매핑
        place_map = {place["id"]: place for place in places}
        
        for day_data in itinerary_data.get("itinerary", []):
            day_places = []
            
            for place_data in day_data.get("places", []):
                place_id = place_data.get("place_id")
                if place_id not in place_map:
                    continue
                
                place = place_map[place_id]
                
                # PlaceRecommendation 객체 생성
                place_rec = PlaceRecommendation(
                    id=place["id"],
                    name=place["name"],
                    time=f"{place_data['arrival_time']}-{place_data['departure_time']}",
                    tags=place.get("tags", [])[:3],
                    description=self._create_place_description(
                        place, place_data, persona
                    ),
                    rating=place.get("rating", 4.0),
                    image=place.get("image"),
                    address=place.get("address"),
                    latitude=place.get("latitude"),
                    longitude=place.get("longitude"),
                )
                
                # 추가 메타데이터 (실제로는 별도 필드로 관리)
                place_rec.metadata = {
                    "duration_minutes": place_data.get("duration_minutes"),
                    "meal_type": place_data.get("meal_type"),
                    "weather_plan": place_data.get("weather_plan"),
                    "alternatives": place_data.get("alternatives", []),
                    "transport_to_next": place_data.get("transport_to_next"),
                }
                
                day_places.append(place_rec)
            
            # 날씨 정보 및 일정 메타데이터
            weather_info = self._create_weather_info(day_data, context)
            
            day_itinerary = DayItinerary(
                day=day_data["day"],
                places=day_places,
                weather=weather_info
            )
            
            # 추가 정보
            day_itinerary.theme = day_data.get("theme", "")
            day_itinerary.tips = day_data.get("tips", [])
            day_itinerary.total_distance = day_data.get("total_distance_km", 0)
            
            optimized_days.append(day_itinerary)
        
        return optimized_days
    
    def _create_place_description(
        self, place: Dict[str, Any], place_data: Dict[str, Any], persona: UserPersona
    ) -> str:
        """페르소나 기반 장소 설명 생성"""
        
        base_description = place.get("description", "")
        
        # 페르소나별 추가 정보
        persona_tips = {
            PersonaType.FOODIE: "맛집 추천",
            PersonaType.CULTURAL: "역사적 의미",
            PersonaType.ADVENTURER: "액티비티 정보",
            PersonaType.FAMILY: "가족 친화 시설",
            PersonaType.BUDGET: "비용 절약 팁",
        }
        
        if persona.primary_type in persona_tips:
            base_description += f" | {persona_tips[persona.primary_type]}"
        
        # 이동 정보 추가
        if place_data.get("transport_to_next"):
            transport = place_data["transport_to_next"]
            base_description += f" | 다음 장소까지 {transport['mode']}로 {transport['duration_minutes']}분"
        
        return base_description
    
    def _create_weather_info(
        self, day_data: Dict[str, Any], context: TravelContext
    ) -> Dict[str, Any]:
        """날씨 정보 생성"""
        
        weather_info = {
            "status": context.weather_conditions.get("conditions", ["맑음"])[0],
            "temperature": context.weather_conditions.get("temperature_range", "15-25°C"),
            "precipitation_chance": context.weather_conditions.get("precipitation_chance", 0),
        }
        
        # 날씨 경고
        if weather_info["precipitation_chance"] > 60:
            weather_info["warning"] = "우산 필수"
        elif weather_info["precipitation_chance"] > 30:
            weather_info["warning"] = "우산 권장"
        
        # 일정 통계 추가
        weather_info["day_stats"] = {
            "total_places": len(day_data.get("places", [])),
            "total_distance_km": day_data.get("total_distance_km", 0),
            "walking_time_minutes": day_data.get("walking_time_minutes", 0),
            "theme": day_data.get("theme", ""),
        }
        
        return weather_info
    
    async def _fallback_generation(
        self, request: CustomTravelRecommendationRequest, places: List[Dict[str, Any]]
    ) -> List[DayItinerary]:
        """폴백 일정 생성"""
        
        logger.warning("AI 생성 실패, 폴백 모드 사용")
        
        # 기본 알고리즘으로 일정 생성
        days = []
        places_per_day = 4 if request.schedule == "packed" else 3
        
        # 장소를 타입별로 분류
        categorized = self._categorize_places(places)
        used_places = set()
        
        for day_num in range(1, request.days + 1):
            day_places = []
            
            # 시간대별 장소 배치
            time_slots = self._get_time_slots(request.schedule)
            
            for i, time_slot in enumerate(time_slots[:places_per_day]):
                # 점심 시간대는 식당
                if i == 1:
                    restaurant = self._select_unused_place(
                        categorized["food"], used_places
                    )
                    if restaurant:
                        place_rec = self._create_place_recommendation(
                            restaurant, time_slot
                        )
                        day_places.append(place_rec)
                        used_places.add(restaurant["id"])
                        continue
                
                # 다른 시간대는 관광지
                for category in ["must_visit", "cultural", "nature", "activity"]:
                    place = self._select_unused_place(
                        categorized[category], used_places
                    )
                    if place:
                        place_rec = self._create_place_recommendation(
                            place, time_slot
                        )
                        day_places.append(place_rec)
                        used_places.add(place["id"])
                        break
            
            # 숙박 추가
            if categorized["accommodation"]:
                accommodation = categorized["accommodation"][0]
                place_rec = self._create_place_recommendation(
                    accommodation, "20:00-다음날"
                )
                day_places.append(place_rec)
            
            day_itinerary = DayItinerary(
                day=day_num,
                places=day_places,
                weather={"status": "맑음", "temperature": "15-25°C"}
            )
            days.append(day_itinerary)
        
        return days
    
    def _get_time_slots(self, schedule: str) -> List[str]:
        """일정 유형별 시간대"""
        if schedule == "packed":
            return [
                "09:00-11:00",
                "11:30-13:30",
                "14:00-16:00",
                "16:30-18:30",
                "19:00-21:00"
            ]
        else:
            return [
                "10:00-12:00",
                "12:30-14:30",
                "15:00-17:00",
                "17:30-19:30"
            ]
    
    def _select_unused_place(
        self, places: List[Dict], used_places: set
    ) -> Optional[Dict]:
        """미사용 장소 선택"""
        for place in places:
            if place["id"] not in used_places:
                return place
        return None
    
    def _create_place_recommendation(
        self, place: Dict[str, Any], time_slot: str
    ) -> PlaceRecommendation:
        """PlaceRecommendation 객체 생성"""
        return PlaceRecommendation(
            id=place["id"],
            name=place["name"],
            time=time_slot,
            tags=place.get("tags", [])[:3],
            description=place.get("description", ""),
            rating=place.get("rating", 4.0),
            image=place.get("image"),
            address=place.get("address"),
            latitude=place.get("coordinates", {}).get("lat"),
            longitude=place.get("coordinates", {}).get("lng"),
        )


def get_advanced_ai_recommendation_service(db: Session) -> AdvancedAIRecommendationService:
    """고급 AI 추천 서비스 인스턴스 생성"""
    return AdvancedAIRecommendationService(db)