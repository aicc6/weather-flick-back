"""AI 기반 여행 추천 서비스"""
import os
import json
from typing import List, Dict, Any
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

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AIRecommendationService:
    """AI 기반 여행 추천 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def generate_travel_itinerary(
        self,
        request: CustomTravelRecommendationRequest,
        places: List[Dict[str, Any]]
    ) -> List[DayItinerary]:
        """AI를 사용하여 최적화된 여행 일정 생성"""
        
        # 프롬프트 생성
        prompt = self._create_itinerary_prompt(request, places)
        
        try:
            # OpenAI API 호출
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 한국 여행 전문가입니다. 사용자의 취향과 상황에 맞는 최적의 여행 일정을 만들어주세요."
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
            itinerary_data = self._parse_ai_response(ai_response)
            
            # DayItinerary 객체로 변환
            return self._create_day_itineraries(itinerary_data, places, request)
            
        except Exception as e:
            print(f"AI 추천 생성 중 오류: {str(e)}")
            # 폴백: 기존 태그 기반 추천 사용
            return self._fallback_recommendation(request, places)
    
    def _create_itinerary_prompt(
        self,
        request: CustomTravelRecommendationRequest,
        places: List[Dict[str, Any]]
    ) -> str:
        """AI 프롬프트 생성"""
        
        # 장소 정보 요약
        place_info = []
        for i, place in enumerate(places[:20]):  # 상위 20개만 사용
            info = f"{i+1}. {place['name']} ({place['type']})"
            if place.get('tags'):
                info += f" - 태그: {', '.join(place['tags'][:3])}"
            if place.get('address'):
                info += f" - 위치: {place['address']}"
            place_info.append(info)
        
        prompt = f"""
다음 정보를 바탕으로 {request.days}일간의 여행 일정을 만들어주세요:

여행 정보:
- 지역: {request.region_name}
- 기간: {request.period} ({request.days}일)
- 동행자: {request.who}
- 선호 스타일: {', '.join(request.styles)}
- 일정 스타일: {request.schedule} ({'빡빡한 일정' if request.schedule == 'packed' else '여유로운 일정'})

사용 가능한 장소들:
{chr(10).join(place_info)}

요구사항:
1. 하루에 {4 if request.schedule == 'packed' else 3}개의 장소를 배치해주세요
2. 점심시간(12:00-14:00)에는 반드시 음식점을 포함해주세요
3. 이동 동선을 고려하여 효율적으로 배치해주세요
4. 동행자 유형과 여행 스타일에 맞는 장소를 우선 선택해주세요
5. 각 일차별로 테마가 있도록 구성해주세요

응답 형식 (JSON):
{{
    "days": [
        {{
            "day": 1,
            "theme": "첫날 테마",
            "places": [
                {{
                    "place_index": 1,
                    "time_slot": "09:00-11:00",
                    "reason": "선택 이유"
                }}
            ]
        }}
    ],
    "tips": ["여행 팁 1", "여행 팁 2"]
}}
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
        request: CustomTravelRecommendationRequest
    ) -> List[DayItinerary]:
        """AI 응답을 DayItinerary 객체로 변환"""
        
        days = []
        used_places = set()
        
        for day_data in itinerary_data.get("days", []):
            day_places = []
            
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
            
            if day_places:
                day_itinerary = DayItinerary(
                    day=day_data.get("day", len(days) + 1),
                    places=day_places,
                    weather={"status": "맑음", "temperature": "15-22°C"}
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