
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_active_user
from app.models import ForecastResponse, User, WeatherRequest, WeatherResponse
from app.services.weather_service import weather_service

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/")
async def get_weather_info():
    """날씨 정보 조회"""
    return {"message": "Weather API endpoint", "provider": "WeatherAPI"}


@router.post("/current", response_model=WeatherResponse)
async def get_current_weather(request: WeatherRequest):
    """현재 날씨 정보 조회"""
    try:
        weather_data = await weather_service.get_current_weather(
            city=request.city, country=request.country
        )
        return WeatherResponse(**weather_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weather service error: {str(e)}")


@router.get("/current/{city}")
async def get_current_weather_by_city(
    city: str,
    country: str | None = Query(None, description="국가 코드 (예: KR, US)"),
):
    """도시명으로 현재 날씨 조회"""
    try:
        weather_data = await weather_service.get_current_weather(
            city=city, country=country
        )
        return WeatherResponse(**weather_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weather service error: {str(e)}")


@router.get("/forecast/{city}")
async def get_weather_forecast(
    city: str,
    days: int = Query(3, ge=1, le=14, description="예보 일수 (1-14일)"),
    country: str | None = Query(None, description="국가 코드 (예: KR, US)"),
):
    """날씨 예보 조회"""
    try:
        forecast_data = await weather_service.get_forecast(
            city=city, days=days, country=country
        )
        return ForecastResponse(**forecast_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weather service error: {str(e)}")


@router.get("/cities")
async def get_supported_cities():
    """지원되는 도시 목록 조회 (주요 도시들)"""
    cities = [
        {"name": "Seoul", "country": "KR", "region": "Seoul"},
        {"name": "Busan", "country": "KR", "region": "Busan"},
        {"name": "Incheon", "country": "KR", "region": "Incheon"},
        {"name": "Daegu", "country": "KR", "region": "Daegu"},
        {"name": "Daejeon", "country": "KR", "region": "Daejeon"},
        {"name": "Gwangju", "country": "KR", "region": "Gwangju"},
        {"name": "Tokyo", "country": "JP", "region": "Tokyo"},
        {"name": "Osaka", "country": "JP", "region": "Osaka"},
        {"name": "New York", "country": "US", "region": "New York"},
        {"name": "Los Angeles", "country": "US", "region": "California"},
        {"name": "London", "country": "GB", "region": "England"},
        {"name": "Paris", "country": "FR", "region": "Ile-de-France"},
        {"name": "Berlin", "country": "DE", "region": "Berlin"},
        {"name": "Sydney", "country": "AU", "region": "New South Wales"},
        {"name": "Toronto", "country": "CA", "region": "Ontario"},
    ]
    return {"cities": cities}


# 인증이 필요한 보호된 엔드포인트들
@router.get("/favorites")
async def get_user_favorites(current_user: User = Depends(get_current_active_user)):
    """사용자의 즐겨찾기 도시 목록 조회"""
    # 실제 구현에서는 데이터베이스에서 사용자의 즐겨찾기 조회
    return {
        "user_id": current_user.id,
        "favorites": [
            {"city": "Seoul", "country": "KR", "added_at": "2024-01-01T00:00:00Z"},
            {"city": "Busan", "country": "KR", "added_at": "2024-01-02T00:00:00Z"},
        ],
    }


@router.post("/favorites/{city}")
async def add_favorite_city(
    city: str,
    country: str | None = Query(None, description="국가 코드"),
    current_user: User = Depends(get_current_active_user),
):
    """즐겨찾기 도시 추가"""
    # 실제 구현에서는 데이터베이스에 즐겨찾기 추가
    return {
        "message": f"Added {city} to favorites",
        "user_id": current_user.id,
        "city": city,
        "country": country,
        "added_at": "2024-01-01T00:00:00Z",
    }


@router.delete("/favorites/{city}")
async def remove_favorite_city(
    city: str, current_user: User = Depends(get_current_active_user)
):
    """즐겨찾기 도시 제거"""
    # 실제 구현에서는 데이터베이스에서 즐겨찾기 제거
    return {
        "message": f"Removed {city} from favorites",
        "user_id": current_user.id,
        "city": city,
    }


@router.get("/favorites/weather")
async def get_favorites_weather(current_user: User = Depends(get_current_active_user)):
    """즐겨찾기 도시들의 현재 날씨 조회"""
    # 실제 구현에서는 데이터베이스에서 즐겨찾기 목록을 가져와서 날씨 조회
    favorite_cities = ["Seoul", "Busan"]
    weather_data = []

    for city in favorite_cities:
        try:
            weather = await weather_service.get_current_weather(city=city, country="KR")
            weather_data.append(weather)
        except Exception:
            # 개별 도시 조회 실패 시 건너뛰기
            continue

    return {"user_id": current_user.id, "favorites_weather": weather_data}
