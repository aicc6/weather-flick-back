"""
실시간 정보 통합 서비스
영업시간, 혼잡도, 날씨 변화, 특별 이벤트 등의 실시간 정보를 통합 관리
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings
from app.utils.cache_decorator import cache_result
from app.services.google_places_service import google_places_service
from app.services.weather_service import weather_service
import logging
import random
import hashlib

logger = logging.getLogger(__name__)


class RealtimeInfoService:
    """실시간 정보 통합 서비스"""
    
    def __init__(self):
        self.google_api_key = getattr(settings, 'google_api_key', None) or os.getenv('GOOGLE_MAPS_API_KEY')
        self.kakao_api_key = getattr(settings, 'kakao_local_api_key', None) or os.getenv('KAKAO_LOCAL_API_KEY')
        self.public_data_api_key = getattr(settings, 'tour_api_key', None) or os.getenv('TOUR_API_KEY')
        
    async def get_place_realtime_info(self, place_id: str) -> Dict[str, Any]:
        """
        장소의 실시간 정보 통합 조회
        
        Args:
            place_id: Google Place ID
            
        Returns:
            영업시간, 혼잡도, 실시간 상태 등의 정보
        """
        try:
            # Google Places API에서 상세 정보 조회
            place_details = await self._get_google_place_details(place_id)
            
            # 카카오 API에서 추가 정보 조회 (선택적)
            kakao_info = None
            if place_details and place_details.get('name'):
                kakao_info = await self._get_kakao_place_info(
                    place_details['name'],
                    place_details.get('latitude'),
                    place_details.get('longitude')
                )
            
            # 정보 통합
            return {
                'place_id': place_id,
                'name': place_details.get('name'),
                'is_open_now': place_details.get('is_open_now'),
                'opening_hours': place_details.get('opening_hours'),
                'current_opening_hours': place_details.get('current_opening_hours'),
                'popular_times': place_details.get('popular_times'),
                'current_popularity': place_details.get('current_popularity'),
                'wait_time': place_details.get('wait_time'),
                'phone_number': place_details.get('phone_number'),
                'website': place_details.get('website'),
                'price_level': place_details.get('price_level'),
                'rating': place_details.get('rating'),
                'user_ratings_total': place_details.get('user_ratings_total'),
                'business_status': place_details.get('business_status'),
                'kakao_info': kakao_info,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting realtime info for place {place_id}: {str(e)}")
            return {
                'place_id': place_id,
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }
    
    async def _get_google_place_details(self, place_id: str) -> Dict[str, Any]:
        """Google Places API에서 상세 정보 조회"""
        if not self.google_api_key:
            logger.warning("Google API key not configured")
            return {}
            
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            'place_id': place_id,
            'fields': (
                'name,formatted_address,geometry,place_id,'
                'opening_hours,current_opening_hours,business_status,'
                'formatted_phone_number,website,price_level,rating,'
                'user_ratings_total,utc_offset_minutes'
            ),
            'key': self.google_api_key,
            'language': 'ko'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and 'result' in data:
                    result = data['result']
                    geometry = result.get('geometry', {})
                    location = geometry.get('location', {})
                    
                    # 영업 시간 파싱
                    opening_hours = result.get('opening_hours', {})
                    current_opening_hours = result.get('current_opening_hours', {})
                    
                    return {
                        'place_id': result.get('place_id'),
                        'name': result.get('name'),
                        'formatted_address': result.get('formatted_address'),
                        'latitude': location.get('lat'),
                        'longitude': location.get('lng'),
                        'is_open_now': opening_hours.get('open_now'),
                        'opening_hours': opening_hours.get('weekday_text', []),
                        'current_opening_hours': current_opening_hours.get('weekday_text', []),
                        'phone_number': result.get('formatted_phone_number'),
                        'website': result.get('website'),
                        'price_level': result.get('price_level'),
                        'rating': result.get('rating'),
                        'user_ratings_total': result.get('user_ratings_total'),
                        'business_status': result.get('business_status', 'OPERATIONAL'),
                        'utc_offset_minutes': result.get('utc_offset_minutes', 540)  # 한국 기본값
                    }
        
        return {}
    
    async def _get_kakao_place_info(self, place_name: str, lat: float = None, lon: float = None) -> Dict[str, Any]:
        """카카오 로컬 API에서 장소 정보 조회"""
        if not self.kakao_api_key:
            return None
            
        headers = {
            'Authorization': f'KakaoAK {self.kakao_api_key}'
        }
        
        # 키워드로 장소 검색
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        params = {
            'query': place_name,
            'size': 1
        }
        
        if lat and lon:
            params['x'] = lon
            params['y'] = lat
            params['radius'] = 1000  # 1km 반경
            params['sort'] = 'distance'
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params, timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    documents = data.get('documents', [])
                    
                    if documents:
                        place = documents[0]
                        return {
                            'place_name': place.get('place_name'),
                            'category_name': place.get('category_name'),
                            'phone': place.get('phone'),
                            'place_url': place.get('place_url'),
                            'road_address': place.get('road_address_name'),
                            'address': place.get('address_name')
                        }
        except Exception as e:
            logger.error(f"Error getting Kakao place info: {str(e)}")
            
        return None
    
    @cache_result(prefix="holidays", expire=86400)  # 24시간 캐싱
    async def get_holidays(self, year: int, month: int = None) -> List[Dict[str, Any]]:
        """
        공휴일 정보 조회
        
        Args:
            year: 연도
            month: 월 (선택적)
            
        Returns:
            공휴일 목록
        """
        if not self.public_data_api_key:
            return []
            
        url = "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo"
        params = {
            'serviceKey': self.public_data_api_key,
            'solYear': year,
            '_type': 'json',
            'numOfRows': 50
        }
        
        if month:
            params['solMonth'] = f"{month:02d}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
                    
                    # 단일 항목인 경우 리스트로 변환
                    if isinstance(items, dict):
                        items = [items]
                    
                    holidays = []
                    for item in items:
                        holidays.append({
                            'date': str(item.get('locdate')),
                            'name': item.get('dateName'),
                            'is_holiday': item.get('isHoliday') == 'Y'
                        })
                    
                    return holidays
        except Exception as e:
            logger.error(f"Error getting holidays: {str(e)}")
            
        return []
    
    def _generate_mock_place_details(self, place_id: str) -> Dict[str, Any]:
        """Google API 키가 없을 때 사용할 Mock 데이터 생성"""
        # place_id를 시드로 사용하여 일관된 랜덤 데이터 생성
        seed = int(hashlib.md5(place_id.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # 장소 유형별 샘플 이름
        place_names = [
            "서울타워", "경복궁", "북촌한옥마을", "명동거리", "인사동",
            "남산공원", "청계천", "동대문디자인플라자", "이태원", "홍대거리",
            "롯데월드타워", "코엑스", "강남역", "가로수길", "성수동카페거리"
        ]
        
        name = random.choice(place_names)
        
        # 영업시간 생성
        is_24_hours = random.random() < 0.1  # 10% 확률로 24시간 영업
        if is_24_hours:
            opening_hours = ["월요일: 24시간 영업", "화요일: 24시간 영업", "수요일: 24시간 영업",
                           "목요일: 24시간 영업", "금요일: 24시간 영업", "토요일: 24시간 영업", 
                           "일요일: 24시간 영업"]
            is_open_now = True
        else:
            # 일반 영업시간
            open_hour = random.choice([8, 9, 10, 11])
            close_hour = random.choice([18, 19, 20, 21, 22])
            weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일"]
            weekend = ["토요일", "일요일"]
            
            opening_hours = []
            for day in weekdays:
                opening_hours.append(f"{day}: 오전 {open_hour}시 – 오후 {close_hour - 12}시")
            
            # 주말은 약간 다른 시간
            weekend_open = open_hour + random.choice([-1, 0, 1])
            weekend_close = close_hour + random.choice([-1, 0, 1])
            for day in weekend:
                if random.random() > 0.2:  # 80% 확률로 주말 영업
                    opening_hours.append(f"{day}: 오전 {weekend_open}시 – 오후 {weekend_close - 12}시")
                else:
                    opening_hours.append(f"{day}: 휴무일")
            
            # 현재 영업 여부 계산
            now = datetime.now()
            current_hour = now.hour
            current_day = now.weekday()
            
            if current_day < 5:  # 평일
                is_open_now = open_hour <= current_hour < close_hour
            else:  # 주말
                is_open_now = weekend_open <= current_hour < weekend_close and random.random() > 0.2
        
        # 주소 생성
        districts = ["종로구", "중구", "용산구", "성동구", "광진구", "동대문구", 
                    "중랑구", "성북구", "강북구", "도봉구", "노원구", "은평구",
                    "서대문구", "마포구", "양천구", "강서구", "구로구", "금천구",
                    "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구", "강동구"]
        
        district = random.choice(districts)
        street_num = random.randint(1, 999)
        
        return {
            'place_id': place_id,
            'name': name,
            'formatted_address': f"서울특별시 {district} {name}로 {street_num}",
            'latitude': 37.5665 + random.uniform(-0.1, 0.1),  # 서울 근처 위도
            'longitude': 126.9780 + random.uniform(-0.1, 0.1),  # 서울 근처 경도
            'is_open_now': is_open_now,
            'opening_hours': opening_hours,
            'current_opening_hours': opening_hours,  # 실제로는 다를 수 있지만 Mock에서는 동일
            'phone_number': f"02-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            'website': f"https://www.{name.replace(' ', '').lower()}.co.kr" if random.random() > 0.3 else None,
            'price_level': random.randint(1, 4),
            'rating': round(random.uniform(3.5, 4.9), 1),
            'user_ratings_total': random.randint(100, 5000),
            'business_status': 'OPERATIONAL' if random.random() > 0.05 else 'CLOSED_TEMPORARILY',
            'utc_offset_minutes': 540  # 한국 시간대
        }
    
    async def check_itinerary_conflicts(self, itinerary: Dict[str, List[Dict]], check_date: datetime = None) -> Dict[str, Any]:
        """
        여행 일정의 실시간 충돌 검사
        
        Args:
            itinerary: 여행 일정
            check_date: 검사 기준 날짜 (기본값: 오늘)
            
        Returns:
            충돌 정보 및 대안
        """
        if check_date is None:
            check_date = datetime.now()
            
        conflicts = []
        alternatives = {}
        
        for day_key, places in itinerary.items():
            day_conflicts = []
            
            for place in places:
                place_id = place.get('place_id')
                if not place_id:
                    continue
                    
                # 실시간 정보 조회
                realtime_info = await self.get_place_realtime_info(place_id)
                
                # 영업 상태 확인
                if realtime_info.get('business_status') == 'CLOSED_PERMANENTLY':
                    day_conflicts.append({
                        'place': place,
                        'issue': 'permanently_closed',
                        'message': f"{place.get('name')}은(는) 영구 폐업했습니다."
                    })
                elif realtime_info.get('business_status') == 'CLOSED_TEMPORARILY':
                    day_conflicts.append({
                        'place': place,
                        'issue': 'temporarily_closed',
                        'message': f"{place.get('name')}은(는) 임시 휴업 중입니다."
                    })
                elif realtime_info.get('is_open_now') is False:
                    # 방문 시간대 영업 여부 확인
                    visit_time = place.get('visit_time', '14:00')
                    day_conflicts.append({
                        'place': place,
                        'issue': 'closed_at_visit_time',
                        'message': f"{place.get('name')}은(는) {visit_time}에 영업하지 않습니다.",
                        'opening_hours': realtime_info.get('opening_hours', [])
                    })
                
                # 혼잡도 확인 (향후 Popular Times API 활용)
                if realtime_info.get('current_popularity'):
                    popularity = realtime_info['current_popularity']
                    if popularity > 80:  # 매우 혼잡
                        day_conflicts.append({
                            'place': place,
                            'issue': 'very_crowded',
                            'message': f"{place.get('name')}은(는) 현재 매우 혼잡합니다.",
                            'popularity': popularity
                        })
            
            if day_conflicts:
                conflicts.extend(day_conflicts)
                # 대안 제시 로직 추가 예정
        
        return {
            'has_conflicts': len(conflicts) > 0,
            'conflicts': conflicts,
            'alternatives': alternatives,
            'checked_at': datetime.now().isoformat()
        }
    
    async def get_weather_alerts(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """
        날씨 특보 및 경고 정보 조회
        
        Args:
            lat: 위도
            lon: 경도
            
        Returns:
            날씨 경고 목록
        """
        # 기상청 API 또는 다른 날씨 API를 통해 특보 정보 조회
        # 현재는 기본 구현
        alerts = []
        
        # weather_service를 통해 현재 날씨 조회
        try:
            # 좌표를 도시명으로 변환 (간단한 구현)
            city = "서울"  # 실제로는 역지오코딩 필요
            current_weather = await weather_service.get_current_weather(city)
            
            # 극한 날씨 조건 확인
            if current_weather['current']['temperature'] > 35:
                alerts.append({
                    'type': 'heat_wave',
                    'severity': 'warning',
                    'message': '폭염 경보: 야외 활동에 주의하세요.'
                })
            elif current_weather['current']['temperature'] < -10:
                alerts.append({
                    'type': 'cold_wave',
                    'severity': 'warning',
                    'message': '한파 경보: 따뜻하게 입으세요.'
                })
                
            if current_weather['current']['wind_speed'] > 50:
                alerts.append({
                    'type': 'strong_wind',
                    'severity': 'warning',
                    'message': '강풍 주의보: 야외 활동에 주의하세요.'
                })
                
        except Exception as e:
            logger.error(f"Error getting weather alerts: {str(e)}")
            
        return alerts
    
    async def suggest_alternatives(self, place: Dict[str, Any], issue_type: str) -> List[Dict[str, Any]]:
        """
        문제가 있는 장소에 대한 대안 제시
        
        Args:
            place: 원래 장소 정보
            issue_type: 문제 유형 (closed, crowded 등)
            
        Returns:
            대체 장소 목록
        """
        alternatives = []
        
        # 장소 카테고리와 위치 기반으로 대안 검색
        # Google Places Nearby Search API 활용
        if self.google_api_key and place.get('latitude') and place.get('longitude'):
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': f"{place['latitude']},{place['longitude']}",
                'radius': 5000,  # 5km 반경
                'type': place.get('type', 'tourist_attraction'),
                'language': 'ko',
                'key': self.google_api_key
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, timeout=10.0)
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get('results', [])[:5]  # 상위 5개
                        
                        for result in results:
                            if result.get('place_id') != place.get('place_id'):
                                alternatives.append({
                                    'place_id': result.get('place_id'),
                                    'name': result.get('name'),
                                    'address': result.get('vicinity'),
                                    'rating': result.get('rating'),
                                    'is_open': result.get('opening_hours', {}).get('open_now'),
                                    'reason': f"{issue_type}로 인한 대체 장소"
                                })
            except Exception as e:
                logger.error(f"Error suggesting alternatives: {str(e)}")
                
        return alternatives


# 서비스 인스턴스
realtime_info_service = RealtimeInfoService()