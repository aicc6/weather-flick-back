import httpx
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from app.config import settings

class AirQualityService:
    def __init__(self):
        self.public_data_api_key = getattr(settings, 'public_data_api_key', None)
        self.weather_api_key = getattr(settings, 'weather_api_key', None)
        self.weather_api_url = getattr(settings, 'weather_api_url', 'http://api.weatherapi.com/v1')

    async def get_current_air_quality(self, city: str) -> Optional[Dict]:
        """현재 대기질 정보 조회"""
        # 공공데이터포털 API 우선 사용
        if self.public_data_api_key:
            result = await self._get_public_data_air_quality(city)
            if result:
                return result

        # WeatherAPI 대기질 정보 사용
        if self.weather_api_key:
            result = await self._get_weather_api_air_quality(city)
            if result:
                return result

        # 내장 데이터 사용
        return await self._get_local_air_quality(city)

    async def get_air_quality_forecast(self, city: str) -> Optional[Dict]:
        """대기질 예보 조회"""
        if self.public_data_api_key:
            return await self._get_public_data_forecast(city)
        else:
            return await self._get_local_forecast(city)

    async def get_nearby_stations(self, latitude: float, longitude: float, radius: float = 5000) -> List[Dict]:
        """주변 측정소 조회"""
        if self.public_data_api_key:
            return await self._get_public_data_stations(latitude, longitude, radius)
        else:
            return await self._get_local_stations(latitude, longitude, radius)

    async def _get_weather_api_air_quality(self, city: str) -> Optional[Dict]:
        """WeatherAPI를 사용한 대기질 정보 조회"""
        if not self.weather_api_key:
            return None

        async with httpx.AsyncClient() as client:
            params = {
                "key": self.weather_api_key,
                "q": city,
                "aqi": "yes"  # 대기질 정보 포함
            }

            try:
                response = await client.get(
                    f"{self.weather_api_url}/current.json",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                current = data.get("current", {})
                air_quality = current.get("air_quality", {})

                if not air_quality:
                    return None

                # WeatherAPI의 AQI를 한국 기준으로 변환
                us_aqi = air_quality.get("us-epa-index", 0)
                korean_grade = self._convert_us_aqi_to_korean(us_aqi)

                return {
                    "city": city,
                    "source": "WeatherAPI",
                    "timestamp": datetime.now().isoformat(),
                    "pm10": {
                        "value": air_quality.get("pm10", 0),
                        "grade": korean_grade,
                        "unit": "㎍/㎥"
                    },
                    "pm25": {
                        "value": air_quality.get("pm2_5", 0),
                        "grade": korean_grade,
                        "unit": "㎍/㎥"
                    },
                    "o3": {
                        "value": air_quality.get("o3", 0),
                        "grade": korean_grade,
                        "unit": "ppm"
                    },
                    "no2": {
                        "value": air_quality.get("no2", 0),
                        "grade": korean_grade,
                        "unit": "ppm"
                    },
                    "co": {
                        "value": air_quality.get("co", 0),
                        "grade": korean_grade,
                        "unit": "ppm"
                    },
                    "so2": {
                        "value": air_quality.get("so2", 0),
                        "grade": korean_grade,
                        "unit": "ppm"
                    },
                    "air_quality_index": {
                        "value": us_aqi,
                        "grade": korean_grade,
                        "color": self._get_grade_color(korean_grade)
                    },
                    "station_name": f"{city} WeatherAPI",
                    "latitude": data.get("location", {}).get("lat"),
                    "longitude": data.get("location", {}).get("lon")
                }
            except Exception as e:
                print(f"WeatherAPI 대기질 API 오류: {e}")
                return None

    async def _get_public_data_air_quality(self, city: str) -> Optional[Dict]:
        """공공데이터포털 API를 사용한 대기질 정보 조회"""
        if not self.public_data_api_key:
            return None

        # 측정소 코드 매핑
        station_codes = {
            "서울": "111001", "부산": "261001", "대구": "271001", "인천": "281001",
            "광주": "291001", "대전": "301001", "울산": "311001", "세종": "361001"
        }

        station_code = station_codes.get(city, "111001")  # 기본값: 서울

        async with httpx.AsyncClient() as client:
            params = {
                "serviceKey": self.public_data_api_key,
                "returnType": "json",
                "numOfRows": 1,
                "pageNo": 1,
                "stationName": station_code,
                "dataTerm": "DAILY",
                "ver": "1.4"
            }

            try:
                response = await client.get(
                    "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                items = data.get("response", {}).get("body", {}).get("items", [])
                if not items:
                    return None

                item = items[0]

                return {
                    "city": city,
                    "source": "공공데이터포털",
                    "timestamp": datetime.now().isoformat(),
                    "pm10": {
                        "value": float(item.get("pm10Value", 0)),
                        "grade": item.get("pm10Grade1h", ""),
                        "unit": "㎍/㎥"
                    },
                    "pm25": {
                        "value": float(item.get("pm25Value", 0)),
                        "grade": item.get("pm25Grade1h", ""),
                        "unit": "㎍/㎥"
                    },
                    "o3": {
                        "value": float(item.get("o3Value", 0)),
                        "grade": item.get("o3Grade", ""),
                        "unit": "ppm"
                    },
                    "no2": {
                        "value": float(item.get("no2Value", 0)),
                        "grade": item.get("no2Grade", ""),
                        "unit": "ppm"
                    },
                    "co": {
                        "value": float(item.get("coValue", 0)),
                        "grade": item.get("coGrade", ""),
                        "unit": "ppm"
                    },
                    "so2": {
                        "value": float(item.get("so2Value", 0)),
                        "grade": item.get("so2Grade", ""),
                        "unit": "ppm"
                    },
                    "air_quality_index": self._calculate_aqi(item),
                    "station_name": item.get("stationName", ""),
                    "latitude": None,
                    "longitude": None
                }
            except Exception as e:
                print(f"공공데이터포털 API 오류: {e}")
                return None

    async def _get_local_air_quality(self, city: str) -> Optional[Dict]:
        """내장 대기질 데이터"""
        air_quality_data = {
            "서울": {
                "pm10": {"value": 45, "grade": "보통", "unit": "㎍/㎥"},
                "pm25": {"value": 25, "grade": "보통", "unit": "㎍/㎥"},
                "o3": {"value": 0.03, "grade": "좋음", "unit": "ppm"},
                "no2": {"value": 0.02, "grade": "좋음", "unit": "ppm"},
                "co": {"value": 0.5, "grade": "좋음", "unit": "ppm"},
                "so2": {"value": 0.005, "grade": "좋음", "unit": "ppm"}
            },
            "부산": {
                "pm10": {"value": 35, "grade": "좋음", "unit": "㎍/㎥"},
                "pm25": {"value": 20, "grade": "좋음", "unit": "㎍/㎥"},
                "o3": {"value": 0.025, "grade": "좋음", "unit": "ppm"},
                "no2": {"value": 0.015, "grade": "좋음", "unit": "ppm"},
                "co": {"value": 0.4, "grade": "좋음", "unit": "ppm"},
                "so2": {"value": 0.004, "grade": "좋음", "unit": "ppm"}
            },
            "대구": {
                "pm10": {"value": 55, "grade": "보통", "unit": "㎍/㎥"},
                "pm25": {"value": 30, "grade": "보통", "unit": "㎍/㎥"},
                "o3": {"value": 0.035, "grade": "보통", "unit": "ppm"},
                "no2": {"value": 0.025, "grade": "보통", "unit": "ppm"},
                "co": {"value": 0.6, "grade": "보통", "unit": "ppm"},
                "so2": {"value": 0.006, "grade": "보통", "unit": "ppm"}
            }
        }

        data = air_quality_data.get(city)
        if not data:
            return None

        return {
            "city": city,
            "source": "내장 데이터",
            "timestamp": datetime.now().isoformat(),
            **data,
            "air_quality_index": self._calculate_local_aqi(data),
            "station_name": f"{city} 측정소",
            "latitude": None,
            "longitude": None
        }

    async def _get_public_data_forecast(self, city: str) -> Optional[Dict]:
        """공공데이터포털 API를 사용한 대기질 예보 조회"""
        if not self.public_data_api_key:
            return None

        async with httpx.AsyncClient() as client:
            params = {
                "serviceKey": self.public_data_api_key,
                "returnType": "json",
                "numOfRows": 24,
                "pageNo": 1,
                "searchDate": datetime.now().strftime("%Y%m%d"),
                "InformCode": "PM10"
            }

            try:
                response = await client.get(
                    "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMinuDustFrcstDspth",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                items = data.get("response", {}).get("body", {}).get("items", [])

                return {
                    "city": city,
                    "source": "공공데이터포털",
                    "forecast_date": datetime.now().strftime("%Y-%m-%d"),
                    "forecasts": [
                        {
                            "date": item.get("dataTime", ""),
                            "pm10_grade": item.get("pm10Grade", ""),
                            "pm25_grade": item.get("pm25Grade", ""),
                            "pm10_value": item.get("pm10Value", ""),
                            "pm25_value": item.get("pm25Value", "")
                        }
                        for item in items
                    ]
                }
            except Exception as e:
                print(f"공공데이터포털 예보 API 오류: {e}")
                return None

    async def _get_local_forecast(self, city: str) -> Optional[Dict]:
        """내장 대기질 예보 데이터"""
        return {
            "city": city,
            "source": "내장 데이터",
            "forecast_date": datetime.now().strftime("%Y-%m-%d"),
            "forecasts": [
                {
                    "date": (datetime.now() + timedelta(hours=i)).strftime("%Y-%m-%d %H:00"),
                    "pm10_grade": "보통",
                    "pm25_grade": "보통",
                    "pm10_value": "45",
                    "pm25_value": "25"
                }
                for i in range(24)
            ]
        }

    async def _get_public_data_stations(self, latitude: float, longitude: float, radius: float) -> List[Dict]:
        """공공데이터포털 API를 사용한 측정소 조회"""
        if not self.public_data_api_key:
            return []

        async with httpx.AsyncClient() as client:
            params = {
                "serviceKey": self.public_data_api_key,
                "returnType": "json",
                "numOfRows": 100,
                "pageNo": 1
            }

            try:
                response = await client.get(
                    "http://apis.data.go.kr/B552584/MsrstnInfoInqireSvc/getNearbyMsrstnList",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                items = data.get("response", {}).get("body", {}).get("items", [])

                return [
                    {
                        "station_name": item.get("stationName", ""),
                        "address": item.get("addr", ""),
                        "latitude": float(item.get("dmX", 0)),
                        "longitude": float(item.get("dmY", 0)),
                        "distance": float(item.get("tm", 0))
                    }
                    for item in items
                ]
            except Exception as e:
                print(f"공공데이터포털 측정소 API 오류: {e}")
                return []

    async def _get_local_stations(self, latitude: float, longitude: float, radius: float) -> List[Dict]:
        """내장 측정소 데이터"""
        stations_data = {
            "서울": [
                {
                    "station_name": "종로구",
                    "address": "서울특별시 종로구",
                    "latitude": 37.5704,
                    "longitude": 126.9997,
                    "distance": 0.5
                }
            ],
            "부산": [
                {
                    "station_name": "해운대구",
                    "address": "부산광역시 해운대구",
                    "latitude": 35.1586,
                    "longitude": 129.1603,
                    "distance": 0.3
                }
            ]
        }

        # 간단한 거리 계산 (실제로는 더 정교한 계산 필요)
        for city, stations in stations_data.items():
            for station in stations:
                station_lat, station_lng = station["latitude"], station["longitude"]
                distance = ((latitude - station_lat) ** 2 + (longitude - station_lng) ** 2) ** 0.5 * 111000  # km
                station["distance"] = distance

        return stations_data.get("서울", [])

    def _convert_us_aqi_to_korean(self, us_aqi: int) -> str:
        """미국 AQI를 한국 대기질 등급으로 변환"""
        if us_aqi <= 50:
            return "좋음"
        elif us_aqi <= 100:
            return "보통"
        elif us_aqi <= 150:
            return "나쁨"
        else:
            return "매우나쁨"

    def _get_grade_color(self, grade: str) -> str:
        """등급에 따른 색상 반환"""
        colors = {
            "좋음": "#00E400",
            "보통": "#FFFF00",
            "나쁨": "#FF7E00",
            "매우나쁨": "#FF0000"
        }
        return colors.get(grade, "#FFFF00")

    def _calculate_aqi(self, item: Dict) -> Dict:
        """공공데이터포털 데이터로 AQI 계산"""
        pm10_value = float(item.get("pm10Value", 0))
        pm25_value = float(item.get("pm25Value", 0))

        # 간단한 AQI 계산 (실제로는 더 복잡한 공식 사용)
        aqi = max(pm10_value, pm25_value * 2)

        if aqi <= 30:
            grade = "좋음"
            color = "#00E400"
        elif aqi <= 80:
            grade = "보통"
            color = "#FFFF00"
        elif aqi <= 150:
            grade = "나쁨"
            color = "#FF7E00"
        else:
            grade = "매우나쁨"
            color = "#FF0000"

        return {
            "value": int(aqi),
            "grade": grade,
            "color": color
        }

    def _calculate_local_aqi(self, data: Dict) -> Dict:
        """내장 데이터로 AQI 계산"""
        pm10_value = data["pm10"]["value"]
        pm25_value = data["pm25"]["value"]

        aqi = max(pm10_value, pm25_value * 2)

        if aqi <= 30:
            grade = "좋음"
            color = "#00E400"
        elif aqi <= 80:
            grade = "보통"
            color = "#FFFF00"
        elif aqi <= 150:
            grade = "나쁨"
            color = "#FF7E00"
        else:
            grade = "매우나쁨"
            color = "#FF0000"

        return {
            "value": int(aqi),
            "grade": grade,
            "color": color
        }

    async def get_supported_cities(self) -> List[str]:
        """지원되는 도시 목록"""
        return ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "수원", "고양", "용인", "창원", "포항", "제주"]

air_quality_service = AirQualityService()
