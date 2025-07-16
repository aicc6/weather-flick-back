import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.config import settings
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/destinations", tags=["destinations"])

GOOGLE_API_KEY = settings.google_api_key


@router.get("/search")
async def search_destination(query: str = Query(...)):
    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            params={
                "language": "ko",
                "key": GOOGLE_API_KEY,
                "input": query,
            },
        )
        data = resp.json()

        # 각 prediction에서 place_id 추출 후, Details API로 대표 사진 얻기
        suggestions = []
        for item in data.get("predictions", []):
            description = item["description"]
            place_id = item.get("place_id")
            photo_url = None
            address = None
            category = None
            latitude = None
            longitude = None
            if place_id:
                # Place Details API 호출
                details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                details_resp = await client.get(
                    details_url,
                    params={
                        "place_id": place_id,
                        "fields": "photo,formatted_address,types,name,geometry",
                        "key": GOOGLE_API_KEY,
                        "language": "ko",
                    },
                )
                details_data = details_resp.json()
                result = details_data.get("result", {})
                photos = result.get("photos", [])
                address = result.get("formatted_address")
                types = result.get("types", [])
                geometry = result.get("geometry", {})
                
                # 좌표 정보 추출
                if geometry and "location" in geometry:
                    location = geometry["location"]
                    latitude = location.get("lat")
                    longitude = location.get("lng")
                
                # 대표적인 카테고리 하나를 선택
                if types:
                    category = types[0]

                if photos:
                    # 대표 사진의 photo_reference로 실제 이미지 URL 생성
                    photo_reference = photos[0].get("photo_reference")
                    if photo_reference:
                        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_reference}&key={GOOGLE_API_KEY}"

            suggestions.append({
                "description": description,
                "place_id": place_id,
                "photo_url": photo_url,
                "address": address,
                "category": category,
                "latitude": latitude,
                "longitude": longitude,
            })
    return {"suggestions": suggestions}


@router.get("/recommend")
async def get_destination_recommendations(
    theme: str = Query(..., description="추천 테마 (예: popular, nature, culture)"),
    weather_conditions: str = Query("", description="날씨 조건 (쉼표로 구분)"),
    city: str = Query("서울", description="도시명"),
    _db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user)
):
    """
    테마와 날씨 조건을 기반으로 여행지를 추천합니다.
    """
    try:
        # 간단한 Mock 데이터로 응답 (실제 구현은 추후 확장)
        mock_recommendations = [
            {
                "id": 1,
                "name": "경복궁",
                "description": "조선 왕조의 대표적인 궁궐",
                "province": "서울",
                "tags": ["#문화", "#역사", "#궁궐"],
                "is_indoor": False,
                "recommendation_score": 95
            },
            {
                "id": 2,
                "name": "한강공원",
                "description": "서울 시민들의 휴식 공간",
                "province": "서울",
                "tags": ["#자연", "#야외", "#공원"],
                "is_indoor": False,
                "recommendation_score": 90
            },
            {
                "id": 3,
                "name": "국립중앙박물관",
                "description": "한국의 역사와 문화를 한눈에",
                "province": "서울",
                "tags": ["#문화", "#실내", "#박물관"],
                "is_indoor": True,
                "recommendation_score": 85
            }
        ]

        return {
            "recommendations": mock_recommendations,
            "theme": theme,
            "weather_conditions": weather_conditions,
            "city": city
        }

    except Exception as e:
        # 에러가 발생해도 빈 결과를 반환하여 프론트엔드가 계속 작동하도록 함
        return {
            "recommendations": [],
            "theme": theme,
            "weather_conditions": weather_conditions,
            "city": city,
            "error": str(e)
        }
