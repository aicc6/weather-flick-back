"""개인화된 추천 라우터"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.services.user_behavior_service import get_user_behavior_service
from app.services.ai_recommendation import AIRecommendationService
from app.services.recommendation_service import get_weather_based_recommendations

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/personalized",
    tags=["personalized-recommendations"],
)


@router.get("/profile")
async def get_user_preference_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 선호도 프로필 조회"""
    
    behavior_service = get_user_behavior_service(db)
    profile = await behavior_service.get_user_preferences_profile(current_user.user_id)
    
    return {
        "status": "success",
        "data": profile
    }


@router.get("/recommendations")
async def get_personalized_recommendations(
    weather: Optional[str] = Query(None, description="현재 날씨 상태"),
    city: Optional[str] = Query(None, description="현재 도시"),
    hour: Optional[int] = Query(None, description="현재 시간 (0-23)"),
    season: Optional[str] = Query(None, description="현재 계절"),
    limit: int = Query(20, description="추천 결과 개수"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """개인화된 추천 결과 제공"""
    
    behavior_service = get_user_behavior_service(db)
    
    # 컨텍스트 정보 구성
    context = {
        "weather": weather,
        "city": city,
        "hour": hour or datetime.now().hour,
        "season": season or _get_current_season()
    }
    
    # 개인화된 추천 생성
    recommendations = await behavior_service.get_personalized_recommendations(
        user_id=current_user.user_id,
        context=context
    )
    
    # 날씨 기반 추천과 병합 (weather가 제공된 경우)
    if weather and city:
        weather_recommendations = await get_weather_based_recommendations(
            db, weather, city, current_user
        )
        
        # 중복 제거 및 병합
        existing_ids = {rec["id"] for rec in recommendations}
        for rec in weather_recommendations:
            if rec["id"] not in existing_ids:
                recommendations.append(rec)
    
    # 결과 제한
    recommendations = recommendations[:limit]
    
    # 추천 결과 조회 추적
    await behavior_service.track_user_activity(
        user_id=current_user.user_id,
        activity_type="recommendation_viewed",
        activity_data={
            "recommendation_count": len(recommendations),
            "context": context
        }
    )
    
    return {
        "status": "success",
        "data": {
            "recommendations": recommendations,
            "context": context,
            "total_count": len(recommendations)
        }
    }


@router.post("/feedback")
async def submit_recommendation_feedback(
    destination_id: str,
    feedback_type: str = Query(..., description="clicked, ignored, disliked"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """추천 결과에 대한 피드백 제출"""
    
    behavior_service = get_user_behavior_service(db)
    
    # 피드백 추적
    await behavior_service.track_user_activity(
        user_id=current_user.user_id,
        activity_type=f"recommendation_{feedback_type}",
        activity_data={
            "destination_id": destination_id,
            "timestamp": datetime.now().isoformat()
        }
    )
    
    return {
        "status": "success",
        "message": "Feedback recorded successfully"
    }


@router.get("/session-based")
async def get_session_based_recommendations(
    session_id: str,
    limit: int = Query(10, description="추천 결과 개수"),
    db: Session = Depends(get_db)
):
    """세션 기반 실시간 추천 (로그인하지 않은 사용자용)"""
    
    # 세션 기반 활동 조회
    from app.models import UserActivityLog
    
    recent_activities = db.query(UserActivityLog).filter(
        UserActivityLog.session_id == session_id
    ).order_by(UserActivityLog.created_at.desc()).limit(20).all()
    
    if not recent_activities:
        return {
            "status": "success",
            "data": {
                "recommendations": [],
                "message": "No session history found"
            }
        }
    
    # 최근 조회한 여행지 태그 수집
    viewed_tags = {}
    for activity in recent_activities:
        if activity.activity_type == "destination_view":
            dest_id = activity.activity_data.get("destination_id")
            if dest_id:
                # 여행지 정보 조회
                behavior_service = get_user_behavior_service(db)
                tags = behavior_service._get_destination_tags(dest_id)
                for tag in tags:
                    viewed_tags[tag] = viewed_tags.get(tag, 0) + 1
    
    # 태그 기반 추천 생성
    recommendations = []
    if viewed_tags:
        # 가장 많이 본 태그 상위 5개
        top_tags = sorted(viewed_tags.items(), key=lambda x: x[1], reverse=True)[:5]
        top_tag_names = [tag for tag, _ in top_tags]
        
        # 해당 태그를 가진 여행지 추천
        from app.services.destination_service import destination_service
        destinations = destination_service.get_destinations_by_tags(db, top_tag_names)
        
        for dest in destinations[:limit]:
            recommendations.append({
                "id": dest.id,
                "name": dest.name,
                "description": dest.description,
                "tags": dest.tags,
                "type": "session_based",
                "score": sum(viewed_tags.get(tag, 0) for tag in dest.tags)
            })
        
        # 점수 기준 정렬
        recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "status": "success",
        "data": {
            "recommendations": recommendations[:limit],
            "session_tags": dict(viewed_tags),
            "total_count": len(recommendations)
        }
    }


@router.get("/explore")
async def get_exploration_recommendations(
    exploration_level: float = Query(0.3, description="탐색 수준 (0.0-1.0)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새로운 경험을 위한 탐색적 추천"""
    
    behavior_service = get_user_behavior_service(db)
    
    # 사용자가 방문하지 않은 카테고리/지역 찾기
    user_profile = await behavior_service.get_user_preferences_profile(current_user.user_id)
    
    # 기존 선호도와 반대되는 추천 생성
    implicit_prefs = user_profile.get("implicit_preferences", {})
    liked_tags = implicit_prefs.get("liked_tags", {})
    
    # 적게 본 태그나 새로운 태그 찾기
    all_tags = ["#모험", "#문화", "#음식", "#쇼핑", "#휴식", "#액티비티", "#자연", "#도시"]
    unexplored_tags = [tag for tag in all_tags if tag not in liked_tags or liked_tags.get(tag, 0) < 2]
    
    # 새로운 태그 기반 추천
    from app.services.destination_service import destination_service
    recommendations = []
    
    for tag in unexplored_tags[:3]:  # 상위 3개 새로운 카테고리
        destinations = destination_service.get_destinations_by_tags(db, [tag])
        for dest in destinations[:5]:  # 각 카테고리에서 5개씩
            recommendations.append({
                "id": dest.id,
                "name": dest.name,
                "description": dest.description,
                "tags": dest.tags,
                "type": "exploration",
                "exploration_reason": f"새로운 경험: {tag}"
            })
    
    # 무작위 섞기
    import random
    random.shuffle(recommendations)
    
    # 탐색 수준에 따라 결과 조정
    result_count = int(20 * exploration_level)
    
    return {
        "status": "success",
        "data": {
            "recommendations": recommendations[:result_count],
            "exploration_level": exploration_level,
            "unexplored_categories": unexplored_tags
        }
    }


@router.post("/preferences/update")
async def update_user_preferences(
    preferences: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 선호도 직접 업데이트"""
    
    # 기존 preferences와 병합
    current_prefs = current_user.preferences or {}
    
    # 명시적 선호도 업데이트
    if "tags" in preferences:
        current_prefs["tags"] = preferences["tags"]
    
    if "regions" in preferences:
        current_prefs["regions"] = preferences["regions"]
    
    if "themes" in preferences:
        current_prefs["themes"] = preferences["themes"]
    
    # 업데이트 시간 기록
    current_prefs["last_manual_update"] = datetime.now().isoformat()
    
    # 저장
    current_user.preferences = current_prefs
    if "preferred_region" in preferences:
        current_user.preferred_region = preferences["preferred_region"]
    if "preferred_theme" in preferences:
        current_user.preferred_theme = preferences["preferred_theme"]
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Preferences updated successfully",
        "data": current_prefs
    }


def _get_current_season() -> str:
    """현재 계절 반환"""
    month = datetime.now().month
    if month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    elif month in [9, 10, 11]:
        return "autumn"
    else:
        return "winter"