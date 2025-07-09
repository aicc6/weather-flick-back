
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_active_user
from app.models import User
from app.services.kma_weather_service import kma_weather_service
from app.utils.kma_utils import (
    get_city_coordinates,
    get_region_code,
    get_supported_cities,
    get_supported_provinces,
    is_supported_city,
    is_supported_province,
)

router = APIRouter(prefix="/kma", tags=["기상청 날씨 API"])


@router.get("/provinces")
async def get_provinces():
    """지원되는 도/광역시 목록 조회"""
    return {
        "provinces": get_supported_provinces(),
        "message": "기상청 API에서 지원하는 도/광역시 목록입니다.",
    }


@router.get("/cities")
async def get_supported_cities_endpoint():
    """지원되는 도시 목록 조회"""
    return {
        "cities": get_supported_cities(),
        "message": "기상청 API에서 지원하는 주요 도시 목록입니다.",
    }


@router.get("/current/all-cities")
async def get_all_cities_current_weather_kma(
    current_user: User | None = Depends(get_current_active_user),
):
    """모든 주요 도시의 현재 날씨 조회"""
    weather_data = await kma_weather_service.get_all_cities_current_weather()
    return {"source": "기상청", "weather_data": weather_data}


@router.get("/current/{city}")
async def get_current_weather_kma(
    city: str, current_user: User | None = Depends(get_current_active_user)
):
    """기상청 현재 날씨 조회"""
    if not is_supported_city(city):
        raise HTTPException(status_code=400, detail=f"지원하지 않는 도시입니다: {city}")

    coords = get_city_coordinates(city)
    if coords is None:
        raise HTTPException(status_code=500, detail=f"도시 좌표 정보를 찾을 수 없습니다: {city}")
    weather_data = await kma_weather_service.get_current_weather(
        coords["nx"], coords["ny"]
    )

    return {
        "city": city,
        "source": "기상청",
        "coordinates": coords,
        "weather": weather_data,
    }


@router.get("/forecast/short/{city}")
async def get_short_forecast_kma(
    city: str, current_user: User | None = Depends(get_current_active_user)
):
    """기상청 단기예보 조회 (3일)"""
    if not is_supported_city(city):
        raise HTTPException(status_code=400, detail=f"지원하지 않는 도시입니다: {city}")

    coords = get_city_coordinates(city)
    if coords is None:
        raise HTTPException(status_code=500, detail=f"도시 좌표 정보를 찾을 수 없습니다: {city}")
    forecast_data = await kma_weather_service.get_short_forecast(
        coords["nx"], coords["ny"]
    )

    return {
        "city": city,
        "source": "기상청",
        "forecast_type": "단기예보 (3일)",
        "coordinates": coords,
        "forecast": forecast_data,
    }


@router.get("/forecast/mid/{city}")
async def get_mid_forecast_kma(
    city: str, current_user: User | None = Depends(get_current_active_user)
):
    """기상청 중기예보 조회 (3~10일)"""
    if not is_supported_city(city):
        raise HTTPException(status_code=400, detail=f"지원하지 않는 도시입니다: {city}")

    reg_id = get_region_code(city)
    if not reg_id:
        raise HTTPException(
            status_code=400, detail=f"중기예보를 지원하지 않는 도시입니다: {city}"
        )

    forecast_data = await kma_weather_service.get_mid_forecast(reg_id)

    return {
        "city": city,
        "source": "기상청",
        "forecast_type": "중기예보 (3~10일)",
        "region_code": reg_id,
        "forecast": forecast_data,
    }


@router.get("/warning/{area}")
async def get_weather_warning_kma(
    area: str, current_user: User | None = Depends(get_current_active_user)
):
    """기상특보 조회"""
    warning_data = await kma_weather_service.get_weather_warning(area)

    return {"area": area, "source": "기상청", "warning": warning_data}


@router.get("/compare/{city}")
async def compare_weather_sources(
    city: str, current_user: User | None = Depends(get_current_active_user)
):
    """WeatherAPI와 기상청 API 비교"""
    if not is_supported_city(city):
        raise HTTPException(status_code=400, detail=f"지원하지 않는 도시입니다: {city}")

    # 기상청 데이터 조회
    coords = get_city_coordinates(city)
    if coords is None:
        raise HTTPException(status_code=500, detail=f"도시 좌표 정보를 찾을 수 없습니다: {city}")
    kma_weather = await kma_weather_service.get_current_weather(
        coords["nx"], coords["ny"]
    )

    # WeatherAPI 데이터 조회 (기존 서비스 사용)
    from app.services.weather_service import weather_service

    try:
        weather_api_data = await weather_service.get_current_weather(city, "KR")
    except Exception:
        weather_api_data = {"error": "WeatherAPI 조회 실패"}

    return {
        "city": city,
        "comparison": {
            "kma": {"source": "기상청", "data": kma_weather},
            "weather_api": {"source": "WeatherAPI", "data": weather_api_data},
        },
    }


@router.get("/coordinates/{city}")
async def get_city_coordinates_api(city: str):
    """도시의 격자 좌표 조회"""
    if not is_supported_city(city):
        raise HTTPException(status_code=400, detail=f"지원하지 않는 도시입니다: {city}")

    return {
        "city": city,
        "coordinates": get_city_coordinates(city),
        "region_code": get_region_code(city),
    }


@router.get("/current/by-province/{province_name}")
async def get_province_weather_kma(
    province_name: str, current_user: User | None = Depends(get_current_active_user)
):
    """특정 도/광역시의 모든 도시 현재 날씨 조회"""
    if not is_supported_province(province_name):
        raise HTTPException(
            status_code=404, detail=f"지원하지 않는 도/광역시입니다: {province_name}"
        )

    weather_data = await kma_weather_service.get_weather_for_province(province_name)

    return {"province": province_name, "source": "기상청", "weather_data": weather_data}
