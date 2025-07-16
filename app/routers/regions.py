"""
지역 정보 API 라우터
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.region_service import RegionService
from app.models import Region

router = APIRouter(prefix="/api/regions", tags=["Regions"])


@router.get("/")
async def get_all_regions(
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 100,
) -> dict:
    """
    모든 지역 정보 조회
    """
    try:
        # 전체 지역 개수
        total_count = db.query(Region).filter(Region.is_active == True).count()
        
        # 페이지네이션 적용
        offset = (page - 1) * page_size
        regions = db.query(Region).filter(Region.is_active == True).offset(offset).limit(page_size).all()
        
        # 응답 데이터 구성
        region_list = []
        for region in regions:
            region_data = {
                "region_id": str(region.region_id),
                "region_code": region.region_code,
                "region_name": region.region_name,
                "region_name_full": region.region_name_full,
                "parent_region_code": region.parent_region_code,
                "region_level": region.region_level,
                "latitude": float(region.latitude) if region.latitude else None,
                "longitude": float(region.longitude) if region.longitude else None,
                "grid_x": region.grid_x,
                "grid_y": region.grid_y,
                "is_active": region.is_active,
                "api_mappings": region.api_mappings or {},
            }
            region_list.append(region_data)
        
        return {
            "regions": region_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size,
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"지역 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/provinces")
async def get_provinces(db: Session = Depends(get_db)) -> dict:
    """
    광역시도 목록 조회
    """
    try:
        provinces = RegionService.get_provinces(db)
        
        result = []
        for province in provinces:
            province_data = {
                "region_code": province.region_code,
                "region_name": province.region_name,
                "region_name_full": province.region_name_full,
                "is_active": province.is_active,
            }
            result.append(province_data)
        
        return {"provinces": result}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"광역시도 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/cities")
async def get_cities(
    province_code: Optional[str] = None,
    db: Session = Depends(get_db)
) -> dict:
    """
    시군구 목록 조회
    """
    try:
        if province_code:
            cities = RegionService.get_cities(db, province_code)
        else:
            cities = db.query(Region).filter(
                Region.region_level == 2,
                Region.is_active == True
            ).all()
        
        result = []
        for city in cities:
            city_data = {
                "region_code": city.region_code,
                "region_name": city.region_name,
                "region_name_full": city.region_name_full,
                "parent_region_code": city.parent_region_code,
                "is_active": city.is_active,
            }
            result.append(city_data)
        
        return {"cities": result}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"시군구 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/supported")
async def get_supported_cities(db: Session = Depends(get_db)) -> dict:
    """
    지원되는 도시 목록 조회 (격자 좌표 보유)
    """
    try:
        cities = RegionService.get_supported_cities(db)
        return {"cities": cities}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"지원 도시 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/{region_code}")
async def get_region_detail(
    region_code: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    특정 지역 상세 정보 조회
    """
    try:
        region = RegionService.get_region_by_code(db, region_code)
        
        if not region:
            raise HTTPException(
                status_code=404,
                detail=f"지역 코드 '{region_code}'를 찾을 수 없습니다."
            )
        
        region_data = {
            "region_id": str(region.region_id),
            "region_code": region.region_code,
            "region_name": region.region_name,
            "region_name_full": region.region_name_full,
            "parent_region_code": region.parent_region_code,
            "region_level": region.region_level,
            "latitude": float(region.latitude) if region.latitude else None,
            "longitude": float(region.longitude) if region.longitude else None,
            "grid_x": region.grid_x,
            "grid_y": region.grid_y,
            "is_active": region.is_active,
            "api_mappings": region.api_mappings or {},
            "coordinate_info": region.coordinate_info or {},
        }
        
        return {"region": region_data}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"지역 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )