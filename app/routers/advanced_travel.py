"""
고급 AI 기반 여행 추천 라우터
- 사용자 페르소나 기반 추천
- 피드백 학습 시스템
- 고급 프롬프트 엔지니어링
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import (
    User,
    CustomTravelRecommendationRequest,
    CustomTravelRecommendationResponse,
    DayItinerary,
)
from app.auth import get_current_user
from app.services.advanced_ai_recommendation import (
    get_advanced_ai_recommendation_service,
    PersonaType
)
from app.services.feedback_learning import (
    get_feedback_learning_service,
    FeedbackType
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/advanced-travel",
    tags=["advanced-travel"],
)


# Pydantic 모델들
class AdvancedTravelRequest(BaseModel):
    """고급 여행 추천 요청"""
    region_code: str = Field(..., description="지역 코드")
    region_name: str = Field(..., description="지역명")
    days: int = Field(..., ge=1, le=7, description="여행 일수")
    who: str = Field(..., description="동행자 유형")
    styles: List[str] = Field(..., description="여행 스타일")
    schedule: str = Field(..., description="일정 강도 (packed/relaxed)")
    transportation: Optional[str] = Field(None, description="교통수단")
    budget: Optional[int] = Field(None, description="예산")
    special_requirements: Optional[List[str]] = Field(None, description="특별 요구사항")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="대화 기록")
    use_advanced_ai: bool = Field(True, description="고급 AI 사용 여부")


class PlaceFeedbackRequest(BaseModel):
    """장소별 피드백"""
    place_id: str
    place_name: str
    visited: bool = True
    rating: Optional[int] = Field(None, ge=1, le=5)
    actual_duration: Optional[int] = Field(None, description="실제 체류 시간(분)")
    recommended_duration: int
    comments: Optional[str] = None
    tags: List[str] = []


class RouteFeedbackRequest(BaseModel):
    """동선 피드백"""
    day: int
    efficiency_rating: int = Field(..., ge=1, le=5)
    total_distance: float
    walking_time: int
    transport_issues: List[str] = []
    suggestions: List[str] = []


class TravelFeedbackRequest(BaseModel):
    """여행 피드백 요청"""
    travel_plan_id: int
    overall_rating: int = Field(..., ge=1, le=5)
    places: List[PlaceFeedbackRequest]
    routes: List[RouteFeedbackRequest]
    timing_satisfaction: int = Field(..., ge=1, le=5)
    weather_adaptation: int = Field(..., ge=1, le=5)
    would_recommend: bool = True
    highlights: List[str] = []
    improvements: List[str] = []
    additional_comments: Optional[str] = None


class UserInsightsResponse(BaseModel):
    """사용자 인사이트 응답"""
    preference_trends: Dict[str, float]
    timing_preferences: Dict[str, Any]
    route_preferences: Dict[str, Any]
    favorite_places: List[Dict[str, Any]]
    avoid_places: List[Dict[str, Any]]
    persona_type: Optional[str]
    travel_style_summary: str


class PersonaAnalysisResponse(BaseModel):
    """페르소나 분석 응답"""
    primary_persona: str
    secondary_persona: Optional[str]
    characteristics: List[str]
    preferences: Dict[str, float]
    travel_pace: str
    budget_level: str
    recommended_styles: List[str]


@router.post("/recommendations", response_model=CustomTravelRecommendationResponse)
async def get_advanced_recommendations(
    request: AdvancedTravelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    고급 AI 기반 맞춤형 여행 일정 추천
    
    - 사용자 페르소나 분석
    - Chain of Thought 추론
    - 이동 시간 최적화
    - 날씨 기반 조정
    - 대화 컨텍스트 활용
    """
    try:
        # 기본 요청 모델로 변환
        base_request = CustomTravelRecommendationRequest(
            region_code=request.region_code,
            region_name=request.region_name,
            days=request.days,
            who=request.who,
            styles=request.styles,
            schedule=request.schedule,
            transportation=request.transportation
        )
        
        # 장소 데이터 조회 (기존 로직 재사용)
        from app.routers.custom_travel import get_places_data
        places = await get_places_data(db, request.region_code)
        
        if not places:
            raise HTTPException(status_code=404, detail="해당 지역에 대한 여행지 정보를 찾을 수 없습니다.")
        
        # 고급 AI 서비스 사용
        if request.use_advanced_ai:
            ai_service = get_advanced_ai_recommendation_service(db)
            itinerary = await ai_service.generate_advanced_itinerary(
                user=current_user,
                request=base_request,
                places=places,
                conversation_history=request.conversation_history
            )
        else:
            # 기존 서비스 사용 (폴백)
            from app.services.enhanced_ai_recommendation import get_enhanced_ai_recommendation_service
            ai_service = get_enhanced_ai_recommendation_service(db)
            itinerary = await ai_service.generate_travel_itinerary(base_request, places)
        
        # 응답 생성
        response = CustomTravelRecommendationResponse(
            itinerary=itinerary,
            total_days=request.days,
            region_name=request.region_name,
            travel_style=request.styles,
            generated_at=datetime.now().isoformat()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"고급 AI 추천 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류가 발생했습니다: {str(e)}")


@router.post("/feedback")
async def submit_travel_feedback(
    feedback: TravelFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    여행 후 피드백 제출
    
    피드백을 통해 AI 추천 품질을 지속적으로 개선합니다.
    """
    try:
        feedback_service = get_feedback_learning_service(db)
        
        # 피드백 데이터 변환
        feedback_data = {
            "overall_rating": feedback.overall_rating,
            "places": [place.dict() for place in feedback.places],
            "routes": [route.dict() for route in feedback.routes],
            "timing_satisfaction": feedback.timing_satisfaction,
            "weather_adaptation": feedback.weather_adaptation,
            "would_recommend": feedback.would_recommend,
            "highlights": feedback.highlights,
            "improvements": feedback.improvements,
            "additional_comments": feedback.additional_comments
        }
        
        # 피드백 수집 및 학습
        result = await feedback_service.collect_feedback(
            user_id=current_user.id,
            travel_plan_id=feedback.travel_plan_id,
            feedback_data=feedback_data
        )
        
        return {
            "status": "success",
            "message": "피드백이 성공적으로 제출되었습니다.",
            "feedback_id": result.travel_plan_id
        }
        
    except Exception as e:
        logger.error(f"피드백 제출 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"피드백 제출 중 오류가 발생했습니다: {str(e)}")


@router.get("/insights", response_model=UserInsightsResponse)
async def get_user_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    사용자별 여행 인사이트 조회
    
    과거 여행 피드백을 기반으로 개인화된 인사이트를 제공합니다.
    """
    try:
        feedback_service = get_feedback_learning_service(db)
        insights = await feedback_service.get_user_insights(current_user.id)
        
        # 페르소나 분석 (간단한 버전)
        ai_service = get_advanced_ai_recommendation_service(db)
        
        # 더미 요청으로 페르소나 분석
        dummy_request = CustomTravelRecommendationRequest(
            region_code="11",
            region_name="서울",
            days=2,
            who="solo",
            styles=["culture"],
            schedule="relaxed"
        )
        
        persona = await ai_service._analyze_user_persona(current_user, dummy_request)
        
        return UserInsightsResponse(
            preference_trends=insights.get("preference_trends", {}),
            timing_preferences=insights.get("timing_preferences", {}),
            route_preferences=insights.get("route_preferences", {}),
            favorite_places=insights.get("favorite_places", []),
            avoid_places=insights.get("avoid_places", []),
            persona_type=persona.primary_type.value if persona else None,
            travel_style_summary=_generate_travel_style_summary(insights, persona)
        )
        
    except Exception as e:
        logger.error(f"인사이트 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"인사이트 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/persona-analysis", response_model=PersonaAnalysisResponse)
async def analyze_user_persona(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    사용자 페르소나 분석
    
    여행 기록과 선호도를 바탕으로 사용자의 여행 페르소나를 분석합니다.
    """
    try:
        ai_service = get_advanced_ai_recommendation_service(db)
        
        # 더미 요청으로 페르소나 분석
        dummy_request = CustomTravelRecommendationRequest(
            region_code="11",
            region_name="서울",
            days=2,
            who="solo",
            styles=["culture"],
            schedule="relaxed"
        )
        
        persona = await ai_service._analyze_user_persona(current_user, dummy_request)
        
        # 페르소나에 따른 추천 스타일
        style_recommendations = {
            PersonaType.ADVENTURER: ["activity", "nature", "landmark"],
            PersonaType.CULTURAL: ["culture", "landmark", "local"],
            PersonaType.FOODIE: ["food", "local", "hotplace"],
            PersonaType.RELAXER: ["healing", "nature", "culture"],
            PersonaType.SHOPPER: ["shopping", "hotplace", "food"],
            PersonaType.FAMILY: ["landmark", "activity", "food"],
            PersonaType.BUDGET: ["local", "nature", "culture"],
            PersonaType.LUXURY: ["healing", "food", "shopping"]
        }
        
        characteristics = _get_persona_characteristics(persona.primary_type)
        
        return PersonaAnalysisResponse(
            primary_persona=persona.primary_type.value,
            secondary_persona=persona.secondary_type.value if persona.secondary_type else None,
            characteristics=characteristics,
            preferences=persona.preferences,
            travel_pace=persona.travel_pace,
            budget_level=persona.budget_level,
            recommended_styles=style_recommendations.get(persona.primary_type, [])
        )
        
    except Exception as e:
        logger.error(f"페르소나 분석 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"페르소나 분석 중 오류가 발생했습니다: {str(e)}")


@router.get("/place-recommendations")
async def get_personalized_place_recommendations(
    place_type: str = Query(..., description="장소 타입 (food/cultural/nature/shopping/activity)"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    개인화된 장소 추천
    
    사용자의 페르소나와 과거 피드백을 기반으로 장소를 추천합니다.
    """
    try:
        # 사용자 페르소나 분석
        ai_service = get_advanced_ai_recommendation_service(db)
        dummy_request = CustomTravelRecommendationRequest(
            region_code="11",
            region_name="서울",
            days=2,
            who="solo",
            styles=["culture"],
            schedule="relaxed"
        )
        persona = await ai_service._analyze_user_persona(current_user, dummy_request)
        
        # 피드백 기반 장소 추천
        feedback_service = get_feedback_learning_service(db)
        recommendations = await feedback_service.get_place_recommendations(
            place_type=place_type,
            persona_type=persona.primary_type.value
        )
        
        return {
            "recommendations": recommendations[:limit],
            "persona_type": persona.primary_type.value,
            "total_found": len(recommendations)
        }
        
    except Exception as e:
        logger.error(f"장소 추천 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"장소 추천 중 오류가 발생했습니다: {str(e)}")


def _generate_travel_style_summary(insights: Dict[str, Any], persona) -> str:
    """사용자의 여행 스타일 요약 생성"""
    summary_parts = []
    
    # 선호도 기반 요약
    preferences = insights.get("preference_trends", {})
    if preferences:
        top_preference = max(preferences.items(), key=lambda x: x[1])[0]
        summary_parts.append(f"{top_preference}을(를) 가장 선호하시는")
    
    # 페르소나 기반 요약
    if persona:
        persona_descriptions = {
            PersonaType.ADVENTURER: "모험을 즐기는",
            PersonaType.CULTURAL: "문화와 역사를 사랑하는",
            PersonaType.FOODIE: "미식을 추구하는",
            PersonaType.RELAXER: "휴식을 중시하는",
            PersonaType.SHOPPER: "쇼핑을 좋아하는",
            PersonaType.FAMILY: "가족과 함께하는",
            PersonaType.BUDGET: "알뜰한",
            PersonaType.LUXURY: "럭셔리를 추구하는"
        }
        summary_parts.append(persona_descriptions.get(persona.primary_type, ""))
    
    summary_parts.append("여행자이십니다.")
    
    return " ".join(summary_parts)


def _get_persona_characteristics(persona_type: PersonaType) -> List[str]:
    """페르소나별 특성 반환"""
    characteristics_map = {
        PersonaType.ADVENTURER: [
            "새로운 경험을 추구합니다",
            "액티비티와 스포츠를 즐깁니다",
            "도전적인 활동을 선호합니다",
            "자연과 야외 활동을 좋아합니다"
        ],
        PersonaType.CULTURAL: [
            "역사와 문화에 깊은 관심이 있습니다",
            "박물관과 전시를 즐겨 방문합니다",
            "현지 문화 체험을 중요시합니다",
            "교육적 가치가 있는 여행을 선호합니다"
        ],
        PersonaType.FOODIE: [
            "맛집 탐방을 가장 중요하게 생각합니다",
            "현지 특산물과 전통 음식에 관심이 많습니다",
            "새로운 맛과 요리를 시도하는 것을 좋아합니다",
            "식사 시간을 충분히 확보합니다"
        ],
        PersonaType.RELAXER: [
            "여유로운 일정을 선호합니다",
            "휴식과 힐링을 최우선으로 합니다",
            "조용하고 평화로운 장소를 좋아합니다",
            "스파와 온천 등 웰니스 활동을 즐깁니다"
        ],
        PersonaType.SHOPPER: [
            "쇼핑을 여행의 주요 목적으로 삼습니다",
            "현지 특산품과 기념품에 관심이 많습니다",
            "백화점, 아울렛, 전통시장을 즐겨 방문합니다",
            "최신 트렌드와 브랜드에 민감합니다"
        ],
        PersonaType.FAMILY: [
            "가족 구성원 모두가 즐길 수 있는 활동을 선호합니다",
            "안전과 편의성을 최우선으로 고려합니다",
            "교육적 가치가 있는 체험을 중시합니다",
            "아이들이 즐길 수 있는 시설을 찾습니다"
        ],
        PersonaType.BUDGET: [
            "가성비 높은 여행을 추구합니다",
            "무료 관광지와 할인 정보에 관심이 많습니다",
            "대중교통 이용을 선호합니다",
            "현지인이 가는 저렴한 맛집을 찾습니다"
        ],
        PersonaType.LUXURY: [
            "최고급 서비스와 시설을 선호합니다",
            "편안함과 프라이버시를 중시합니다",
            "미슐랭 레스토랑 등 고급 다이닝을 즐깁니다",
            "특별한 경험과 VIP 서비스를 추구합니다"
        ]
    }
    
    return characteristics_map.get(persona_type, [])


# 헬퍼 함수: custom_travel.py에서 재사용
async def get_places_data(db: Session, region_code: str) -> List[Dict[str, Any]]:
    """지역별 장소 데이터 조회 (custom_travel.py의 로직 재사용)"""
    from app.routers.custom_travel import (
        get_category_name,
        TouristAttraction,
        CulturalFacility,
        Restaurant,
        Shopping,
        Accommodation,
        Region
    )
    
    # region_code를 tour_api_area_code로 매핑
    region = db.query(Region).filter(Region.region_code == region_code).first()
    if region and region.tour_api_area_code:
        db_region_code = region.tour_api_area_code
    else:
        # 하드코딩된 매핑 사용
        region_code_mapping = {
            "11": "1", "26": "6", "27": "4", "28": "2",
            "29": "5", "30": "3", "31": "7", "36": "8",
            "41": "31", "43": "33", "44": "34", "46": "36",
            "47": "35", "48": "38", "50": "39", "51": "32", "52": "37"
        }
        db_region_code = region_code_mapping.get(region_code, region_code)
    
    # 장소 데이터 조회
    places = []
    
    # 관광지
    attractions = db.query(TouristAttraction).filter(
        TouristAttraction.region_code == db_region_code
    ).limit(200).all()
    
    for attr in attractions:
        places.append({
            "id": f"attr_{attr.id}",
            "name": attr.name,
            "type": "attraction",
            "description": attr.description,
            "address": attr.address,
            "latitude": attr.latitude,
            "longitude": attr.longitude,
            "tags": _extract_tags(attr, db),
            "rating": 4.2,
            "image": attr.image_url
        })
    
    # 문화시설
    cultural = db.query(CulturalFacility).filter(
        CulturalFacility.region_code == db_region_code
    ).limit(100).all()
    
    for cult in cultural:
        places.append({
            "id": f"cult_{cult.id}",
            "name": cult.name,
            "type": "cultural",
            "description": cult.description,
            "address": cult.address,
            "latitude": cult.latitude,
            "longitude": cult.longitude,
            "tags": _extract_tags(cult, db),
            "rating": 4.3,
            "image": cult.image_url
        })
    
    # 음식점
    restaurants = db.query(Restaurant).filter(
        Restaurant.region_code == db_region_code
    ).limit(100).all()
    
    for rest in restaurants:
        places.append({
            "id": f"rest_{rest.id}",
            "name": rest.name,
            "type": "restaurant",
            "description": rest.description,
            "address": rest.address,
            "latitude": rest.latitude,
            "longitude": rest.longitude,
            "tags": _extract_tags(rest, db),
            "rating": 4.1,
            "image": rest.image_url
        })
    
    return places


def _extract_tags(place, db) -> List[str]:
    """장소에서 태그 추출"""
    tags = []
    
    # 카테고리 코드에서 태그 추출
    if hasattr(place, 'category_code') and place.category_code:
        from app.routers.custom_travel import get_category_name
        category_name = get_category_name(place.category_code, db)
        if category_name:
            tags.append(category_name)
    
    # 설명에서 키워드 추출
    if hasattr(place, 'description') and place.description:
        keywords = ["문화", "역사", "자연", "체험", "전통", "현대", "휴식"]
        for keyword in keywords:
            if keyword in place.description:
                tags.append(keyword)
    
    return tags[:5]  # 최대 5개 태그