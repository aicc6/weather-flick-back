"""
기상청 API 유틸리티 함수들
"""

from typing import Dict, List, Optional, Tuple
import json
import os

# 주요 도시의 격자 좌표 (nx, ny)
CITY_COORDINATES = {
    "서울": {"nx": 60, "ny": 127},
    "부산": {"nx": 97, "ny": 74},
    "대구": {"nx": 89, "ny": 90},
    "인천": {"nx": 55, "ny": 124},
    "광주": {"nx": 58, "ny": 74},
    "대전": {"nx": 67, "ny": 100},
    "울산": {"nx": 102, "ny": 84},
    "세종": {"nx": 66, "ny": 103},
    "수원": {"nx": 60, "ny": 120},
    "고양": {"nx": 57, "ny": 128},
    "용인": {"nx": 64, "ny": 119},
    "창원": {"nx": 89, "ny": 76},
    "포항": {"nx": 102, "ny": 94},
    "제주": {"nx": 53, "ny": 38}
}

# 중기예보 지역 코드
REGION_CODES = {
    "서울": "11B10101",
    "부산": "11H20201",
    "대구": "11H10701",
    "인천": "11B20201",
    "광주": "11F20501",
    "대전": "11C20401",
    "울산": "11H20101",
    "세종": "11C20404",
    "수원": "11B20601",
    "고양": "11B20301",
    "용인": "11B20602",
    "창원": "11H20301",
    "포항": "11H10201",
    "제주": "11G00201"
}

# 도/특별시/광역시별 도시 매핑
PROVINCE_CITIES = {
    "서울특별시": ["서울"],
    "부산광역시": ["부산"],
    "대구광역시": ["대구"],
    "인천광역시": ["인천"],
    "광주광역시": ["광주"],
    "대전광역시": ["대전"],
    "울산광역시": ["울산"],
    "세종특별자치시": ["세종"],
    "경기도": ["수원", "고양", "용인"],
    "경상남도": ["창원"],
    "경상북도": ["포항"],
    "제주특별자치도": ["제주"]
}

KMA_AREA_CODE_MAP = {
    # ... (기존 매핑 정보)
}

# 도시 이름을 TourAPI 지역 코드로 변환하는 맵
CITY_TO_TOURAPI_AREA_CODE = {
    "서울": "1",
    "인천": "2",
    "대전": "3",
    "대구": "4",
    "광주": "5",
    "부산": "6",
    "울산": "7",
    "세종": "8",
    "경기도": "31",
    "강원도": "32",
    "충청북도": "33",
    "충청남도": "34",
    "경상북도": "35",
    "경상남도": "36",
    "전라북도": "37",
    "전라남도": "38",
    "제주도": "39",
}

def get_city_coordinates(city: str) -> Optional[Dict[str, int]]:
    """도시의 격자 좌표 조회"""
    return CITY_COORDINATES.get(city)

def get_region_code(city: str) -> Optional[str]:
    """도시의 중기예보 지역 코드 조회"""
    return REGION_CODES.get(city)

def get_supported_cities() -> List[str]:
    """지원되는 도시 목록 반환"""
    return list(CITY_COORDINATES.keys())

def is_supported_city(city: str) -> bool:
    """도시가 지원되는지 확인"""
    return city in CITY_COORDINATES

def get_supported_provinces() -> List[str]:
    """지원되는 도/광역시 목록 반환"""
    return list(PROVINCE_CITIES.keys())

def is_supported_province(province: str) -> bool:
    """도/광역시가 지원되는지 확인"""
    return province in PROVINCE_CITIES

def get_cities_in_province(province: str) -> Optional[List[str]]:
    """도/광역시에 속한 도시 목록 반환"""
    return PROVINCE_CITIES.get(province)

def get_all_city_info() -> Dict[str, Dict]:
    """모든 도시 정보 반환"""
    result = {}
    for city in CITY_COORDINATES:
        result[city] = {
            "coordinates": CITY_COORDINATES[city],
            "region_code": REGION_CODES.get(city, "N/A")
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
        "소나기": "소나기"
    }
    return weather_codes.get(code, code)

def convert_precipitation_type(code: str) -> str:
    """강수형태 코드 변환"""
    types = {
        "0": "없음",
        "1": "비",
        "2": "비/눈",
        "3": "눈",
        "4": "소나기"
    }
    return types.get(code, "알 수 없음")

def convert_wind_direction(degree: str) -> str:
    """풍향 각도를 방향으로 변환"""
    try:
        deg = float(degree)
        directions = ["북", "북동", "동", "남동", "남", "남서", "서", "북서"]
        index = int((deg + 22.5) / 45) % 8
        return directions[index]
    except:
        return "알 수 없음"

def get_base_time() -> Tuple[str, str]:
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

def get_nearest_city(nx: int, ny: int) -> Optional[str]:
    """가장 가까운 도시 찾기"""
    min_distance = float('inf')
    nearest_city = None

    for city, coords in CITY_COORDINATES.items():
        distance = ((nx - coords["nx"]) ** 2 + (ny - coords["ny"]) ** 2) ** 0.5
        if distance < min_distance:
            min_distance = distance
            nearest_city = city

    return nearest_city

def format_weather_data(data: Dict) -> Dict:
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

def get_area_code_for_city(city_name: str) -> str | None:
    """
    KMA 도시 이름(예: '서울', '수원')을 TourAPI 지역 코드(예: '1', '31')로 변환합니다.
    """
    if city_name in CITY_TO_TOURAPI_AREA_CODE:
        return CITY_TO_TOURAPI_AREA_CODE[city_name]

    for province, cities in PROVINCE_CITIES.items():
        if city_name in cities:
            return CITY_TO_TOURAPI_AREA_CODE.get(province)

    return None
