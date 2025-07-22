"""
지역 정보 서비스 - 데이터베이스 기반 지역 관리
하드코딩된 지역 정보를 대체
"""

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Region


class RegionService:
    """지역 정보 관리 서비스"""

    @staticmethod
    def get_all_regions(db: Session) -> list[Region]:
        """모든 지역 정보 조회"""
        return db.query(Region).filter(Region.is_active == True).all()

    @staticmethod
    def get_provinces(db: Session) -> list[Region]:
        """광역시도(1레벨) 조회"""
        return (
            db.query(Region)
            .filter(and_(Region.region_level == 1, Region.is_active == True))
            .all()
        )

    @staticmethod
    def get_cities(db: Session, parent_code: str | None = None) -> list[Region]:
        """시군구(2레벨) 조회"""
        query = db.query(Region).filter(
            and_(Region.region_level == 2, Region.is_active == True)
        )

        if parent_code:
            query = query.filter(Region.parent_region_code == parent_code)

        return query.all()

    @staticmethod
    def get_region_by_code(db: Session, region_code: str) -> Region | None:
        """지역 코드로 지역 정보 조회"""
        return (
            db.query(Region)
            .filter(and_(Region.region_code == region_code, Region.is_active == True))
            .first()
        )

    @staticmethod
    def get_region_by_name(db: Session, region_name: str) -> Region | None:
        """지역명으로 지역 정보 조회"""
        return (
            db.query(Region)
            .filter(
                and_(
                    or_(
                        Region.region_name == region_name,
                        Region.region_name_full == region_name,
                    ),
                    Region.is_active == True,
                )
            )
            .first()
        )

    @staticmethod
    def search_regions(db: Session, search_term: str) -> list[Region]:
        """지역 검색"""
        search_pattern = f"%{search_term}%"
        return (
            db.query(Region)
            .filter(
                and_(
                    or_(
                        Region.region_name.ilike(search_pattern),
                        Region.region_name_full.ilike(search_pattern),
                    ),
                    Region.is_active == True,
                )
            )
            .all()
        )

    @staticmethod
    def get_coordinates(db: Session, region_code: str) -> tuple[float, float] | None:
        """지역의 좌표 조회"""
        region = RegionService.get_region_by_code(db, region_code)
        if region and region.latitude and region.longitude:
            return (float(region.latitude), float(region.longitude))
        return None

    @staticmethod
    def get_kma_grid_coordinates(
        db: Session, region_code: str
    ) -> dict[str, int] | None:
        """기상청 격자 좌표 조회"""
        region = RegionService.get_region_by_code(db, region_code)
        if region and region.grid_x and region.grid_y:
            return {"nx": region.grid_x, "ny": region.grid_y}
        return None

    @staticmethod
    def get_api_mappings(db: Session, region_code: str) -> dict | None:
        """API 매핑 정보 조회"""
        region = RegionService.get_region_by_code(db, region_code)
        if region and region.api_mappings:
            return region.api_mappings
        return None

    @staticmethod
    def get_tour_api_area_code(db: Session, region_code: str) -> str | None:
        """관광공사 API 지역 코드 조회"""
        region = RegionService.get_region_by_code(db, region_code)
        if region and region.api_mappings:
            tour_api = region.api_mappings.get("tour_api", {})
            return str(tour_api.get("area_code")) if tour_api.get("area_code") else None
        return None

    @staticmethod
    def get_supported_cities(db: Session) -> list[str]:
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
    ) -> Region | None:
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
    def get_region_statistics(db: Session) -> dict:
        """지역 통계 정보"""
        total_regions = db.query(Region).filter(Region.is_active == True).count()
        provinces = (
            db.query(Region)
            .filter(and_(Region.region_level == 1, Region.is_active == True))
            .count()
        )
        cities = (
            db.query(Region)
            .filter(and_(Region.region_level == 2, Region.is_active == True))
            .count()
        )

        return {
            "total_regions": total_regions,
            "provinces": provinces,
            "cities": cities,
            "active_regions": total_regions,
        }

    @staticmethod
    def get_weather_compatible_regions(db: Session) -> list[Region]:
        """기상청 API 호환 지역 목록"""
        return (
            db.query(Region)
            .filter(
                and_(
                    Region.is_active == True,
                    Region.grid_x.isnot(None),
                    Region.grid_y.isnot(None),
                )
            )
            .all()
        )

    @staticmethod
    def get_tour_compatible_regions(db: Session) -> list[Region]:
        """관광공사 API 호환 지역 목록"""
        return (
            db.query(Region)
            .filter(
                and_(
                    Region.is_active == True,
                    Region.api_mappings.op("->>")(["tour_api", "area_code"]).isnot(
                        None
                    ),
                )
            )
            .all()
        )

    @staticmethod
    def get_region_by_tour_api_area_code(
        db: Session, tour_api_area_code: str
    ) -> Region | None:
        """관광공사 API 지역 코드로 지역 정보 조회"""
        return (
            db.query(Region)
            .filter(
                and_(
                    Region.is_active == True,
                    Region.tour_api_area_code == tour_api_area_code,
                )
            )
            .first()
        )

    @staticmethod
    def get_region_name_by_frontend_code(db: Session, frontend_code: str) -> str:
        """프론트엔드 지역 코드로 지역명 조회 (매핑 테이블 사용)"""
        # 프론트엔드 코드를 실제 tour_api_area_code로 매핑
        frontend_to_tour_api_mapping = {
            "11": "1",  # 서울
            "28": "2",  # 인천
            "30": "3",  # 대전
            "27": "4",  # 대구
            "29": "5",  # 광주
            "26": "6",  # 부산
            "31": "7",  # 울산
            "36": "8",  # 세종 (DB에 없을 수 있음)
            "41": "31",  # 경기
            "51": "32",  # 강원
            "43": "33",  # 충북
            "44": "34",  # 충남
            "47": "35",  # 경북
            "48": "36",  # 경남
            "52": "37",  # 전북
            "46": "38",  # 전남
            "50": "39",  # 제주
        }

        # 매핑된 tour_api_area_code 가져오기
        tour_api_code = frontend_to_tour_api_mapping.get(frontend_code, frontend_code)

        # DB에서 지역 정보 조회
        region = RegionService.get_region_by_tour_api_area_code(db, tour_api_code)

        # 세종시가 DB에 없는 경우 하드코딩된 값 반환
        if not region and frontend_code == "36":
            return "세종"

        return region.region_name if region else "지역"


# 하위 호환성을 위한 함수들 (기존 kma_utils.py 함수들을 대체)
def get_city_coordinates(city: str, db: Session = None) -> dict[str, int] | None:
    """도시의 격자 좌표 조회 (하위 호환성)"""
    if db is None:
        db = next(get_db())

    return RegionService.get_kma_grid_coordinates(db, city)


def get_region_code(city: str, db: Session = None) -> str | None:
    """중기예보 지역 코드 조회 (하위 호환성)"""
    if db is None:
        db = next(get_db())

    mappings = RegionService.get_api_mappings(db, city)
    if mappings:
        kma_info = mappings.get("kma", {})
        return kma_info.get("region_code")
    return None


def get_supported_cities(db: Session = None) -> list[str]:
    """지원되는 도시 목록 반환 (하위 호환성)"""
    if db is None:
        db = next(get_db())

    return RegionService.get_supported_cities(db)


def is_supported_city(city: str, db: Session = None) -> bool:
    """도시가 지원되는지 확인 (하위 호환성)"""
    if db is None:
        db = next(get_db())

    return RegionService.is_supported_city(db, city)


def get_area_code_for_city(city_name: str, db: Session = None) -> str | None:
    """KMA 도시 이름을 TourAPI 지역 코드로 변환 (하위 호환성)"""
    if db is None:
        db = next(get_db())

    return RegionService.get_tour_api_area_code(db, city_name)


def get_nearest_city(nx: int, ny: int, db: Session = None) -> str | None:
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
            distance = ((nx - region.grid_x) ** 2 + (ny - region.grid_y) ** 2) ** 0.5

            if distance < min_distance:
                min_distance = distance
                nearest_city = region.region_name

    return nearest_city


# 전역 인스턴스
region_service = RegionService()
