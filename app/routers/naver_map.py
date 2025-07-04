
from fastapi import APIRouter, HTTPException, Query, status

from app.services.naver_map_service import naver_map_service

router = APIRouter(prefix="/map", tags=["naver_map"])


@router.get("/search")
async def search_places(
    query: str = Query(..., description="검색할 장소명"),
    location: str | None = Query(None, description="위치 (위도,경도)"),
    category: str | None = Query(None, description="카테고리"),
    limit: int = Query(20, description="결과 개수", ge=1, le=100),
):
    """네이버 지도 API를 사용한 장소 검색"""
    places = await naver_map_service.search_places(query, location, category, limit)
    return {"places": places, "total": len(places), "query": query}


@router.get("/route")
async def get_route_guidance(
    start: str = Query(..., description="출발지"),
    goal: str = Query(..., description="목적지"),
    mode: str = Query("driving", description="이동 수단 (driving, walking, transit)"),
):
    """경로 안내"""
    route = await naver_map_service.get_route_guidance(start, goal, mode)
    return route


@router.get("/nearby")
async def get_nearby_places(
    latitude: float = Query(..., description="위도"),
    longitude: float = Query(..., description="경도"),
    radius: float = Query(1000, description="반경 (미터)", ge=100, le=10000),
    category: str | None = Query(None, description="카테고리"),
):
    """주변 장소 검색"""
    places = await naver_map_service.get_nearby_places(
        latitude, longitude, radius, category
    )
    return {
        "places": places,
        "total": len(places),
        "center": {"latitude": latitude, "longitude": longitude},
        "radius": radius,
    }


@router.get("/restaurants/nearby")
async def get_nearby_restaurants(
    latitude: float = Query(..., description="위도"),
    longitude: float = Query(..., description="경도"),
    radius: float = Query(1000, description="반경 (미터)", ge=100, le=10000),
):
    """주변 맛집 검색"""
    restaurants = await naver_map_service.search_restaurants_nearby(
        latitude, longitude, radius
    )
    return {
        "restaurants": restaurants,
        "total": len(restaurants),
        "center": {"latitude": latitude, "longitude": longitude},
        "radius": radius,
    }


@router.get("/hotels/nearby")
async def get_nearby_hotels(
    latitude: float = Query(..., description="위도"),
    longitude: float = Query(..., description="경도"),
    radius: float = Query(1000, description="반경 (미터)", ge=100, le=10000),
):
    """주변 숙소 검색"""
    hotels = await naver_map_service.search_hotels_nearby(latitude, longitude, radius)
    return {
        "hotels": hotels,
        "total": len(hotels),
        "center": {"latitude": latitude, "longitude": longitude},
        "radius": radius,
    }


@router.get("/transportation/nearby")
async def get_nearby_transportation(
    latitude: float = Query(..., description="위도"),
    longitude: float = Query(..., description="경도"),
    radius: float = Query(1000, description="반경 (미터)", ge=100, le=10000),
):
    """주변 교통 정보 검색"""
    transportation = await naver_map_service.search_transportation_nearby(
        latitude, longitude, radius
    )
    return {
        "transportation": transportation,
        "total": len(transportation),
        "center": {"latitude": latitude, "longitude": longitude},
        "radius": radius,
    }


@router.get("/coordinates/{city}")
async def get_city_coordinates(city: str):
    """도시의 좌표 정보 조회"""
    coordinates = await naver_map_service.get_city_coordinates(city)
    if not coordinates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coordinates for city '{city}' not found",
        )
    return coordinates


@router.get("/embed")
async def get_map_embed_url(
    latitude: float = Query(..., description="위도"),
    longitude: float = Query(..., description="경도"),
    zoom: int = Query(15, description="줌 레벨", ge=1, le=20),
    width: int = Query(600, description="지도 너비", ge=200, le=1200),
    height: int = Query(400, description="지도 높이", ge=200, le=800),
):
    """네이버 지도 임베드 URL 생성"""
    embed_url = await naver_map_service.get_map_embed_url(
        latitude, longitude, zoom, width, height
    )
    return {
        "embed_url": embed_url,
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "zoom": zoom,
        "size": {"width": width, "height": height},
    }


@router.get("/static")
async def get_static_map_url(
    latitude: float = Query(..., description="위도"),
    longitude: float = Query(..., description="경도"),
    zoom: int = Query(15, description="줌 레벨", ge=1, le=20),
    width: int = Query(600, description="지도 너비", ge=200, le=1200),
    height: int = Query(400, description="지도 높이", ge=200, le=800),
):
    """정적 지도 이미지 URL 생성"""
    static_url = await naver_map_service.get_static_map_url(
        latitude, longitude, zoom, width, height
    )
    return {
        "static_url": static_url,
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "zoom": zoom,
        "size": {"width": width, "height": height},
    }


@router.get("/widget")
async def get_map_widget_html(
    latitude: float = Query(..., description="위도"),
    longitude: float = Query(..., description="경도"),
    zoom: int = Query(15, description="줌 레벨", ge=1, le=20),
    width: int = Query(600, description="지도 너비", ge=200, le=1200),
    height: int = Query(400, description="지도 높이", ge=200, le=800),
):
    """네이버 지도 위젯 HTML 생성"""
    widget_html = await naver_map_service.get_map_widget_html(
        latitude, longitude, zoom, width, height
    )
    return {
        "html": widget_html,
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "zoom": zoom,
        "size": {"width": width, "height": height},
    }


@router.get("/place/{place_id}")
async def get_place_details(place_id: str):
    """장소 상세 정보 조회"""
    details = await naver_map_service.get_place_details(place_id)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Place details not found"
        )
    return details


@router.get("/search/coordinates")
async def search_with_coordinates(
    latitude: float = Query(..., description="위도"),
    longitude: float = Query(..., description="경도"),
    query: str = Query(..., description="검색할 장소명"),
    limit: int = Query(20, description="결과 개수", ge=1, le=100),
):
    """좌표 기반 장소 검색"""
    places = await naver_map_service.search_with_coordinates(
        latitude, longitude, query, limit
    )
    return {
        "places": places,
        "total": len(places),
        "query": query,
        "coordinates": {"latitude": latitude, "longitude": longitude},
    }


@router.get("/cities")
async def get_supported_cities():
    """지원되는 도시 목록"""
    cities = [
        "서울",
        "부산",
        "대구",
        "인천",
        "광주",
        "대전",
        "울산",
        "세종",
        "수원",
        "고양",
        "용인",
        "창원",
        "포항",
        "제주",
    ]
    return {"cities": cities}


@router.get("/categories")
async def get_search_categories():
    """검색 카테고리 목록"""
    categories = [
        "맛집",
        "카페",
        "호텔",
        "펜션",
        "게스트하우스",
        "모텔",
        "리조트",
        "지하철역",
        "버스정류장",
        "공항",
        "기차역",
        "관광지",
        "쇼핑몰",
        "병원",
        "약국",
        "은행",
        "편의점",
        "주유소",
        "주차장",
    ]
    return {"categories": categories}
