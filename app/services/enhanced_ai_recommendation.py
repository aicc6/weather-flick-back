"""
경로 최적화가 통합된 향상된 AI 추천 서비스
기존 AI 추천에 경로 최적화를 적용하여 더 효율적인 여행 일정 생성
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import (
    CustomTravelRecommendationRequest,
    DayItinerary,
    PlaceRecommendation,
)
from app.services.ai_recommendation import AIRecommendationService
from app.services.route_optimizer import Location, RouteOptimizer

logger = logging.getLogger(__name__)


class EnhancedAIRecommendationService(AIRecommendationService):
    """경로 최적화가 통합된 AI 추천 서비스"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.route_optimizer = RouteOptimizer(db)
        
    async def generate_travel_itinerary(
        self, 
        request: CustomTravelRecommendationRequest, 
        places: List[Dict[str, Any]]
    ) -> List[DayItinerary]:
        """AI 추천 후 경로 최적화를 적용한 여행 일정 생성"""
        
        logger.info(f"향상된 AI 추천 서비스 시작 - {request.days}일 일정")
        
        # 1단계: 기존 AI 추천으로 장소 선택
        initial_itinerary = await super().generate_travel_itinerary(request, places)
        
        if not initial_itinerary:
            return []
        
        # 2단계: 각 날짜별로 경로 최적화 적용
        optimized_days = []
        
        # 숙소 위치 추출 (있는 경우)
        accommodation_location = self._get_accommodation_location(request, places)
        
        for day_idx, day_itinerary in enumerate(initial_itinerary):
            logger.info(f"{day_idx + 1}일차 경로 최적화 시작 - {len(day_itinerary.places)}개 장소")
            
            # DayItinerary에서 장소 정보 추출
            day_places = []
            for place in day_itinerary.places:
                place_data = {
                    'id': place.id,
                    'name': place.name,
                    'latitude': place.latitude,
                    'longitude': place.longitude,
                    'address': place.address,
                    'type': self._get_place_type(place.tags),
                    'duration': self._estimate_duration(place),
                    'priority': (place.rating / 5.0) if place.rating else 0.8
                }
                day_places.append(place_data)
            
            if not day_places:
                optimized_days.append(day_itinerary)
                continue
            
            try:
                # 경로 최적화 실행
                optimized_route = await self.route_optimizer.optimize_daily_route(
                    day_places,
                    start_location=accommodation_location,
                    preferences={
                        'transport_mode': self._get_transport_mode(request.transportation),
                        'schedule': request.schedule
                    }
                )
                
                if optimized_route and optimized_route.places:
                    # 최적화된 순서로 장소 재배열
                    optimized_places = []
                    
                    for idx, opt_place in enumerate(optimized_route.places):
                        # 원본 장소 정보 찾기
                        original_place = next(
                            (p for p in day_itinerary.places if p.id == opt_place.id),
                            None
                        )
                        
                        if original_place:
                            # 이동 시간 정보 추가
                            if idx < len(optimized_route.segments):
                                segment = optimized_route.segments[idx]
                                # 시간 정보 업데이트
                                original_place.time = f"{segment.departure_time}-{segment.arrival_time}"
                                
                                # 교통 정보를 설명에 추가
                                transport_info = self._format_transport_info(segment)
                                if original_place.description:
                                    original_place.description += f" | {transport_info}"
                                else:
                                    original_place.description = transport_info
                                    
                            optimized_places.append(original_place)
                    
                    # 최적화된 장소로 업데이트
                    day_itinerary.places = optimized_places
                    
                    # 경로 효율성 정보 추가
                    route_summary = {
                        'total_distance': round(optimized_route.total_distance, 1),
                        'total_duration': optimized_route.total_duration,
                        'efficiency_score': round(optimized_route.efficiency_score, 2),
                        'optimized': True
                    }
                    
                    # weather 필드와 함께 route_info 추가
                    if hasattr(day_itinerary, 'weather') and day_itinerary.weather:
                        day_itinerary.weather['route_info'] = route_summary
                    else:
                        day_itinerary.weather = {'route_info': route_summary}
                    
                    logger.info(
                        f"{day_idx + 1}일차 최적화 완료 - "
                        f"거리: {route_summary['total_distance']}km, "
                        f"효율성: {route_summary['efficiency_score']}"
                    )
                else:
                    logger.warning(f"{day_idx + 1}일차 경로 최적화 실패 - 원본 순서 유지")
                    
            except Exception as e:
                logger.error(f"{day_idx + 1}일차 경로 최적화 중 오류: {str(e)}")
                # 오류 발생 시 원본 순서 유지
                
            optimized_days.append(day_itinerary)
        
        return optimized_days
    
    def _get_accommodation_location(
        self, 
        request: CustomTravelRecommendationRequest,
        places: List[Dict[str, Any]]
    ) -> Optional[Location]:
        """숙소 위치 추출"""
        # 시작 위치가 지정된 경우
        if hasattr(request, 'start_location') and request.start_location:
            return Location(
                id="start",
                name=request.start_location,
                latitude=37.5665,  # 기본값 (서울)
                longitude=126.9780
            )
        
        # 숙박시설 찾기
        accommodations = [p for p in places if p.get('type') == 'accommodation']
        if accommodations:
            acc = accommodations[0]
            return Location(
                id=acc['id'],
                name=acc['name'],
                latitude=acc['latitude'],
                longitude=acc['longitude']
            )
            
        return None
    
    def _get_place_type(self, tags: List[str]) -> str:
        """태그를 기반으로 장소 타입 결정"""
        if not tags:
            return 'attraction'
            
        tag_str = ' '.join(tags).lower()
        
        if any(word in tag_str for word in ['음식', '맛집', '레스토랑', '카페']):
            return 'restaurant'
        elif any(word in tag_str for word in ['쇼핑', '시장', '백화점', '면세점']):
            return 'shopping'
        elif any(word in tag_str for word in ['숙박', '호텔', '게스트하우스', '펜션']):
            return 'accommodation'
        elif any(word in tag_str for word in ['문화', '박물관', '미술관', '공연']):
            return 'cultural'
        else:
            return 'attraction'
    
    def _estimate_duration(self, place: PlaceRecommendation) -> int:
        """장소별 예상 체류 시간 추정 (분)"""
        # 태그 기반 추정
        tags_str = ' '.join(place.tags).lower() if place.tags else ''
        
        if '식사' in tags_str or '레스토랑' in tags_str:
            return 90
        elif '카페' in tags_str:
            return 60
        elif '쇼핑' in tags_str or '시장' in tags_str:
            return 120
        elif '박물관' in tags_str or '미술관' in tags_str:
            return 150
        elif '공원' in tags_str or '산책' in tags_str:
            return 90
        else:
            return 120  # 기본값
    
    def _get_transport_mode(self, transportation: Optional[str]) -> str:
        """교통수단 매핑"""
        if not transportation:
            return 'transit'
            
        transport_map = {
            '대중교통': 'transit',
            '자가용': 'driving',
            '도보': 'walking',
            '택시': 'driving',
            '렌터카': 'driving'
        }
        
        return transport_map.get(transportation, 'transit')
    
    def _format_transport_info(self, segment) -> str:
        """교통 정보 포맷팅"""
        transport_names = {
            'walking': '도보',
            'transit': '대중교통',
            'driving': '차량'
        }
        
        mode_name = transport_names.get(segment.transport_mode, segment.transport_mode)
        
        if segment.duration < 60:
            time_str = f"{segment.duration}분"
        else:
            hours = segment.duration // 60
            minutes = segment.duration % 60
            time_str = f"{hours}시간 {minutes}분" if minutes > 0 else f"{hours}시간"
        
        return f"{segment.from_place.name}에서 {mode_name}로 {time_str} 이동"


def get_enhanced_ai_recommendation_service(db: Session) -> EnhancedAIRecommendationService:
    """향상된 AI 추천 서비스 인스턴스 생성"""
    return EnhancedAIRecommendationService(db)