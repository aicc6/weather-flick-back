from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(
    prefix="/weather",
    tags=["weather"]
)

class WeatherRequest(BaseModel):
    city: str
    country: Optional[str] = None

class WeatherResponse(BaseModel):
    city: str
    temperature: float
    description: str
    humidity: int
    wind_speed: float

@router.get("/")
async def get_weather_info():
    """날씨 정보 조회"""
    return {"message": "Weather API endpoint"}

@router.post("/current", response_model=WeatherResponse)
async def get_current_weather(request: WeatherRequest):
    """현재 날씨 정보 조회"""
    # 실제 구현에서는 외부 날씨 API를 호출
    return WeatherResponse(
        city=request.city,
        temperature=22.5,
        description="맑음",
        humidity=65,
        wind_speed=3.2
    )

@router.get("/cities")
async def get_supported_cities():
    """지원되는 도시 목록 조회"""
    cities = [
        {"name": "Seoul", "country": "KR"},
        {"name": "Busan", "country": "KR"},
        {"name": "Tokyo", "country": "JP"},
        {"name": "New York", "country": "US"}
    ]
    return {"cities": cities}
