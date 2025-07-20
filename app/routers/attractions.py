"""관광지 정보 라우터"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TouristAttraction, PetTourInfo, Region
from app.utils import create_error_response, create_standard_response

router = APIRouter(
    prefix="/attractions",
    tags=["attractions"],
)


@router.get("/search", response_model=dict)
async def search_attractions(
    query: str = Query(..., description="검색어"),
    limit: int = Query(10, ge=1, le=50, description="결과 개수"),
    db: Session = Depends(get_db),
):
    """
    관광지 검색 (자동완성용)
    
    Args:
        query: 검색어
        limit: 반환할 최대 결과 수
    
    Returns:
        검색된 관광지 목록
    """
    try:
        # 검색어가 2글자 미만이면 빈 결과 반환
        if len(query.strip()) < 2:
            return create_standard_response(
                success=True,
                data={"suggestions": []}
            )

        # 관광지명, 주소에서 검색
        search_pattern = f"%{query}%"
        attractions = (
            db.query(TouristAttraction)
            .filter(
                or_(
                    TouristAttraction.attraction_name.ilike(search_pattern),
                    TouristAttraction.address.ilike(search_pattern)
                )
            )
            .limit(limit)
            .all()
        )

        # 자동완성 형식으로 변환
        suggestions = []
        for attraction in attractions:
            suggestions.append({
                "description": attraction.attraction_name,
                "place_id": attraction.content_id,
                "structured_formatting": {
                    "main_text": attraction.attraction_name,
                    "secondary_text": attraction.address
                }
            })

        return create_standard_response(
            success=True,
            data={"suggestions": suggestions}
        )

    except Exception as e:
        return create_error_response(
            code="SEARCH_ERROR",
            message="관광지 검색에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.get("/by-region", response_model=dict)
async def get_attractions_by_region(
    region_code: str = Query(..., description="지역 코드"),
    limit: int = Query(100, ge=1, le=500, description="조회할 최대 개수"),
    pet_friendly: bool = Query(False, description="반려동물 동반 가능 여부 필터"),
    db: Session = Depends(get_db),
):
    """
    지역별 관광지 조회
    
    Args:
        region_code: 지역 코드 (예: 11=서울, 26=부산 등)
        limit: 조회할 최대 개수
    
    Returns:
        해당 지역의 관광지 목록
    """
    try:
        # region_code를 tour_api_area_code로 매핑
        region_to_tour_api_mapping = {
            "11": "1",    # 서울
            "26": "6",    # 부산
            "27": "4",    # 대구
            "28": "2",    # 인천
            "29": "5",    # 광주
            "30": "3",    # 대전
            "31": "7",    # 울산
            "36": "8",    # 세종
            "41": "31",   # 경기
            "43": "33",   # 충북
            "44": "34",   # 충남
            "46": "36",   # 전남
            "47": "35",   # 경북
            "48": "38",   # 경남
            "50": "39",   # 제주
            "51": "32",   # 강원
            "52": "37",   # 전북
            # 긴 코드 형태 처리
            "11000000": "1",  # 서울
            "42000000": "31", # 경기도
        }

        # 긴 형태의 region_code를 짧은 형태로 변환
        if len(region_code) > 2:
            short_code = region_code[:2]
            tour_api_area_code = region_to_tour_api_mapping.get(short_code, region_code)
        else:
            tour_api_area_code = region_to_tour_api_mapping.get(region_code, region_code)

        # TouristAttraction과 Region 테이블을 조인하여 tour_api_area_code로 조회
        query = db.query(TouristAttraction).join(
            Region, TouristAttraction.region_code == Region.region_code
        ).filter(
            Region.tour_api_area_code == tour_api_area_code
        )
        
        # 반려동물 동반 가능 필터 적용
        if pet_friendly:
            # pet_tour_info에서 해당 지역의 content_id 목록 조회
            pet_content_ids = db.query(PetTourInfo.content_id).filter(
                PetTourInfo.area_code == tour_api_area_code,
                PetTourInfo.content_id.isnot(None)
            ).subquery()
            
            query = query.filter(
                TouristAttraction.content_id.in_(pet_content_ids)
            )
        
        attractions = query.limit(limit).all()

        # 응답 데이터 구성
        attraction_list = []
        for attraction in attractions:
            attraction_list.append({
                "content_id": attraction.content_id,
                "name": attraction.attraction_name,
                "category": attraction.category_name,
                "address": attraction.address,
                "latitude": float(attraction.latitude) if attraction.latitude else None,
                "longitude": float(attraction.longitude) if attraction.longitude else None,
                "description": attraction.description,
                "image_url": attraction.image_url,
                "created_at": attraction.created_at.isoformat() if attraction.created_at else None,
            })

        return create_standard_response(
            success=True,
            data={
                "attractions": attraction_list,
                "total": len(attraction_list),
                "region_code": region_code,
                "tour_api_area_code": tour_api_area_code
            }
        )

    except Exception as e:
        return create_error_response(
            code="QUERY_ERROR",
            message="관광지 조회에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.get("/{content_id}", response_model=dict)
async def get_attraction_detail(
    content_id: str,
    db: Session = Depends(get_db),
):
    """
    특정 관광지 상세 정보 조회
    
    Args:
        content_id: 관광지 콘텐츠 ID
    
    Returns:
        관광지 상세 정보
    """
    try:
        attraction = (
            db.query(TouristAttraction)
            .filter(TouristAttraction.content_id == content_id)
            .first()
        )

        if not attraction:
            return create_error_response(
                code="NOT_FOUND",
                message="관광지를 찾을 수 없습니다."
            )

        # 응답 데이터 구성
        attraction_data = {
            "content_id": attraction.content_id,
            "name": attraction.attraction_name,
            "category": attraction.category_name,
            "category_code": attraction.category_code,
            "address": attraction.address,
            "latitude": float(attraction.latitude) if attraction.latitude else None,
            "longitude": float(attraction.longitude) if attraction.longitude else None,
            "description": attraction.description,
            "homepage": attraction.homepage,
            "image_url": attraction.image_url,
            "created_at": attraction.created_at.isoformat() if attraction.created_at else None,
            "updated_at": attraction.updated_at.isoformat() if attraction.updated_at else None,
        }

        return create_standard_response(
            success=True,
            data=attraction_data
        )

    except Exception as e:
        return create_error_response(
            code="QUERY_ERROR",
            message="관광지 상세 정보 조회에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )
