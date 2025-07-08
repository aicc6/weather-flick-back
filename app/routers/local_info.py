from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.models import (
    ReviewCreate,
    SearchRequest,
    SearchResult,
    User,
    Restaurant,
    RestaurantResponse,
    Accommodation,
)
from app.services.local_info_service import local_info_service

router = APIRouter(prefix="/local", tags=["local_info"])


@router.get("/cities")
async def get_supported_cities(db: Session = Depends(get_db)):
    """
    활성화된 지역 목록 조회 (unified_regions 테이블에서)
    프론트엔드 지도 컴포넌트용
    """
    regions = await local_info_service.get_unified_regions_level1(db)
    return {"cities": regions}


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


@router.get("/restaurants/all")
async def get_all_restaurants(
    page: int = Query(1, description="페이지 번호", ge=1),
    page_size: int = Query(50, description="페이지당 항목 수", ge=1, le=200),
    region_code: str | None = Query(None, description="지역 코드"),
    category_code: str | None = Query(None, description="카테고리 코드"),
    db: Session = Depends(get_db),
):
    """
    모든 레스토랑 정보 조회 (PostgreSQL restaurants 테이블)

    Args:
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 항목 수 (기본값: 50, 최대: 200)
        region_code: 지역 코드로 필터링 (선택사항)
        category_code: 카테고리 코드로 필터링 (선택사항)
        db: 데이터베이스 세션

    Returns:
        dict: 레스토랑 목록과 페이지네이션 정보
    """
    try:
        # 쿼리 시작
        query = db.query(Restaurant)

        # 필터 적용
        if region_code:
            query = query.filter(Restaurant.region_code == region_code)

        if category_code:
            query = query.filter(Restaurant.category_code == category_code)

        # 전체 개수 계산
        total_count = query.count()

        # 페이지네이션 적용
        offset = (page - 1) * page_size
        restaurants = query.offset(offset).limit(page_size).all()

        # 응답 데이터 구성
        restaurant_list = []
        for restaurant in restaurants:
            restaurant_data = {
                "content_id": restaurant.content_id,
                "region_code": restaurant.region_code,
                "restaurant_name": restaurant.restaurant_name,
                "category_code": restaurant.category_code,
                "sub_category_code": restaurant.sub_category_code,
                "address": restaurant.address,
                "detail_address": restaurant.detail_address,
                "zipcode": restaurant.zipcode,
                "latitude": restaurant.latitude,
                "longitude": restaurant.longitude,
                "tel": restaurant.tel,
                "homepage": restaurant.homepage,
                "cuisine_type": restaurant.cuisine_type,
                "specialty_dish": restaurant.specialty_dish,
                "operating_hours": restaurant.operating_hours,
                "rest_date": restaurant.rest_date,
                "reservation_info": restaurant.reservation_info,
                "credit_card": restaurant.credit_card,
                "smoking": restaurant.smoking,
                "parking": restaurant.parking,
                "room_available": restaurant.room_available,
                "children_friendly": restaurant.children_friendly,
                "takeout": restaurant.takeout,
                "delivery": restaurant.delivery,
                "overview": restaurant.overview,
                "first_image": restaurant.first_image,
                "first_image_small": restaurant.first_image_small,
                "data_quality_score": restaurant.data_quality_score,
                "processing_status": restaurant.processing_status,
                "created_at": restaurant.created_at,
                "updated_at": restaurant.updated_at,
                "last_sync_at": restaurant.last_sync_at,
            }
            restaurant_list.append(restaurant_data)

        # 페이지네이션 정보 계산
        total_pages = (total_count + page_size - 1) // page_size

        return {
            "restaurants": restaurant_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "filters": {
                "region_code": region_code,
                "category_code": category_code,
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"레스토랑 정보를 가져오는 중 오류가 발생했습니다: {str(e)}"
        )


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


@router.get("/accommodations/all")
async def get_all_accommodations(
    page: int = Query(1, description="페이지 번호", ge=1),
    page_size: int = Query(50, description="페이지당 항목 수", ge=1, le=200),
    region_code: str | None = Query(None, description="지역 코드"),
    category_code: str | None = Query(None, description="카테고리 코드"),
    accommodation_type: str | None = Query(None, description="숙소 타입"),
    db: Session = Depends(get_db),
):
    """
    모든 숙소 정보 조회 (PostgreSQL accommodations 테이블)

    Args:
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 항목 수 (기본값: 50, 최대: 200)
        region_code: 지역 코드로 필터링 (선택사항)
        category_code: 카테고리 코드로 필터링 (선택사항)
        accommodation_type: 숙소 타입으로 필터링 (선택사항)
        db: 데이터베이스 세션

    Returns:
        dict: 숙소 목록과 페이지네이션 정보
    """
    try:
        # 쿼리 시작
        query = db.query(Accommodation)

        # 필터 적용
        if region_code:
            query = query.filter(Accommodation.region_code == region_code)

        # category_code와 accommodation_type 필터는 실제 DB에 해당 컬럼이 없으므로 제거
        # if category_code:
        #     query = query.filter(Accommodation.category_code == category_code)

        # if accommodation_type:
        #     query = query.filter(Accommodation.accommodation_type == accommodation_type)

        # 전체 개수 계산
        total_count = query.count()

        # 페이지네이션 적용
        offset = (page - 1) * page_size
        accommodations = query.offset(offset).limit(page_size).all()

        # 응답 데이터 구성
        accommodation_list = []
        for accommodation in accommodations:
            accommodation_data = {
                "content_id": accommodation.content_id,
                "region_code": accommodation.region_code,
                "accommodation_name": accommodation.accommodation_name,
                "accommodation_type": accommodation.accommodation_type,
                "address": accommodation.address,
                "tel": accommodation.tel,
                "latitude": accommodation.latitude,
                "longitude": accommodation.longitude,
                "parking": accommodation.parking,
                "created_at": accommodation.created_at,
            }
            accommodation_list.append(accommodation_data)

        # 페이지네이션 정보 계산
        total_pages = (total_count + page_size - 1) // page_size

        return {
            "accommodations": accommodation_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "filters": {
                "region_code": region_code,
                "category_code": category_code,
                "accommodation_type": accommodation_type,
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"숙소 정보를 가져오는 중 오류가 발생했습니다: {str(e)}"
        )


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

    # 새 리뷰 생성
    new_review = Review(
        user_id=current_user.id,
        destination_id=review.destination_id,
        travel_plan_id=review.travel_plan_id,
        rating=review.rating,
        content=review.content,
        photos=review.photos,
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return {
        "message": "Review created successfully",
        "review_id": new_review.review_id,
    }


@router.get("/reviews/{place_type}/{place_id}")
async def get_place_reviews(
    place_type: str,
    place_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """장소별 리뷰 조회"""
    from app.models import Review

    reviews = (
        db.query(Review)
        .filter(Review.destination_id == place_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "review_id": review.review_id,
            "user_id": review.user_id,
            "rating": review.rating,
            "content": review.content,
            "photos": review.photos,
            "created_at": review.created_at,
        }
        for review in reviews
    ]


@router.get("/categories")
async def get_categories():
    """카테고리 목록 조회"""
    return {
        "restaurants": ["한식", "중식", "일식", "양식", "카페", "기타"],
        "accommodations": ["호텔", "펜션", "게스트하우스", "모텔", "리조트"],
        "transportation": ["지하철", "버스", "택시", "기차", "공항"],
    }


@router.get("/nearby")
async def get_nearby_places(
    latitude: float = Query(..., description="위도"),
    longitude: float = Query(..., description="경도"),
    radius: float = Query(5.0, description="반경 (km)", ge=0.1, le=50.0),
    category: str | None = Query(None, description="카테고리"),
    limit: int = Query(20, description="결과 개수", ge=1, le=100),
):
    """주변 장소 검색"""
    nearby_places = await local_info_service.get_nearby_places(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        category=category,
        limit=limit,
    )
    return {"places": nearby_places, "total": len(nearby_places)}


@router.get("/resions")
async def get_unified_regions_level1(db: Session = Depends(get_db)):
    """통합 지역정보 레벨1 조회"""
    regions = await local_info_service.get_unified_regions_level1(db)
    return {"regions": regions}


@router.get("/resions_point")
async def get_regions_point(db: Session = Depends(get_db)):
    """통합 지역정보 포인트 조회"""
    regions = await local_info_service.get_regions_point(db)
    return {"regions": regions}
