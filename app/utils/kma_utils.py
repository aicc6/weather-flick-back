"""
기상청 API 유틸리티 함수들 - 데이터베이스 기반으로 리팩토링됨
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session

# 데이터베이스 기반 지역 서비스 import
from app.services.region_service import region_service, RegionService
from app.database import get_db


def get_city_coordinates(city: str, db: Session = None) -> Dict[str, int] | None:
    """도시의 격자 좌표 조회 - DB 기반"""
    if db is None:
        db = next(get_db())
    
    coordinates = RegionService.get_kma_grid_coordinates(db, city)
    return coordinates


def get_region_code(city: str, db: Session = None) -> str | None:
    """도시의 중기예보 지역 코드 조회 - DB 기반"""
    if db is None:
        db = next(get_db())
    
    mappings = RegionService.get_api_mappings(db, city)
    if mappings:
        kma_info = mappings.get("kma", {})
        return kma_info.get("region_code")
    return None


def get_supported_cities(db: Session = None) -> List[str]:
    """지원되는 도시 목록 반환 - DB 기반"""
    if db is None:
        db = next(get_db())
    
    return RegionService.get_supported_cities(db)


def is_supported_city(city: str, db: Session = None) -> bool:
    """도시가 지원되는지 확인 - DB 기반"""
    if db is None:
        db = next(get_db())
    
    return RegionService.is_supported_city(db, city)


def get_supported_provinces(db: Session = None) -> List[str]:
    """지원되는 도/광역시 목록 반환 - DB 기반"""
    if db is None:
        db = next(get_db())
    
    provinces = RegionService.get_provinces(db)
    return [province.region_name for province in provinces]


def is_supported_province(province: str, db: Session = None) -> bool:
    """도/광역시가 지원되는지 확인 - DB 기반"""
    if db is None:
        db = next(get_db())
    
    region = RegionService.get_region_by_name(db, province)
    return region is not None and region.region_level == 1


def get_cities_in_province(province: str, db: Session = None) -> List[str] | None:
    """도/광역시에 속한 도시 목록 반환 - DB 기반"""
    if db is None:
        db = next(get_db())
    
    # 광역시도 찾기
    province_region = RegionService.get_region_by_name(db, province)
    if not province_region:
        return None
    
    # 하위 시군구 찾기
    cities = RegionService.get_cities(db, province_region.region_code)
    return [city.region_name for city in cities]


def get_all_city_info(db: Session = None) -> Dict[str, Dict]:
    """모든 도시 정보 반환 - DB 기반"""
    if db is None:
        db = next(get_db())
    
    regions = RegionService.get_all_regions(db)
    result = {}
    
    for region in regions:
        coordinates = RegionService.get_kma_grid_coordinates(db, region.region_code)
        mappings = RegionService.get_api_mappings(db, region.region_code)
        
        region_code = "N/A"
        if mappings:
            kma_info = mappings.get("kma", {})
            region_code = kma_info.get("region_code", "N/A")
        
        result[region.region_name] = {
            "coordinates": coordinates or {},
            "region_code": region_code,
            "latitude": float(region.latitude) if region.latitude else None,
            "longitude": float(region.longitude) if region.longitude else None,
            "region_level": region.region_level,
        }
    
    return result


def convert_weather_code(code: str) -> str:
    """기상청 날씨 코드를 설명으로 변환"""
    weather_codes = {
        "맑음": "맑음",
        "구름많음": "구름많음",
        "흐림": "흐림",
        "비": "비",
        "비/눈": "비/눈",
        "눈": "눈",
        "소나기": "소나기",
    }
    return weather_codes.get(code, code)


def convert_precipitation_type(code: str) -> str:
    """강수형태 코드 변환"""
    types = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}
    return types.get(code, "알 수 없음")


def convert_wind_direction(degree: str) -> str:
    """풍향 각도를 방향으로 변환"""
    try:
        deg = float(degree)
        directions = ["북", "북동", "동", "남동", "남", "남서", "서", "북서"]
        index = int((deg + 22.5) / 45) % 8
        return directions[index]
    except (ValueError, TypeError):
        return "알 수 없음"


def get_base_time() -> tuple[str, str]:
    """기상청 API 기준시간 계산"""
    from datetime import datetime, timedelta

    now = datetime.now()
    hour = now.hour

    if hour < 2:
        # 전날 23시 발표
        base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
        base_time = "2300"
    elif hour < 5:
        base_date = now.strftime("%Y%m%d")
        base_time = "0200"
    elif hour < 8:
        base_date = now.strftime("%Y%m%d")
        base_time = "0500"
    elif hour < 11:
        base_date = now.strftime("%Y%m%d")
        base_time = "0800"
    elif hour < 14:
        base_date = now.strftime("%Y%m%d")
        base_time = "1100"
    elif hour < 17:
        base_date = now.strftime("%Y%m%d")
        base_time = "1400"
    elif hour < 20:
        base_date = now.strftime("%Y%m%d")
        base_time = "1700"
    elif hour < 23:
        base_date = now.strftime("%Y%m%d")
        base_time = "2000"
    else:
        base_date = now.strftime("%Y%m%d")
        base_time = "2300"

    return base_date, base_time


def validate_coordinates(nx: int, ny: int) -> bool:
    """격자 좌표 유효성 검사"""
    # 한국 영역 내 좌표인지 확인 (대략적인 범위)
    return 50 <= nx <= 150 and 30 <= ny <= 150


def get_nearest_city(nx: int, ny: int, db: Session = None) -> str | None:
    """가장 가까운 도시 찾기 - DB 기반"""
    if db is None:
        db = next(get_db())
    
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


def format_weather_data(data: dict) -> dict:
    """날씨 데이터 포맷팅"""
    if "temperature" in data:
        data["temperature"] = round(float(data["temperature"]), 1)

    if "humidity" in data:
        data["humidity"] = int(float(data["humidity"]))

    if "wind_speed" in data:
        data["wind_speed"] = round(float(data["wind_speed"]), 1)

    if "rainfall" in data:
        data["rainfall"] = round(float(data["rainfall"]), 1)

    return data


def get_area_code_for_city(city_name: str, db: Session = None) -> str | None:
    """
    KMA 도시 이름을 TourAPI 지역 코드로 변환 - DB 기반
    """
    if db is None:
        db = next(get_db())
    
    return RegionService.get_tour_api_area_code(db, city_name)
