from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import User
from app.services.destination_service import get_destinations_by_tags
from app.services.tour_api_service import get_festivals_from_tour_api
from app.utils.kma_utils import get_area_code_for_city

# 날씨 상태와 관련 태그 매핑
weather_to_tags_map = {
    "맑음": ["#야외", "#활동적인", "#공원", "#산책", "#자연"],
    "구름많음": ["#실내", "#문화", "#전시", "#카페", "#쇼핑"],
    "흐림": ["#실내", "#문화", "#전시", "#카페", "#쇼핑"],
    "비": ["#실내", "#아늑한", "#전시", "#박물관", "#카페"],
    "비/눈": ["#실내", "#아늑한", "#전시", "#박물관", "#카페"],
    "눈": ["#실내", "#겨울", "#아늑한", "#전시", "#카페"],
    "소나기": ["#실내", "#급할때", "#쇼핑", "#카페"],
}


async def get_weather_based_recommendations(
    db: Session, weather_status: str, city: str, user: User
) -> List[Dict[str, Any]]:
    """
    날씨, 도시, 사용자 선호도를 기반으로 여행지를 추천합니다.
    '맑은 날'에는 현재 진행중인 축제 정보를 추가로 추천합니다.
    """
    # 1. 날씨 상태에 따라 추천 태그 목록 생성
    recommended_tags = weather_to_tags_map.get(weather_status, [])
    if not recommended_tags:
        return []

    # 2. 날씨가 "맑음"일 경우, 현재 진행중인 축제/이벤트 정보 추가
    events_recommendations = []
    if weather_status == "맑음":
        area_code = get_area_code_for_city(city)
        if area_code:
            today_str = datetime.now().strftime('%Y%m%d')
            try:
                festivals = await get_festivals_from_tour_api(area_code=area_code, event_start_date=today_str)
                for festival in festivals:
                    events_recommendations.append({
                        "id": festival.get("contentid"),
                        "name": f"[축제] {festival.get('title')}",
                        "description": festival.get("addr1"),
                        "province": city,
                        "tags": ["#축제", "#이벤트", "#야외"],
                        "is_indoor": False,
                        "recommendation_score": 100,
                    })
            except Exception as e:
                print(f"Error fetching festival data: {e}")

    # 3. 태그에 맞는 여행지 조회
    destinations = get_destinations_by_tags(db, recommended_tags)

    # 4. 개인화 점수 계산
    user_preferences = set(user.preferences.get("tags", [])) if user.preferences else set()
    recommended_destinations = []
    for dest in destinations:
        dest_tags = set(dest.tags)

        weather_score = len(set(recommended_tags).intersection(dest_tags))
        personalization_score = len(user_preferences.intersection(dest_tags)) * 2
        total_score = weather_score + personalization_score

        if total_score > 0:
            recommended_destinations.append({
                "id": dest.id,
                "name": dest.name,
                "description": dest.description,
                "province": dest.province,
                "tags": dest.tags,
                "is_indoor": dest.is_indoor,
                "recommendation_score": total_score,
            })

    # 5. 최종 추천 목록 생성 및 정렬
    final_recommendations = sorted(
        events_recommendations + recommended_destinations,
        key=lambda x: x["recommendation_score"],
        reverse=True
    )

    return final_recommendations
