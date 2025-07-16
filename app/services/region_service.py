"""
지역 정보 서비스 - 데이터베이스 기반 지역 관리
하드코딩된 지역 정보를 대체
"""

from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import Region
from app.database import get_db


class RegionService:
    """지역 정보 관리 서비스"""

    @staticmethod
    def get_all_regions(db: Session) -> List[Region]:
        """모든 지역 정보 조회"""
        return db.query(Region).filter(Region.is_active == True).all()

    @staticmethod
    def get_provinces(db: Session) -> List[Region]:
        """광역시도(1레벨) 조회"""
        return (
            db.query(Region)
            .filter(and_(Region.region_level == 1, Region.is_active == True))
            .all()
        )

    @staticmethod
    def get_cities(db: Session, parent_code: Optional[str] = None) -> List[Region]:
        """시군구(2레벨) 조회"""
        query = db.query(Region).filter(
            and_(Region.region_level == 2, Region.is_active == True)
        )
        
        if parent_code:
            query = query.filter(Region.parent_region_code == parent_code)
            
        return query.all()

    @staticmethod
    def get_region_by_code(db: Session, region_code: str) -> Optional[Region]:
        """지역 코드로 지역 정보 조회"""
        return (
            db.query(Region)
            .filter(
                and_(Region.region_code == region_code, Region.is_active == True)
            )
            .first()
        )

    @staticmethod
    def get_region_by_name(db: Session, region_name: str) -> Optional[Region]:
        """지역명으로 지역 정보 조회"""
        return (
            db.query(Region)
            .filter(
                and_(
                    or_(
                        Region.region_name == region_name,
                        Region.region_name_full == region_name
                    ),
                    Region.is_active == True
                )
            )
            .first()
        )

    @staticmethod
    def search_regions(db: Session, search_term: str) -> List[Region]:
        """지역 검색"""
        search_pattern = f"%{search_term}%"
        return (
            db.query(Region)
            .filter(
                and_(
                    or_(
                        Region.region_name.ilike(search_pattern),
                        Region.region_name_full.ilike(search_pattern)
                    ),
                    Region.is_active == True
                )
            )
            .all()
        )

    @staticmethod
    def get_coordinates(db: Session, region_code: str) -> Optional[Tuple[float, float]]:
        """지역의 좌표 조회"""
        region = RegionService.get_region_by_code(db, region_code)
        if region and region.latitude and region.longitude:
            return (float(region.latitude), float(region.longitude))
        return None

    @staticmethod
    def get_kma_grid_coordinates(db: Session, region_code: str) -> Optional[Dict[str, int]]:
        """기상청 격자 좌표 조회"""
        region = RegionService.get_region_by_code(db, region_code)
        if region and region.grid_x and region.grid_y:
            return {"nx": region.grid_x, "ny": region.grid_y}
        return None

    @staticmethod
    def get_api_mappings(db: Session, region_code: str) -> Optional[Dict]:
        """API 매핑 정보 조회"""
        region = RegionService.get_region_by_code(db, region_code)
        if region and region.api_mappings:
            return region.api_mappings
        return None

    @staticmethod
    def get_tour_api_area_code(db: Session, region_code: str) -> Optional[str]:
        """관광공사 API 지역 코드 조회"""
        region = RegionService.get_region_by_code(db, region_code)
        if region and region.api_mappings:
            tour_api = region.api_mappings.get("tour_api", {})
            return str(tour_api.get("area_code")) if tour_api.get("area_code") else None
        return None

    @staticmethod
    def get_supported_cities(db: Session) -> List[str]:
        """지원되는 도시 목록 (하위 호환성)"""
        regions = RegionService.get_all_regions(db)
        return [region.region_name for region in regions]

    @staticmethod
    def is_supported_city(db: Session, city_name: str) -> bool:
        """도시 지원 여부 확인"""
        region = RegionService.get_region_by_name(db, city_name)
        return region is not None

    @staticmethod
    def get_nearest_region(
        db: Session, latitude: float, longitude: float
    ) -> Optional[Region]:
        """가장 가까운 지역 찾기"""
        regions = RegionService.get_all_regions(db)
        
        min_distance = float("inf")
        nearest_region = None

        for region in regions:
            if region.latitude and region.longitude:
                distance = (
                    (latitude - float(region.latitude)) ** 2
                    + (longitude - float(region.longitude)) ** 2
                ) ** 0.5
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_region = region

        return nearest_region

    @staticmethod
    def get_region_statistics(db: Session) -> Dict:
        """지역 통계 정보"""
        total_regions = db.query(Region).filter(Region.is_active == True).count()
        provinces = db.query(Region).filter(
            and_(Region.region_level == 1, Region.is_active == True)
        ).count()
        cities = db.query(Region).filter(
            and_(Region.region_level == 2, Region.is_active == True)
        ).count()

        return {
            "total_regions": total_regions,
            "provinces": provinces,
            "cities": cities,
            "active_regions": total_regions,
        }

    @staticmethod
    def get_weather_compatible_regions(db: Session) -> List[Region]:
        """기상청 API 호환 지역 목록"""
        return (
            db.query(Region)
            .filter(
                and_(
                    Region.is_active == True,
                    Region.grid_x.isnot(None),
                    Region.grid_y.isnot(None)
                )
            )
            .all()
        )

    @staticmethod
    def get_tour_compatible_regions(db: Session) -> List[Region]:
        """관광공사 API 호환 지역 목록"""
        return (
            db.query(Region)
            .filter(
                and_(
                    Region.is_active == True,
                    Region.api_mappings.op("->>")(["tour_api", "area_code"]).isnot(None)
                )
            )
            .all()
        )


# 하위 호환성을 위한 함수들 (기존 kma_utils.py 함수들을 대체)
def get_city_coordinates(city: str, db: Session = None) -> Optional[Dict[str, int]]:
    """도시의 격자 좌표 조회 (하위 호환성)"""
    if db is None:
        db = next(get_db())
    
    return RegionService.get_kma_grid_coordinates(db, city)


def get_region_code(city: str, db: Session = None) -> Optional[str]:
    """중기예보 지역 코드 조회 (하위 호환성)"""
    if db is None:
        db = next(get_db())
    
    mappings = RegionService.get_api_mappings(db, city)
    if mappings:
        kma_info = mappings.get("kma", {})
        return kma_info.get("region_code")
    return None


def get_supported_cities(db: Session = None) -> List[str]:
    """지원되는 도시 목록 반환 (하위 호환성)"""
    if db is None:
        db = next(get_db())
    
    return RegionService.get_supported_cities(db)


def is_supported_city(city: str, db: Session = None) -> bool:
    """도시가 지원되는지 확인 (하위 호환성)"""
    if db is None:
        db = next(get_db())
    
    return RegionService.is_supported_city(db, city)


def get_area_code_for_city(city_name: str, db: Session = None) -> Optional[str]:
    """KMA 도시 이름을 TourAPI 지역 코드로 변환 (하위 호환성)"""
    if db is None:
        db = next(get_db())
    
    return RegionService.get_tour_api_area_code(db, city_name)


def get_nearest_city(nx: int, ny: int, db: Session = None) -> Optional[str]:
    """가장 가까운 도시 찾기 (하위 호환성)"""
    if db is None:
        db = next(get_db())
    
    # 격자 좌표를 위경도로 변환하는 로직이 필요하지만,
    # 임시로 기존 로직을 사용
    regions = RegionService.get_weather_compatible_regions(db)
    
    min_distance = float("inf")
    nearest_city = None

    for region in regions:
        if region.grid_x and region.grid_y:
            distance = (
                (nx - region.grid_x) ** 2 + (ny - region.grid_y) ** 2
            ) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                nearest_city = region.region_name

    return nearest_city


# 전역 인스턴스
region_service = RegionService()