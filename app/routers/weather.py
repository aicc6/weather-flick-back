from fastapi import APIRouter, Depends, HTTPException, Query
import os
import httpx

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


@router.get("/by-place-id")
async def get_weather_by_place_id(place_id: str):
    """Google place_id로 위경도 변환 후, weatherapi.com에서 날씨 조회"""
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    WEATHER_API_URL = os.getenv("WEATHER_API_URL")
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
    if not (GOOGLE_API_KEY and WEATHER_API_URL and WEATHER_API_KEY):
        raise HTTPException(status_code=500, detail="API 키 또는 URL 누락")
    # 1. place_id로 위경도 조회
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(details_url, params={
            "place_id": place_id,
            "key": GOOGLE_API_KEY,
            "fields": "geometry"
        })
        details = resp.json()
        if "result" not in details or "geometry" not in details["result"]:
            raise HTTPException(status_code=404, detail="장소 정보를 찾을 수 없음")
        location = details["result"]["geometry"]["location"]
        lat, lon = location["lat"], location["lng"]
        # 2. weatherapi.com에서 날씨 조회
        weather_resp = await client.get(
            f"{WEATHER_API_URL}/current.json",
            params={"key": WEATHER_API_KEY, "q": f"{lat},{lon}", "lang": "ko"}
        )
        if weather_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="날씨 API 호출 실패")
        weather = weather_resp.json()
        # 3. 필요한 정보만 추출
        current = weather.get("current", {})
        condition = current.get("condition", {})
        return {
            "icon": condition.get("icon"),
            "temp": current.get("temp_c"),
            "summary": condition.get("text"),
        }


@router.get("/forecast-by-place-id")
async def get_forecast_by_place_id(place_id: str, date: str):
    """Google place_id로 위경도 변환 후, 해당 날짜의 예보 반환 (최고/최저기온, 강수확률 포함)"""
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    WEATHER_API_URL = os.getenv("WEATHER_API_URL")
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
    if not (GOOGLE_API_KEY and WEATHER_API_URL and WEATHER_API_KEY):
        raise HTTPException(status_code=500, detail="API 키 또는 URL 누락")
    # 1. place_id로 위경도 조회
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(details_url, params={
            "place_id": place_id,
            "key": GOOGLE_API_KEY,
            "fields": "geometry"
        })
        details = resp.json()
        if "result" not in details or "geometry" not in details["result"]:
            raise HTTPException(status_code=404, detail="장소 정보를 찾을 수 없음")
        location = details["result"]["geometry"]["location"]
        lat, lon = location["lat"], location["lng"]
        # 2. weatherapi.com에서 예보 조회 (최대 7일)
        weather_resp = await client.get(
            f"{WEATHER_API_URL}/forecast.json",
            params={"key": WEATHER_API_KEY, "q": f"{lat},{lon}", "lang": "ko", "days": 7}
        )
        if weather_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="날씨 API 호출 실패")
        weather = weather_resp.json()
        # 3. date에 해당하는 예보만 추출
        for day in weather.get("forecast", {}).get("forecastday", []):
            if day["date"] == date:
                return {
                    "date": day["date"],
                    "icon": day["day"]["condition"]["icon"],
                    "temp": day["day"]["avgtemp_c"],
                    "max_temp": day["day"]["maxtemp_c"],
                    "min_temp": day["day"]["mintemp_c"],
                    "chance_of_rain": day["day"].get("daily_chance_of_rain", 0),
                    "summary": day["day"]["condition"]["text"],
                }
        raise HTTPException(status_code=404, detail="해당 날짜의 예보 없음")
