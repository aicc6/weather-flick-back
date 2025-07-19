"""
여행 계획 최적화 서비스
실시간 정보를 바탕으로 여행 일정을 동적으로 조정
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import logging
from app.services.realtime_info_service import realtime_info_service
from app.services.weather_service import weather_service
from app.services.route_optimizer import RouteOptimizer

logger = logging.getLogger(__name__)


class TravelPlanOptimizer:
    """여행 계획 최적화 서비스"""
    
    def __init__(self):
        self.realtime_service = realtime_info_service
        self.weather_service = weather_service
        # RouteOptimizer는 필요할 때 초기화
        self.route_optimizer = None
        
    async def optimize_daily_itinerary(
        self, 
        itinerary: Dict[str, List[Dict]], 
        date: datetime,
        preferences: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        하루 일정 최적화
        
        Args:
            itinerary: 일정 정보
            date: 여행 날짜
            preferences: 사용자 선호도
            
        Returns:
            최적화된 일정 및 변경 사항
        """
        optimized_itinerary = {}
        changes = []
        alerts = []
        
        for day_key, places in itinerary.items():
            optimized_places = []
            day_changes = []
            
            # 각 장소의 실시간 정보 수집
            places_with_info = []
            for place in places:
                place_id = place.get('place_id')
                if place_id:
                    realtime_info = await self.realtime_service.get_place_realtime_info(place_id)
                    place_with_info = {**place, 'realtime_info': realtime_info}
                    places_with_info.append(place_with_info)
                else:
                    places_with_info.append(place)
            
            # 영업시간 기반 재정렬
            sorted_places = await self._sort_by_opening_hours(places_with_info, date)
            
            # 혼잡도 기반 시간 조정
            time_adjusted_places = await self._adjust_visit_times(sorted_places, preferences)
            
            # 날씨 기반 실내/실외 조정
            weather_adjusted_places = await self._adjust_for_weather(
                time_adjusted_places, 
                date,
                places[0].get('latitude') if places else None,
                places[0].get('longitude') if places else None
            )
            
            # 경로 최적화
            if len(weather_adjusted_places) > 1:
                route_optimized = await self._optimize_route(weather_adjusted_places)
            else:
                route_optimized = weather_adjusted_places
            
            # 변경 사항 기록
            for i, (original, optimized) in enumerate(zip(places, route_optimized)):
                if original != optimized:
                    day_changes.append({
                        'original': original,
                        'optimized': optimized,
                        'reason': self._get_change_reason(original, optimized)
                    })
            
            optimized_places = route_optimized
            
            # 문제 있는 장소 처리
            final_places = []
            for place in optimized_places:
                realtime_info = place.get('realtime_info', {})
                
                # 영구 폐업 확인
                if realtime_info.get('business_status') == 'CLOSED_PERMANENTLY':
                    # 대체 장소 찾기
                    alternatives = await self.realtime_service.suggest_alternatives(
                        place, 'permanently_closed'
                    )
                    if alternatives:
                        alternative = alternatives[0]
                        final_places.append({
                            **alternative,
                            'original_place': place['name'],
                            'replacement_reason': '영구 폐업으로 인한 대체'
                        })
                        day_changes.append({
                            'type': 'replacement',
                            'original': place,
                            'new': alternative,
                            'reason': '영구 폐업'
                        })
                    else:
                        alerts.append({
                            'type': 'no_alternative',
                            'place': place['name'],
                            'message': f"{place['name']}이(가) 영구 폐업했으며 적절한 대체 장소를 찾을 수 없습니다."
                        })
                else:
                    final_places.append(place)
            
            optimized_itinerary[day_key] = final_places
            if day_changes:
                changes.extend(day_changes)
        
        return {
            'optimized_itinerary': optimized_itinerary,
            'changes': changes,
            'alerts': alerts,
            'optimization_timestamp': datetime.now().isoformat()
        }
    
    async def _sort_by_opening_hours(self, places: List[Dict], date: datetime) -> List[Dict]:
        """영업시간에 따라 장소 정렬"""
        places_with_hours = []
        
        for place in places:
            realtime_info = place.get('realtime_info', {})
            opening_hours = realtime_info.get('opening_hours', [])
            
            # 영업 시작 시간 파싱 (간단한 구현)
            opening_time = self._parse_opening_time(opening_hours, date.weekday())
            
            places_with_hours.append({
                **place,
                'opening_time': opening_time
            })
        
        # 영업 시작 시간 순으로 정렬
        sorted_places = sorted(
            places_with_hours,
            key=lambda x: x['opening_time'] if x['opening_time'] else '99:99'
        )
        
        return sorted_places
    
    def _parse_opening_time(self, opening_hours: List[str], weekday: int) -> Optional[str]:
        """영업 시작 시간 파싱"""
        if not opening_hours or weekday >= len(opening_hours):
            return None
            
        # 간단한 파싱 로직 (실제로는 더 복잡한 처리 필요)
        day_hours = opening_hours[weekday]
        if '휴무' in day_hours or 'Closed' in day_hours:
            return None
            
        # "09:00" 형식 추출 시도
        import re
        time_match = re.search(r'(\d{1,2}:\d{2})', day_hours)
        if time_match:
            return time_match.group(1)
            
        return None
    
    async def _adjust_visit_times(self, places: List[Dict], preferences: Dict = None) -> List[Dict]:
        """혼잡도를 고려한 방문 시간 조정"""
        adjusted_places = []
        current_time = datetime.strptime("09:00", "%H:%M")
        
        for place in places:
            realtime_info = place.get('realtime_info', {})
            
            # 선호 방문 시간대 확인
            preferred_time = None
            if preferences and preferences.get('avoid_crowds'):
                # 혼잡도가 낮은 시간대 찾기
                popular_times = realtime_info.get('popular_times', {})
                if popular_times:
                    # Popular Times API 데이터 분석 (실제 구현 필요)
                    preferred_time = self._find_least_crowded_time(popular_times)
            
            # 방문 시간 설정
            if preferred_time:
                visit_time = preferred_time
            else:
                visit_time = current_time.strftime("%H:%M")
            
            # 예상 체류 시간
            duration = place.get('duration', 60)  # 기본 60분
            
            adjusted_place = {
                **place,
                'suggested_visit_time': visit_time,
                'estimated_duration': duration
            }
            adjusted_places.append(adjusted_place)
            
            # 다음 장소 시작 시간 계산
            current_time = current_time + timedelta(minutes=duration + 30)  # 이동 시간 30분 추가
        
        return adjusted_places
    
    def _find_least_crowded_time(self, popular_times: Dict) -> Optional[str]:
        """가장 한적한 시간대 찾기"""
        # Popular Times 데이터 구조에 따라 구현
        # 간단한 예시 구현
        return "14:00"  # 실제로는 데이터 분석 필요
    
    async def _adjust_for_weather(
        self, 
        places: List[Dict], 
        date: datetime,
        lat: float = None,
        lon: float = None
    ) -> List[Dict]:
        """날씨에 따른 실내/실외 장소 조정"""
        adjusted_places = []
        
        # 날씨 정보 조회
        weather_info = None
        if lat and lon:
            # 좌표를 도시명으로 변환 (실제로는 역지오코딩 필요)
            city = "서울"
            try:
                weather_info = await self.weather_service.get_forecast(city, days=1)
            except Exception as e:
                logger.error(f"Error getting weather info: {str(e)}")
        
        if weather_info and weather_info.get('forecast'):
            forecast = weather_info['forecast'][0]
            
            # 악천후 확인
            is_bad_weather = (
                forecast.get('precipitation_chance', 0) > 70 or
                forecast.get('temperature_max', 20) > 35 or
                forecast.get('temperature_min', 10) < -5
            )
            
            if is_bad_weather:
                # 실내 장소 우선 배치
                indoor_places = [p for p in places if p.get('is_indoor', False)]
                outdoor_places = [p for p in places if not p.get('is_indoor', False)]
                
                # 날씨가 좋아지는 시간대에 실외 활동 배치
                adjusted_places = indoor_places + outdoor_places
            else:
                adjusted_places = places
        else:
            adjusted_places = places
        
        return adjusted_places
    
    async def _optimize_route(self, places: List[Dict]) -> List[Dict]:
        """경로 최적화"""
        if len(places) <= 2:
            return places
            
        # RouteOptimizer 사용
        try:
            # RouteOptimizer 초기화
            if not self.route_optimizer:
                self.route_optimizer = RouteOptimizer()
                
            # 장소 좌표 추출
            coordinates = []
            for place in places:
                if place.get('latitude') and place.get('longitude'):
                    coordinates.append({
                        'lat': place['latitude'],
                        'lon': place['longitude'],
                        'place': place
                    })
            
            if len(coordinates) < len(places):
                # 좌표가 없는 장소가 있으면 원래 순서 유지
                return places
            
            # 경로 최적화 (첫 장소는 고정)
            optimized_order = await self.route_optimizer.optimize_route_order(coordinates)
            
            # 최적화된 순서로 재배열
            optimized_places = [coord['place'] for coord in optimized_order]
            
            return optimized_places
            
        except Exception as e:
            logger.error(f"Error optimizing route: {str(e)}")
            return places
    
    def _get_change_reason(self, original: Dict, optimized: Dict) -> str:
        """변경 사유 생성"""
        reasons = []
        
        if original.get('name') != optimized.get('name'):
            reasons.append("장소 변경")
            
        if original.get('suggested_visit_time') != optimized.get('suggested_visit_time'):
            reasons.append("방문 시간 조정")
            
        if original.get('order') != optimized.get('order'):
            reasons.append("방문 순서 변경")
            
        return ", ".join(reasons) if reasons else "최적화"
    
    async def monitor_and_notify(
        self,
        plan_id: str,
        itinerary: Dict[str, List[Dict]],
        user_preferences: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        여행 계획 모니터링 및 알림
        
        Args:
            plan_id: 여행 계획 ID
            itinerary: 여행 일정
            user_preferences: 사용자 선호도
            
        Returns:
            모니터링 결과 및 알림
        """
        notifications = []
        
        # 실시간 충돌 검사
        conflicts = await self.realtime_service.check_itinerary_conflicts(itinerary)
        
        if conflicts['has_conflicts']:
            for conflict in conflicts['conflicts']:
                notifications.append({
                    'type': 'conflict',
                    'severity': 'high',
                    'title': f"{conflict['place']['name']} 방문 불가",
                    'message': conflict['message'],
                    'place': conflict['place'],
                    'timestamp': datetime.now().isoformat()
                })
        
        # 날씨 알림
        for day_key, places in itinerary.items():
            if places:
                first_place = places[0]
                if first_place.get('latitude') and first_place.get('longitude'):
                    weather_alerts = await self.realtime_service.get_weather_alerts(
                        first_place['latitude'],
                        first_place['longitude']
                    )
                    
                    for alert in weather_alerts:
                        notifications.append({
                            'type': 'weather',
                            'severity': alert['severity'],
                            'title': '날씨 알림',
                            'message': alert['message'],
                            'day': day_key,
                            'timestamp': datetime.now().isoformat()
                        })
        
        # 추천 사항
        if notifications:
            notifications.append({
                'type': 'recommendation',
                'severity': 'info',
                'title': '일정 재검토 권장',
                'message': '변경된 상황을 반영하여 일정을 다시 최적화하는 것을 권장합니다.',
                'timestamp': datetime.now().isoformat()
            })
        
        return {
            'plan_id': plan_id,
            'has_notifications': len(notifications) > 0,
            'notifications': notifications,
            'monitored_at': datetime.now().isoformat()
        }


# 서비스 인스턴스
travel_plan_optimizer = TravelPlanOptimizer()