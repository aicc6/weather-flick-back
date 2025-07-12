"""AI 기반 여행 추천 서비스"""
import os
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta
from openai import OpenAI
from sqlalchemy.orm import Session
from app.models import (
    TouristAttraction,
    CulturalFacility,
    Restaurant,
    Shopping,
    CustomTravelRecommendationRequest,
    PlaceRecommendation,
    DayItinerary
)
from app.services.kma_weather_service import KMAWeatherService
from app.utils.kma_utils import get_city_coordinates

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AIRecommendationService:
    """AI 기반 여행 추천 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self.weather_service = KMAWeatherService()

    async def generate_travel_itinerary(
        self,
        request: CustomTravelRecommendationRequest,
        places: List[Dict[str, Any]]
    ) -> List[DayItinerary]:
        """AI를 사용하여 최적화된 여행 일정 생성"""

        # 날씨 정보 가져오기
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"날씨 정보 조회 시작: {request.region_name}, {request.days}일")
        weather_data = await self.get_weather_forecast(request.region_name, request.days)
        logger.info(f"날씨 정보 조회 완료: {weather_data}")

        # 프롬프트 생성 (날씨 정보 포함)
        prompt = self._create_itinerary_prompt(request, places, weather_data)

        try:
            # OpenAI API 호출
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 한국 여행 전문가입니다. 사용자의 취향과 상황에 맞는 최적의 여행 일정을 만들어주세요. 각 일차마다 관광지, 문화시설, 음식점, 쇼핑 등 다양한 유형의 장소를 조합해주세요. 특히 점심 시간에는 반드시 음식점을 포함시켜주세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )

            # AI 응답 파싱
            ai_response = response.choices[0].message.content
            logger.info(f"AI 응답: {ai_response[:500]}...")  # 디버깅용
            itinerary_data = self._parse_ai_response(ai_response)

            # DayItinerary 객체로 변환 (날씨 정보 포함)
            return self._create_day_itineraries(itinerary_data, places, request, weather_data)

        except Exception as e:
            print(f"AI 추천 생성 중 오류: {str(e)}")
            # 폴백: 기존 태그 기반 추천 사용
            return self._fallback_recommendation(request, places)

    def _create_itinerary_prompt(
        self,
        request: CustomTravelRecommendationRequest,
        places: List[Dict[str, Any]],
        weather_data: Dict[str, Any]
    ) -> str:
        """AI 프롬프트 생성"""

        # 장소 정보 요약 (타입별로 분류)
        place_info = []
        places_by_type = {'attraction': [], 'cultural': [], 'restaurant': [], 'shopping': []}

        # 먼저 상위 장소들을 타입별로 분류
        for i, place in enumerate(places[:100]):  # 상위 100개에서 선택
            place_type = place.get('type', 'other')
            if place_type in places_by_type and len(places_by_type[place_type]) < 15:
                places_by_type[place_type].append((i, place))

        # 각 타입이 충분하지 않으면 전체에서 추가로 가져오기
        for place_type in places_by_type:
            if len(places_by_type[place_type]) < 5:
                for i, place in enumerate(places):
                    if place.get('type') == place_type and (i, place) not in places_by_type[place_type]:
                        places_by_type[place_type].append((i, place))
                        if len(places_by_type[place_type]) >= 10:
                            break

        # 각 타입별로 장소 정보 추가
        for place_type, type_places in places_by_type.items():
            type_name = {
                'attraction': '관광지',
                'cultural': '문화시설',
                'restaurant': '음식점',
                'shopping': '쇼핑'
            }.get(place_type, place_type)

            if type_places:
                place_info.append(f"\n[{type_name}]")
                for idx, (i, place) in enumerate(type_places[:10]):
                    info = f"{i+1}. {place['name']}"
                    if place.get('tags'):
                        info += f" - 태그: {', '.join(place['tags'][:3])}"
                    if place.get('address'):
                        addr_parts = place['address'].split()
                        info += f" - 위치: {addr_parts[1] if len(addr_parts) > 1 else place['address']}"
                    place_info.append(info)

        # 날씨 정보 요약
        weather_info = []
        if weather_data.get('daily_forecast'):
            for i, day_weather in enumerate(weather_data['daily_forecast'][:request.days]):
                weather_info.append(
                    f"- {i+1}일차: {day_weather.get('sky', '맑음')}, "
                    f"기온 {day_weather.get('temperature_min', 15)}-{day_weather.get('temperature_max', 25)}°C, "
                    f"강수확률 {day_weather.get('rain_probability', 0)}%"
                )

        prompt = f"""
다음 정보를 바탕으로 {request.days}일간의 여행 일정을 만들어주세요:

여행 정보:
- 지역: {request.region_name}
- 기간: {request.period} ({request.days}일)
- 동행자: {request.who}
- 선호 스타일: {', '.join(request.styles)}
- 일정 스타일: {request.schedule} ({'빡빡한 일정' if request.schedule == 'packed' else '여유로운 일정'})

날씨 예보:
{chr(10).join(weather_info) if weather_info else '날씨 정보 없음'}
- 전반적 예보: {weather_data.get('forecast', '대체로 맑음')}
- 날씨 권장사항: {weather_data.get('recommendation', '야외 활동하기 좋은 날씨입니다')}

사용 가능한 장소들:
{chr(10).join(place_info)}

요구사항:
1. 하루에 {4 if request.schedule == 'packed' else 3}개의 장소를 배치해주세요
2. 점심시간(12:00-14:00)에는 반드시 음식점을 포함해주세요
3. 이동 동선을 고려하여 효율적으로 배치해주세요 (같은 구/지역 우선)
4. 동행자 유형과 여행 스타일에 맞는 장소를 우선 선택해주세요
5. 각 일차별로 테마가 있도록 구성해주세요
6. 날씨를 고려하여 비 오는 날은 실내 활동 위주로 배치해주세요
7. 장소 타입을 다양하게 섞어주세요 (관광지, 문화시설, 쇼핑 등)
8. 오전에는 관광지나 문화시설, 오후에는 쇼핑이나 카페 등을 배치해주세요

응답 형식 (JSON):
{{
    "days": [
        {{
            "day": 1,
            "theme": "첫날 테마",
            "weather_consideration": "날씨를 고려한 설명",
            "places": [
                {{
                    "place_index": 1,  // 위 목록에서 선택한 장소의 번호
                    "time_slot": "09:00-11:00",
                    "reason": "선택 이유"
                }},
                {{
                    "place_index": 25,  // 음식점 선택 예시
                    "time_slot": "12:00-14:00",
                    "reason": "점심 식사"
                }},
                {{
                    "place_index": 15,  // 오후 관광지
                    "time_slot": "15:00-17:00",
                    "reason": "오후 활동"
                }}
            ]
        }}
    ],
    "tips": ["여행 팁 1", "여행 팁 2"]
}}

주의: 각 장소의 place_index는 위에 제공된 장소 목록의 실제 번호여야 합니다.
"""
        return prompt

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """AI 응답 파싱"""
        try:
            # JSON 부분 추출
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
        except:
            pass

        # 파싱 실패 시 빈 구조 반환
        return {"days": [], "tips": []}

    def _create_day_itineraries(
        self,
        itinerary_data: Dict[str, Any],
        places: List[Dict[str, Any]],
        request: CustomTravelRecommendationRequest,
        weather_data: Dict[str, Any]
    ) -> List[DayItinerary]:
        """AI 응답을 DayItinerary 객체로 변환"""

        days = []
        used_places = set()
        daily_forecast = weather_data.get('daily_forecast', [])

        for day_data in itinerary_data.get("days", []):
            day_places = []
            day_num = day_data.get("day", len(days) + 1)

            for place_data in day_data.get("places", []):
                place_idx = place_data.get("place_index", 0) - 1

                if 0 <= place_idx < len(places) and place_idx not in used_places:
                    place = places[place_idx]
                    used_places.add(place_idx)

                    place_rec = PlaceRecommendation(
                        id=place['id'],
                        name=place['name'],
                        time=place_data.get("time_slot", "10:00-12:00"),
                        tags=place.get('tags', [])[:3],
                        description=place.get('description', ''),
                        rating=place.get('rating', 4.0),
                        image=place.get('image'),
                        address=place.get('address'),
                        latitude=place.get('latitude'),
                        longitude=place.get('longitude')
                    )
                    day_places.append(place_rec)

            # 해당 날짜의 날씨 정보 가져오기
            day_weather = {}
            if day_num <= len(daily_forecast):
                forecast = daily_forecast[day_num - 1]
                day_weather = {
                    "status": forecast.get('sky', '맑음'),
                    "temperature": f"{forecast.get('temperature_min', 15)}-{forecast.get('temperature_max', 25)}°C",
                    "rain_probability": forecast.get('rain_probability', 0)
                }

                # 비 확률이 높으면 경고 추가
                if forecast.get('rain_probability', 0) > 60:
                    day_weather["warning"] = "우산을 준비하세요"
            else:
                # 기본 날씨 정보
                day_weather = {"status": "맑음", "temperature": "15-22°C"}

            if day_places:
                day_itinerary = DayItinerary(
                    day=day_num,
                    places=day_places,
                    weather=day_weather
                )
                days.append(day_itinerary)

        # 부족한 일수 채우기
        while len(days) < request.days:
            days.extend(self._fallback_recommendation(request, places, start_day=len(days) + 1))

        return days[:request.days]

    def _fallback_recommendation(
        self,
        request: CustomTravelRecommendationRequest,
        places: List[Dict[str, Any]],
        start_day: int = 1
    ) -> List[DayItinerary]:
        """폴백 추천 (기존 로직)"""

        places_per_day = 4 if request.schedule == "packed" else 3
        days = []
        used_places = set()

        for day in range(start_day, request.days + 1):
            day_places = []

            # 시간대 설정
            if request.schedule == "packed":
                time_slots = ["09:00-11:00", "11:30-13:30", "14:00-16:00", "16:30-18:30"]
            else:
                time_slots = ["10:00-12:00", "14:00-16:00", "17:00-19:00"]

            for i, time_slot in enumerate(time_slots[:places_per_day]):
                # 점심시간대 음식점 우선
                if i == 1 or (i == 2 and request.schedule == "relaxed"):
                    for place in places:
                        if place['type'] == 'restaurant' and place['id'] not in used_places:
                            place_rec = PlaceRecommendation(
                                id=place['id'],
                                name=place['name'],
                                time=time_slot,
                                tags=place.get('tags', [])[:3],
                                description=place.get('description', ''),
                                rating=place.get('rating', 4.0),
                                image=place.get('image'),
                                address=place.get('address'),
                                latitude=place.get('latitude'),
                                longitude=place.get('longitude')
                            )
                            day_places.append(place_rec)
                            used_places.add(place['id'])
                            break
                    if len(day_places) > i:
                        continue

                # 일반 장소 선택
                for place in places:
                    if place['id'] not in used_places:
                        place_rec = PlaceRecommendation(
                            id=place['id'],
                            name=place['name'],
                            time=time_slot,
                            tags=place.get('tags', [])[:3],
                            description=place.get('description', ''),
                            rating=place.get('rating', 4.0),
                            image=place.get('image'),
                            address=place.get('address'),
                            latitude=place.get('latitude'),
                            longitude=place.get('longitude')
                        )
                        day_places.append(place_rec)
                        used_places.add(place['id'])
                        break

            if day_places:
                day_itinerary = DayItinerary(
                    day=day,
                    places=day_places,
                    weather={"status": "맑음", "temperature": "15-22°C"}
                )
                days.append(day_itinerary)

        return days

    def enhance_with_weather_data(
        self,
        itinerary: List[DayItinerary],
        weather_data: Dict[str, Any]
    ) -> List[DayItinerary]:
        """날씨 데이터로 일정 보강"""

        # 날씨에 따른 실내/실외 장소 조정
        for day in itinerary:
            if weather_data.get("rain_expected"):
                # 비 예보시 실내 장소 우선
                day.weather = {
                    "status": "비",
                    "temperature": weather_data.get("temperature", "15-22°C"),
                    "warning": "우산을 준비하세요"
                }

        return itinerary

    async def get_weather_forecast(
        self,
        region_name: str,
        days: int
    ) -> Dict[str, Any]:
        """지역의 날씨 예보 가져오기"""
        try:
            # 지역명을 좌표로 변환
            coords = get_city_coordinates(region_name)
            if not coords:
                # 기본값 (서울)
                coords = get_city_coordinates("서울")

            # 단기 예보 가져오기 (3일)
            weather_data = await self.weather_service.get_short_forecast(
                nx=coords["nx"],
                ny=coords["ny"]
            )

            # 일별 날씨 정보 추출
            daily_weather = []

            # daily_forecast가 이미 파싱된 경우 사용
            if "daily_forecast" in weather_data and weather_data["daily_forecast"]:
                for i, day_data in enumerate(weather_data["daily_forecast"][:days]):
                    day_weather = {
                        "date": day_data.get("date", ""),
                        "temperature_min": day_data.get("min_temp", 15),
                        "temperature_max": day_data.get("max_temp", 25),
                        "sky": self._get_sky_status(day_data.get("rainfall_probability", 0)),
                        "rain_probability": day_data.get("rainfall_probability", 0)
                    }
                    daily_weather.append(day_weather)
            else:
                # forecast 원시 데이터에서 추출
                for i in range(min(days, 3)):  # 최대 3일
                    date = datetime.now() + timedelta(days=i)
                    date_str = date.strftime("%Y%m%d")

                    # 해당 날짜의 날씨 정보 찾기
                    day_weather = {
                        "date": date_str,
                        "temperature_min": 15,
                        "temperature_max": 25,
                        "sky": "맑음",
                        "rain_probability": 0
                    }

                    # weather_data에서 정보 추출
                    if "forecast" in weather_data:
                        for forecast in weather_data["forecast"]:
                            if forecast.get("fcstDate") == date_str:
                                category = forecast.get("category")
                                value = forecast.get("fcstValue")

                                if category == "TMN":  # 최저기온
                                    day_weather["temperature_min"] = float(value)
                                elif category == "TMX":  # 최고기온
                                    day_weather["temperature_max"] = float(value)
                                elif category == "SKY":  # 하늘상태
                                    sky_map = {"1": "맑음", "3": "구름많음", "4": "흐림"}
                                    day_weather["sky"] = sky_map.get(value, "맑음")
                                elif category == "POP":  # 강수확률
                                    day_weather["rain_probability"] = int(value)

                    daily_weather.append(day_weather)

            # 날씨 요약 생성
            avg_rain_prob = sum(d["rain_probability"] for d in daily_weather) / len(daily_weather) if daily_weather else 0

            weather_summary = {
                "forecast": "비 예보" if avg_rain_prob > 60 else "대체로 맑음",
                "average_temperature": f"{min(d['temperature_min'] for d in daily_weather)}-{max(d['temperature_max'] for d in daily_weather)}°C",
                "recommendation": "우산을 준비하세요" if avg_rain_prob > 60 else "야외 활동하기 좋은 날씨입니다.",
                "daily_forecast": daily_weather
            }

            return weather_summary

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"날씨 정보 조회 실패: {str(e)}")
            # 기본 날씨 정보 반환
            return {
                "forecast": "대체로 맑음",
                "average_temperature": "15-22°C",
                "recommendation": "야외 활동하기 좋은 날씨입니다.",
                "daily_forecast": []
            }

    def _get_sky_status(self, rain_probability: int) -> str:
        """강수확률에 따른 하늘 상태 반환"""
        if rain_probability >= 70:
            return "비"
        elif rain_probability >= 40:
            return "흐림"
        elif rain_probability >= 20:
            return "구름많음"
        else:
            return "맑음"
