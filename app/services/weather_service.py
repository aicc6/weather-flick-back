from typing import Any

import httpx
from fastapi import HTTPException

from app.config import settings
from app.utils.cache_decorator import cache_result, invalidate_cache


class WeatherService:
    def __init__(self):
        self.api_key = settings.weather_api_key
        self.base_url = settings.weather_api_url

    @cache_result(prefix="weather:current", expire=600)  # 10분 캐싱
    async def get_current_weather(
        self, city: str, country: str | None = None
    ) -> dict[str, Any]:
        """현재 날씨 정보 조회"""
        try:
            # 도시명과 국가코드를 결합
            location = f"{city},{country}" if country else city

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/current.json",
                    params={
                        "key": self.api_key,
                        "q": location,
                        "aqi": "no",  # 대기질 정보 제외
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_current_weather(data)
                elif response.status_code == 400:
                    raise HTTPException(status_code=400, detail="Invalid location")
                elif response.status_code == 401:
                    raise HTTPException(status_code=401, detail="Invalid API key")
                else:
                    raise HTTPException(status_code=500, detail="Weather API error")

        except httpx.TimeoutException:
            raise HTTPException(status_code=408, detail="Weather API timeout")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Weather API unavailable")

    @cache_result(prefix="weather:forecast", expire=1800)  # 30분 캐싱
    async def get_forecast(
        self, city: str, days: int = 3, country: str | None = None
    ) -> dict[str, Any]:
        """날씨 예보 조회"""
        try:
            location = f"{city},{country}" if country else city

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/forecast.json",
                    params={
                        "key": self.api_key,
                        "q": location,
                        "days": min(days, 14),  # 최대 14일
                        "aqi": "no",
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_forecast(data)
                else:
                    raise HTTPException(status_code=500, detail="Weather API error")

        except httpx.TimeoutException:
            raise HTTPException(status_code=408, detail="Weather API timeout")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Weather API unavailable")

    def _parse_current_weather(self, data: dict[str, Any]) -> dict[str, Any]:
        """현재 날씨 데이터 파싱"""
        location = data.get("location", {})
        current = data.get("current", {})

        return {
            "city": location.get("name", ""),
            "country": location.get("country", ""),
            "region": location.get("region", ""),
            "temperature": current.get("temp_c", 0),
            "feels_like": current.get("feelslike_c", 0),
            "description": current.get("condition", {}).get("text", ""),
            "icon": current.get("condition", {}).get("icon", ""),
            "humidity": current.get("humidity", 0),
            "wind_speed": current.get("wind_kph", 0),
            "wind_direction": current.get("wind_dir", ""),
            "pressure": current.get("pressure_mb", 0),
            "visibility": current.get("vis_km", 0),
            "uv_index": current.get("uv", 0),
            "last_updated": current.get("last_updated", ""),
        }

    def _parse_forecast(self, data: dict[str, Any]) -> dict[str, Any]:
        """예보 데이터 파싱"""
        location = data.get("location", {})
        forecast = data.get("forecast", {})

        forecast_days = []
        for day in forecast.get("forecastday", []):
            day_data = day.get("day", {})
            forecast_days.append(
                {
                    "date": day.get("date", ""),
                    "max_temp": day_data.get("maxtemp_c", 0),
                    "min_temp": day_data.get("mintemp_c", 0),
                    "avg_temp": day_data.get("avgtemp_c", 0),
                    "description": day_data.get("condition", {}).get("text", ""),
                    "icon": day_data.get("condition", {}).get("icon", ""),
                    "humidity": day_data.get("avghumidity", 0),
                    "chance_of_rain": day_data.get("daily_chance_of_rain", 0),
                    "chance_of_snow": day_data.get("daily_chance_of_snow", 0),
                    "uv_index": day_data.get("uv", 0),
                }
            )

        return {
            "city": location.get("name", ""),
            "country": location.get("country", ""),
            "region": location.get("region", ""),
            "forecast": forecast_days,
        }


# 서비스 인스턴스
weather_service = WeatherService()
