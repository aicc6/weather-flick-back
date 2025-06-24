import httpx
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from datetime import datetime, timedelta
from app.config import settings
from app.utils.kma_utils import (
    get_base_time, convert_precipitation_type, convert_wind_direction,
    format_weather_data
)

class KMAWeatherService:
    """기상청 공공데이터포털 API 서비스"""

    def __init__(self):
        self.api_key = settings.kma_api_key
        self.base_url = "http://apis.data.go.kr/1360000"

    async def get_current_weather(self, nx: int, ny: int) -> Dict[str, Any]:
        """현재 날씨 정보 조회 (기상청)"""
        try:
            # 현재 시간 기준으로 조회
            base_date, base_time = get_base_time()

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/VilageFcstInfoService_2.0/getUltraSrtNcst",
                    params={
                        "serviceKey": self.api_key,
                        "pageNo": "1",
                        "numOfRows": "1000",
                        "dataType": "JSON",
                        "base_date": base_date,
                        "base_time": base_time,
                        "nx": nx,
                        "ny": ny
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_current_weather_kma(data, nx, ny)
                else:
                    raise HTTPException(status_code=500, detail="기상청 API 오류")

        except httpx.TimeoutException:
            raise HTTPException(status_code=408, detail="기상청 API 타임아웃")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="기상청 API 서비스 불가")

    async def get_short_forecast(self, nx: int, ny: int) -> Dict[str, Any]:
        """단기예보 조회 (3일)"""
        try:
            base_date, base_time = get_base_time()

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/VilageFcstInfoService_2.0/getVilageFcst",
                    params={
                        "serviceKey": self.api_key,
                        "pageNo": "1",
                        "numOfRows": "1000",
                        "dataType": "JSON",
                        "base_date": base_date,
                        "base_time": base_time,
                        "nx": nx,
                        "ny": ny
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_short_forecast_kma(data, nx, ny)
                else:
                    raise HTTPException(status_code=500, detail="기상청 API 오류")

        except httpx.TimeoutException:
            raise HTTPException(status_code=408, detail="기상청 API 타임아웃")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="기상청 API 서비스 불가")

    async def get_mid_forecast(self, regId: str) -> Dict[str, Any]:
        """중기예보 조회 (3~10일)"""
        try:
            now = datetime.now()
            tmFc = now.strftime("%Y%m%d0600")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/MidFcstInfoService/getMidFcst",
                    params={
                        "serviceKey": self.api_key,
                        "pageNo": "1",
                        "numOfRows": "10",
                        "dataType": "JSON",
                        "tmFc": tmFc,
                        "regId": regId
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_mid_forecast_kma(data, regId)
                else:
                    raise HTTPException(status_code=500, detail="기상청 API 오류")

        except httpx.TimeoutException:
            raise HTTPException(status_code=408, detail="기상청 API 타임아웃")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="기상청 API 서비스 불가")

    async def get_weather_warning(self, area: str) -> Dict[str, Any]:
        """기상특보 조회"""
        try:
            now = datetime.now()
            fromTmFc = (now - timedelta(days=1)).strftime("%Y%m%d")
            toTmFc = now.strftime("%Y%m%d")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/WarningInfoService/getWarningInfo",
                    params={
                        "serviceKey": self.api_key,
                        "pageNo": "1",
                        "numOfRows": "10",
                        "dataType": "JSON",
                        "fromTmFc": fromTmFc,
                        "toTmFc": toTmFc,
                        "area": area
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_weather_warning_kma(data, area)
                else:
                    raise HTTPException(status_code=500, detail="기상청 API 오류")

        except httpx.TimeoutException:
            raise HTTPException(status_code=408, detail="기상청 API 타임아웃")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="기상청 API 서비스 불가")

    def _parse_current_weather_kma(self, data: Dict[str, Any], nx: int, ny: int) -> Dict[str, Any]:
        """기상청 현재날씨 데이터 파싱"""
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        weather_data = {
            "nx": nx,
            "ny": ny,
            "temperature": 0,
            "humidity": 0,
            "rainfall": 0,
            "wind_speed": 0,
            "wind_direction": "",
            "pressure": 0,
            "visibility": 0,
            "cloud_cover": 0
        }

        for item in items:
            category = item.get("category")
            value = item.get("obsrValue", "0")

            if category == "T1H":  # 기온
                weather_data["temperature"] = float(value)
            elif category == "RN1":  # 1시간 강수량
                weather_data["rainfall"] = float(value)
            elif category == "REH":  # 습도
                weather_data["humidity"] = float(value)
            elif category == "WSD":  # 풍속
                weather_data["wind_speed"] = float(value)
            elif category == "PTY":  # 강수형태
                weather_data["precipitation_type"] = convert_precipitation_type(value)
            elif category == "VEC":  # 풍향
                weather_data["wind_direction"] = convert_wind_direction(value)
            elif category == "PCP":  # 1시간 강수량
                weather_data["rainfall"] = float(value) if value != "강수없음" else 0

        return format_weather_data(weather_data)

    def _parse_short_forecast_kma(self, data: Dict[str, Any], nx: int, ny: int) -> Dict[str, Any]:
        """기상청 단기예보 데이터 파싱"""
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        # 날짜별로 데이터 그룹화
        forecast_by_date = {}

        for item in items:
            fcst_date = item.get("fcstDate")
            fcst_time = item.get("fcstTime")
            category = item.get("category")
            value = item.get("fcstValue")

            if fcst_date not in forecast_by_date:
                forecast_by_date[fcst_date] = {}

            if fcst_time not in forecast_by_date[fcst_date]:
                forecast_by_date[fcst_date][fcst_time] = {}

            forecast_by_date[fcst_date][fcst_time][category] = value

        # 일별 요약 데이터 생성
        daily_forecast = []
        for date, times in forecast_by_date.items():
            daily_data = {
                "date": date,
                "max_temp": -999,
                "min_temp": 999,
                "avg_temp": 0,
                "rainfall_probability": 0,
                "weather_description": "",
                "wind_speed": 0
            }

            temp_count = 0
            total_temp = 0

            for time, categories in times.items():
                if "TMP" in categories:  # 기온
                    temp = float(categories["TMP"])
                    daily_data["max_temp"] = max(daily_data["max_temp"], temp)
                    daily_data["min_temp"] = min(daily_data["min_temp"], temp)
                    total_temp += temp
                    temp_count += 1

                if "POP" in categories:  # 강수확률
                    daily_data["rainfall_probability"] = max(daily_data["rainfall_probability"], int(categories["POP"]))

                if "WSD" in categories:  # 풍속
                    daily_data["wind_speed"] = max(daily_data["wind_speed"], float(categories["WSD"]))

            if temp_count > 0:
                daily_data["avg_temp"] = total_temp / temp_count

            daily_forecast.append(daily_data)

        return {
            "nx": nx,
            "ny": ny,
            "forecast": daily_forecast
        }

    def _parse_mid_forecast_kma(self, data: Dict[str, Any], regId: str) -> Dict[str, Any]:
        """기상청 중기예보 데이터 파싱"""
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        forecast_data = {
            "regId": regId,
            "forecast": []
        }

        for item in items:
            if item.get("rnSt") and item.get("rnSt") != "":  # 강수확률이 있는 경우
                forecast_data["forecast"].append({
                    "date": item.get("tmFc", "")[:8],  # YYYYMMDD
                    "weather": item.get("wfSv", ""),
                    "rainfall_probability": int(item.get("rnSt", "0")),
                    "max_temp": int(item.get("taMax", "0")),
                    "min_temp": int(item.get("taMin", "0"))
                })

        return forecast_data

    def _parse_weather_warning_kma(self, data: Dict[str, Any], area: str) -> Dict[str, Any]:
        """기상특보 데이터 파싱"""
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        warnings = []
        for item in items:
            warnings.append({
                "area": item.get("area", ""),
                "warning_type": item.get("warningType", ""),
                "warning_level": item.get("warningLevel", ""),
                "warning_message": item.get("warningMessage", ""),
                "issue_time": item.get("issueTime", ""),
                "cancel_time": item.get("cancelTime", "")
            })

        return {
            "area": area,
            "warnings": warnings
        }

# 서비스 인스턴스
kma_weather_service = KMAWeatherService()
