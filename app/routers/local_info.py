from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.models import (
    ReviewCreate,
    SearchRequest,
    SearchResult,
    User,
)
from app.services.local_info_service import local_info_service

router = APIRouter(prefix="/local", tags=["local_info"])


@router.get("/cities")
async def get_supported_cities():
    """지원되는 도시 목록 조회"""
    cities = await local_info_service.get_supported_cities()
    return {"cities": cities}


@router.get("/cities/{city}/info")
async def get_city_info(city: str):
    """도시 정보 조회"""
    city_info = await local_info_service.get_city_info(city)
    if not city_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"City '{city}' not found"
        )
    return city_info


@router.get("/restaurants")
async def search_restaurants(
    city: str = Query(..., description="도시명"),
    region: str | None = Query(None, description="지역명"),
    category: str | None = Query(
        None, description="음식 카테고리 (한식, 중식, 일식, 양식, 카페, 기타)"
    ),
    keyword: str | None = Query(None, description="검색 키워드"),
    limit: int = Query(20, description="결과 개수", ge=1, le=100),
    db: Session = Depends(get_db),
):
    """맛집 검색"""
    restaurants = await local_info_service.search_restaurants(
        city=city, region=region, category=category, keyword=keyword, limit=limit, db=db
    )
    return {"restaurants": restaurants, "total": len(restaurants)}


@router.get("/transportation")
async def search_transportation(
    city: str = Query(..., description="도시명"),
    region: str | None = Query(None, description="지역명"),
    transport_type: str | None = Query(
        None, description="교통 수단 타입 (지하철, 버스, 택시, 기차, 공항)"
    ),
    limit: int = Query(20, description="결과 개수", ge=1, le=100),
):
    """교통 정보 검색"""
    transportations = await local_info_service.search_transportation(
        city=city, region=region, transport_type=transport_type, limit=limit
    )
    return {"transportations": transportations, "total": len(transportations)}


@router.get("/accommodations")
async def search_accommodations(
    city: str = Query(..., description="도시명"),
    region: str | None = Query(None, description="지역명"),
    accommodation_type: str | None = Query(
        None, description="숙소 타입 (호텔, 펜션, 게스트하우스, 모텔, 리조트)"
    ),
    limit: int = Query(20, description="결과 개수", ge=1, le=100),
):
    """숙소 정보 검색"""
    accommodations = await local_info_service.search_accommodations(
        city=city, region=region, accommodation_type=accommodation_type, limit=limit
    )
    return {"accommodations": accommodations, "total": len(accommodations)}


@router.post("/search")
async def search_all(
    search_request: SearchRequest, current_user: User = Depends(get_current_active_user)
):
    """통합 검색 (인증 필요)"""
    results = SearchResult()

    # 도시 정보
    city_info = await local_info_service.get_city_info(search_request.city)
    if city_info:
        results.city_info = city_info

    # 맛집 검색
    if not search_request.category or search_request.category == "restaurant":
        restaurants = await local_info_service.search_restaurants(
            city=search_request.city, keyword=search_request.keyword, limit=10
        )
        results.restaurants = restaurants

    # 교통 정보 검색
    if not search_request.category or search_request.category == "transportation":
        transportations = await local_info_service.search_transportation(
            city=search_request.city, limit=10
        )
        results.transportations = transportations

    # 숙소 검색
    if not search_request.category or search_request.category == "accommodation":
        accommodations = await local_info_service.search_accommodations(
            city=search_request.city, limit=10
        )
        results.accommodations = accommodations

    return results


@router.get("/favorites")
async def get_user_favorites(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """사용자 즐겨찾기 조회 (인증 필요)"""
    from app.models import FavoritePlace

    favorites = (
        db.query(FavoritePlace).filter(FavoritePlace.user_id == current_user.id).all()
    )

    return [
        {
            "id": fav.id,
            "place_id": fav.place_id,
            "place_type": fav.place_type,
            "city": fav.city,
            "added_at": fav.added_at,
        }
        for fav in favorites
    ]


@router.post("/favorites/{place_type}/{place_id}")
async def add_favorite(
    place_type: str,
    place_id: int,
    city: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """즐겨찾기 추가 (인증 필요)"""
    from app.models import FavoritePlace

    # 중복 확인
    existing = (
        db.query(FavoritePlace)
        .filter(
            FavoritePlace.user_id == current_user.id,
            FavoritePlace.place_id == place_id,
            FavoritePlace.place_type == place_type,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Already in favorites"
        )

    # 새 즐겨찾기 추가
    favorite = FavoritePlace(
        user_id=current_user.id, place_id=place_id, place_type=place_type, city=city
    )

    db.add(favorite)
    db.commit()
    db.refresh(favorite)

    return {"message": "Added to favorites", "favorite_id": favorite.id}


@router.delete("/favorites/{place_type}/{place_id}")
async def remove_favorite(
    place_type: str,
    place_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """즐겨찾기 제거 (인증 필요)"""
    from app.models import FavoritePlace

    favorite = (
        db.query(FavoritePlace)
        .filter(
            FavoritePlace.user_id == current_user.id,
            FavoritePlace.place_id == place_id,
            FavoritePlace.place_type == place_type,
        )
        .first()
    )

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found"
        )

    db.delete(favorite)
    db.commit()

    return {"message": "Removed from favorites"}


@router.post("/reviews")
async def create_review(
    review: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """리뷰 작성 (인증 필요)"""
    from app.models import Review

    # 리뷰 생성
    new_review = Review(
        user_id=current_user.id,
        place_id=review.place_id,
        place_type=review.place_type,
        rating=review.rating,
        comment=review.comment,
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return {"message": "Review created successfully", "review_id": new_review.id}


@router.get("/reviews/{place_type}/{place_id}")
async def get_place_reviews(
    place_type: str,
    place_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """장소별 리뷰 조회"""
    from app.models import Review, User

    reviews = (
        db.query(Review, User.username)
        .join(User, Review.user_id == User.id)
        .filter(Review.place_id == place_id, Review.place_type == place_type)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": review.Review.id,
            "user_id": review.Review.user_id,
            "username": review.username,
            "rating": review.Review.rating,
            "comment": review.Review.comment,
            "created_at": review.Review.created_at,
        }
        for review in reviews
    ]


@router.get("/categories")
async def get_categories():
    """카테고리 목록 조회"""
    return {
        "restaurant_categories": ["한식", "중식", "일식", "양식", "카페", "기타"],
        "transportation_types": ["지하철", "버스", "택시", "기차", "공항"],
        "accommodation_types": ["호텔", "펜션", "게스트하우스", "모텔", "리조트"],
        "price_ranges": ["저렴", "보통", "고급", "럭셔리"],
    }


@router.get("/nearby")
async def get_nearby_places(
    latitude: float = Query(..., description="위도"),
    longitude: float = Query(..., description="경도"),
    radius: float = Query(5.0, description="반경 (km)", ge=0.1, le=50.0),
    category: str | None = Query(None, description="카테고리"),
    limit: int = Query(20, description="결과 개수", ge=1, le=100),
):
    """주변 장소 검색 (위치 기반)"""
    # 간단한 구현 - 실제로는 더 정교한 거리 계산 필요
    return {
        "message": "Nearby search feature is under development",
        "latitude": latitude,
        "longitude": longitude,
        "radius": radius,
        "category": category,
    }


@router.get("/resions")
async def get_regions_with_si_gun(db: Session = Depends(get_db)):
    """
    region_name이 '시' 또는 '군'으로 끝나는 지역만 반환
    """
    regions = await local_info_service.get_regions_with_si_gun(db)
    return {"regions": regions, "total": len(regions)}


@router.get("/resions_point")
async def get_regions_point(db: Session = Depends(get_db)):
    """
    region_level이 1인 지역만 반환
    """
    regions = await local_info_service.get_regions_point(db)
    return {"regions": regions, "total": len(regions)}
