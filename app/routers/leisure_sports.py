"""레저 스포츠 정보 라우터"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LeisureSports, Region
from app.utils import create_error_response, create_standard_response

router = APIRouter(
    prefix="/leisure-sports",
    tags=["leisure-sports"],
)


@router.get("/search", response_model=dict)
async def search_leisure_sports(
    query: str = Query(..., description="검색어"),
    limit: int = Query(10, ge=1, le=50, description="결과 개수"),
    db: Session = Depends(get_db),
):
    """
    레저 스포츠 검색 (자동완성용)
    
    Args:
        query: 검색어
        limit: 반환할 최대 결과 수
    
    Returns:
        검색된 레저 스포츠 목록
    """
    try:
        # 검색어가 2글자 미만이면 빈 결과 반환
        if len(query.strip()) < 2:
            return create_standard_response(
                success=True,
                data={"suggestions": []}
            )

        # 시설명, 주소에서 검색
        search_pattern = f"%{query}%"
        leisure_sports = (
            db.query(LeisureSports)
            .filter(
                or_(
                    LeisureSports.facility_name.ilike(search_pattern),
                    LeisureSports.address.ilike(search_pattern)
                )
            )
            .limit(limit)
            .all()
        )

        # 자동완성 형식으로 변환
        suggestions = []
        for sport in leisure_sports:
            suggestions.append({
                "description": sport.facility_name,
                "place_id": sport.content_id,
                "structured_formatting": {
                    "main_text": sport.facility_name,
                    "secondary_text": sport.address
                }
            })

        return create_standard_response(
            success=True,
            data={"suggestions": suggestions}
        )

    except Exception as e:
        return create_error_response(
            code="SEARCH_ERROR",
            message="레저 스포츠 검색에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.get("/by-region", response_model=dict)
async def get_leisure_sports_by_region(
    region_code: str = Query(..., description="지역 코드"),
    limit: int = Query(100, ge=1, le=500, description="조회할 최대 개수"),
    db: Session = Depends(get_db),
):
    """
    지역별 레저 스포츠 조회
    
    Args:
        region_code: 지역 코드 (예: 1=서울, 6=부산 등)
        limit: 조회할 최대 개수
    
    Returns:
        해당 지역의 레저 스포츠 목록
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

        # Regions 테이블과 조인하여 tour_api_area_code로 레저 스포츠 조회
        leisure_sports = (
            db.query(LeisureSports)
            .join(Region, LeisureSports.region_code == Region.region_code)
            .filter(Region.tour_api_area_code == tour_api_area_code)
            .limit(limit)
            .all()
        )

        # 응답 데이터 구성
        sports_list = []
        for sport in leisure_sports:
            sports_list.append({
                "content_id": sport.content_id,
                "name": sport.facility_name,
                "sports_type": sport.sports_type,
                "address": sport.address,
                "latitude": float(sport.latitude) if sport.latitude else None,
                "longitude": float(sport.longitude) if sport.longitude else None,
                "tel": sport.tel,
                "homepage": sport.homepage,
                "operating_hours": sport.operating_hours,
                "admission_fee": sport.admission_fee,
                "parking_info": sport.parking_info,
                "created_at": sport.created_at.isoformat() if sport.created_at else None,
            })

        return create_standard_response(
            success=True,
            data={
                "leisure_sports": sports_list,
                "total": len(sports_list),
                "region_code": region_code,
                "tour_api_area_code": tour_api_area_code
            }
        )

    except Exception as e:
        return create_error_response(
            code="QUERY_ERROR",
            message="레저 스포츠 조회에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.get("/{content_id}", response_model=dict)
async def get_leisure_sports_detail(
    content_id: str,
    db: Session = Depends(get_db),
):
    """
    특정 레저 스포츠 상세 정보 조회
    
    Args:
        content_id: 레저 스포츠 콘텐츠 ID
    
    Returns:
        레저 스포츠 상세 정보
    """
    try:
        leisure_sport = (
            db.query(LeisureSports)
            .filter(LeisureSports.content_id == content_id)
            .first()
        )

        if not leisure_sport:
            return create_error_response(
                code="NOT_FOUND",
                message="레저 스포츠를 찾을 수 없습니다."
            )

        # 응답 데이터 구성
        sport_data = {
            "content_id": leisure_sport.content_id,
            "name": leisure_sport.facility_name,
            "sports_type": leisure_sport.sports_type,
            "category_code": leisure_sport.category_code,
            "sub_category_code": leisure_sport.sub_category_code,
            "address": leisure_sport.address,
            "detail_address": leisure_sport.detail_address,
            "zipcode": leisure_sport.zipcode,
            "latitude": float(leisure_sport.latitude) if leisure_sport.latitude else None,
            "longitude": float(leisure_sport.longitude) if leisure_sport.longitude else None,
            "tel": leisure_sport.tel,
            "homepage": leisure_sport.homepage,
            "operating_hours": leisure_sport.operating_hours,
            "admission_fee": leisure_sport.admission_fee,
            "parking_info": leisure_sport.parking_info,
            "rental_info": leisure_sport.rental_info,
            "capacity": leisure_sport.capacity,
            "reservation_info": leisure_sport.reservation_info,
            "overview": leisure_sport.overview,
            "first_image": leisure_sport.first_image,
            "created_at": leisure_sport.created_at.isoformat() if leisure_sport.created_at else None,
            "updated_at": leisure_sport.updated_at.isoformat() if leisure_sport.updated_at else None,
        }

        return create_standard_response(
            success=True,
            data=sport_data
        )

    except Exception as e:
        return create_error_response(
            code="QUERY_ERROR",
            message="레저 스포츠 상세 정보 조회에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )