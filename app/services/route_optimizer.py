"""
경로 최적화 서비스
여행 일정의 장소 간 이동을 최적화하여 효율적인 동선 제공
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import numpy as np
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class Location(BaseModel):
    """위치 정보"""
    id: str
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    
    
class Place(BaseModel):
    """장소 정보"""
    id: str
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    place_type: Optional[str] = None  # attraction, restaurant, accommodation 등
    duration: int = 120  # 방문 소요시간 (분)
    visit_duration: Optional[int] = None  # duration의 별칭
    operating_hours: Optional[Dict[str, str]] = None  # {"open": "09:00", "close": "18:00"}
    opening_time: Optional[str] = None  # 영업 시작 시간
    closing_time: Optional[str] = None  # 영업 종료 시간
    priority: float = 1.0  # 우선순위 (사용자 선호도)
    
    def __init__(self, **data):
        super().__init__(**data)
        # visit_duration이 설정되지 않았으면 duration 값 사용
        if self.visit_duration is None:
            self.visit_duration = self.duration
    

class RouteConstraints(BaseModel):
    """경로 최적화 제약 조건"""
    start_time: str = "09:00"  # 시작 시간
    end_time: str = "18:00"    # 종료 시간
    lunch_time: Tuple[str, str] = ("12:00", "14:00")  # 점심 시간대
    travel_mode: str = "driving"  # 이동 수단
    max_walking_distance: int = 1000  # 최대 도보 거리 (미터)
    prefer_shortest_distance: bool = False  # 거리 우선 (vs 시간 우선)
    

class RouteSegment(BaseModel):
    """경로 구간 정보"""
    from_place: Place
    to_place: Place
    transport_mode: str  # walking, transit, driving
    distance: float  # km
    duration: int  # 분
    departure_time: str
    arrival_time: str
    cost: Optional[int] = None
    route_info: Optional[Dict[str, Any]] = None  # 상세 경로 정보


class OptimizedRoute(BaseModel):
    """최적화된 경로"""
    day: int
    places: List[Place]
    segments: List[RouteSegment]
    total_distance: float
    total_duration: int
    total_cost: Optional[int] = None
    efficiency_score: float  # 0-1 사이의 효율성 점수


class RouteOptimizer:
    """경로 최적화 서비스"""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.kakao_local_key = os.getenv("KAKAO_LOCAL_API_KEY")
        self.kakao_mobility_key = os.getenv("KAKAO_MOBILITY_API_KEY")
        self.distance_cache = {}  # 메모리 캐시
        
    def optimize_route(self, places: List[Place], constraints: RouteConstraints) -> List[Place]:
        """
        장소 목록을 최적 경로로 정렬
        
        Args:
            places: 방문할 장소 목록
            constraints: 경로 최적화 제약 조건
            
        Returns:
            최적화된 순서의 장소 목록
        """
        if len(places) <= 2:
            return places
            
        # 간단한 최근접 이웃 알고리즘 구현
        optimized = []
        remaining = places.copy()
        
        # 첫 장소 선택 (보통 숙소나 출발지)
        current = remaining.pop(0)
        optimized.append(current)
        
        # 나머지 장소들을 거리 기준으로 정렬
        while remaining:
            # 현재 위치에서 가장 가까운 장소 찾기
            min_distance = float('inf')
            nearest = None
            nearest_idx = -1
            
            for idx, place in enumerate(remaining):
                distance = self._calculate_distance(
                    current.latitude, current.longitude,
                    place.latitude, place.longitude
                )
                
                # 우선순위 가중치 적용
                weighted_distance = distance / place.priority
                
                if weighted_distance < min_distance:
                    min_distance = weighted_distance
                    nearest = place
                    nearest_idx = idx
            
            if nearest:
                optimized.append(nearest)
                remaining.pop(nearest_idx)
                current = nearest
                
        return optimized
        
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """두 지점 간의 거리 계산 (km)"""
        R = 6371  # 지구 반지름 (km)
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        return R * c
        
    async def optimize_daily_route(
        self,
        places: List[Dict[str, Any]],
        start_location: Optional[Location] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> OptimizedRoute:
        """
        하루 일정의 경로 최적화
        
        Args:
            places: 방문할 장소 목록
            start_location: 출발 위치 (숙소 등)
            preferences: 사용자 선호 설정
            
        Returns:
            최적화된 경로 정보
        """
        if not places:
            return None
            
        # Place 객체로 변환
        place_objects = [self._dict_to_place(p) for p in places]
        
        # 거리 매트릭스 계산
        distance_matrix = await self._calculate_distance_matrix(place_objects, start_location)
        
        # 최적 경로 계산 (개선된 최근접 이웃 알고리즘)
        optimized_order = self._optimize_route_order(
            place_objects,
            distance_matrix,
            start_location,
            preferences
        )
        
        # 경로 세그먼트 생성
        segments = await self._create_route_segments(
            optimized_order,
            start_location,
            preferences
        )
        
        # 통계 계산
        total_distance = sum(s.distance for s in segments)
        total_duration = sum(s.duration for s in segments)
        total_cost = sum(s.cost or 0 for s in segments) if any(s.cost for s in segments) else None
        
        # 효율성 점수 계산
        efficiency_score = self._calculate_efficiency_score(
            optimized_order,
            segments,
            preferences
        )
        
        return OptimizedRoute(
            day=1,
            places=optimized_order,
            segments=segments,
            total_distance=total_distance,
            total_duration=total_duration,
            total_cost=total_cost,
            efficiency_score=efficiency_score
        )
    
    async def optimize_multi_day_itinerary(
        self,
        all_places: List[Dict[str, Any]],
        days: int,
        accommodation: Optional[Location] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[OptimizedRoute]:
        """
        여러 날의 여행 일정 최적화
        
        Args:
            all_places: 전체 장소 목록
            days: 여행 일수
            accommodation: 숙소 위치
            preferences: 사용자 선호 설정
            
        Returns:
            일별 최적화된 경로 목록
        """
        # 장소를 지리적으로 클러스터링
        clustered_places = self._cluster_places_by_location(all_places, days)
        
        # 각 일차별로 최적화
        daily_routes = []
        for day, day_places in enumerate(clustered_places, 1):
            route = await self.optimize_daily_route(
                day_places,
                accommodation,
                preferences
            )
            if route:
                route.day = day
                daily_routes.append(route)
                
        return daily_routes
    
    def _dict_to_place(self, place_dict: Dict[str, Any]) -> Place:
        """딕셔너리를 Place 객체로 변환"""
        return Place(
            id=place_dict.get('id', ''),
            name=place_dict.get('name', ''),
            latitude=place_dict.get('latitude', 0),
            longitude=place_dict.get('longitude', 0),
            address=place_dict.get('address'),
            place_type=place_dict.get('type', 'attraction'),
            duration=place_dict.get('duration', 120),
            operating_hours=place_dict.get('operating_hours'),
            priority=place_dict.get('priority', 1.0)
        )
    
    async def _calculate_distance_matrix(
        self,
        places: List[Place],
        start_location: Optional[Location] = None
    ) -> np.ndarray:
        """
        장소 간 거리/시간 매트릭스 계산
        
        Returns:
            거리 매트릭스 (numpy array)
        """
        locations = []
        if start_location:
            locations.append(start_location)
        locations.extend(places)
        
        n = len(locations)
        matrix = np.zeros((n, n))
        
        # 병렬로 거리 계산
        tasks = []
        for i in range(n):
            for j in range(i+1, n):
                task = self._get_distance_time(locations[i], locations[j])
                tasks.append((i, j, task))
        
        results = await asyncio.gather(*[task for _, _, task in tasks])
        
        # 매트릭스 채우기
        for idx, (i, j, _) in enumerate(tasks):
            distance, time = results[idx]
            matrix[i][j] = time  # 시간을 기준으로 최적화
            matrix[j][i] = time
            
        return matrix
    
    async def _get_distance_time(
        self,
        origin: Location,
        destination: Location,
        mode: str = 'transit'
    ) -> Tuple[float, int]:
        """
        두 지점 간 거리와 시간 계산
        
        Returns:
            (거리(km), 시간(분)) 튜플
        """
        # 캐시 키 생성
        cache_key = f"{origin.latitude},{origin.longitude}:{destination.latitude},{destination.longitude}:{mode}"
        
        if cache_key in self.distance_cache:
            return self.distance_cache[cache_key]
        
        # 직선 거리 계산 (Haversine formula)
        straight_distance = self._haversine_distance(
            origin.latitude, origin.longitude,
            destination.latitude, destination.longitude
        )
        
        # 간단한 추정 (실제로는 API 호출)
        if mode == 'walking' and straight_distance <= 1.5:
            # 도보: 4km/h 속도 가정
            time = int(straight_distance * 15)  # 분
            result = (straight_distance, time)
        else:
            # 대중교통/자동차: 평균 속도로 추정
            # 실제로는 카카오 모빌리티 API 호출
            avg_speed = 25 if mode == 'transit' else 30  # km/h
            time = int(straight_distance * 60 / avg_speed * 1.3)  # 실제 도로 거리 보정
            distance = straight_distance * 1.3
            result = (distance, time)
        
        self.distance_cache[cache_key] = result
        return result
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine 공식을 사용한 두 지점 간 거리 계산 (km)"""
        R = 6371  # 지구 반지름 (km)
        
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c
    
    def _optimize_route_order(
        self,
        places: List[Place],
        distance_matrix: np.ndarray,
        start_location: Optional[Location],
        preferences: Optional[Dict[str, Any]]
    ) -> List[Place]:
        """
        개선된 최근접 이웃 알고리즘으로 경로 순서 최적화
        """
        n = len(places)
        if n <= 1:
            return places
            
        # 시작 인덱스 (숙소가 있으면 0, 없으면 1부터)
        start_idx = 0 if start_location else 1
        current_idx = start_idx
        
        unvisited = list(range(start_idx + 1, n + start_idx))
        route = []
        
        # 시간 제약 고려
        current_time = 9 * 60  # 오전 9시 시작 (분 단위)
        max_time = 21 * 60     # 오후 9시 종료
        
        while unvisited and current_time < max_time:
            # 현재 위치에서 방문 가능한 장소 중 최적 선택
            best_idx = None
            best_score = float('inf')
            
            for idx in unvisited:
                place_idx = idx - start_idx
                if place_idx >= len(places):
                    continue
                    
                place = places[place_idx]
                
                # 운영시간 체크
                if not self._is_place_open(place, current_time):
                    continue
                
                # 점수 계산 (거리 + 우선순위)
                distance_score = distance_matrix[current_idx][idx]
                priority_penalty = (1 - place.priority) * 30  # 우선순위가 낮으면 페널티
                
                total_score = distance_score + priority_penalty
                
                if total_score < best_score:
                    best_score = total_score
                    best_idx = idx
                    
            if best_idx is None:
                break
                
            # 선택된 장소 방문
            place_idx = best_idx - start_idx
            if place_idx < len(places):
                route.append(places[place_idx])
                unvisited.remove(best_idx)
                
                # 시간 업데이트
                travel_time = distance_matrix[current_idx][best_idx]
                current_time += travel_time + places[place_idx].duration
                current_idx = best_idx
        
        return route
    
    def _is_place_open(self, place: Place, time_minutes: int) -> bool:
        """장소가 해당 시간에 열려있는지 확인"""
        if not place.operating_hours:
            return True
            
        time_str = f"{time_minutes // 60:02d}:{time_minutes % 60:02d}"
        open_time = place.operating_hours.get('open', '00:00')
        close_time = place.operating_hours.get('close', '23:59')
        
        return open_time <= time_str <= close_time
    
    async def _create_route_segments(
        self,
        places: List[Place],
        start_location: Optional[Location],
        preferences: Optional[Dict[str, Any]]
    ) -> List[RouteSegment]:
        """경로 세그먼트 생성"""
        segments = []
        current_time = "09:00"
        
        # 시작 위치 설정
        current_location = start_location or places[0]
        
        for i, place in enumerate(places):
            # 이동 정보 계산
            distance, duration = await self._get_distance_time(
                current_location,
                place,
                mode=preferences.get('transport_mode', 'transit') if preferences else 'transit'
            )
            
            # 도착 시간 계산
            departure_time = current_time
            arrival_time = self._add_minutes_to_time(current_time, duration)
            
            # 세그먼트 생성
            segment = RouteSegment(
                from_place=current_location if isinstance(current_location, Place) else Place(
                    id="start",
                    name="출발지",
                    latitude=current_location.latitude,
                    longitude=current_location.longitude,
                    place_type="start"
                ),
                to_place=place,
                transport_mode=preferences.get('transport_mode', 'transit') if preferences else 'transit',
                distance=distance,
                duration=duration,
                departure_time=departure_time,
                arrival_time=arrival_time
            )
            segments.append(segment)
            
            # 다음 구간을 위한 업데이트
            current_location = place
            current_time = self._add_minutes_to_time(arrival_time, place.duration)
            
        return segments
    
    def _add_minutes_to_time(self, time_str: str, minutes: int) -> str:
        """시간 문자열에 분 추가"""
        hours, mins = map(int, time_str.split(':'))
        total_minutes = hours * 60 + mins + minutes
        
        new_hours = (total_minutes // 60) % 24
        new_mins = total_minutes % 60
        
        return f"{new_hours:02d}:{new_mins:02d}"
    
    def _calculate_efficiency_score(
        self,
        places: List[Place],
        segments: List[RouteSegment],
        preferences: Optional[Dict[str, Any]]
    ) -> float:
        """
        경로 효율성 점수 계산 (0-1)
        
        고려 요소:
        - 총 이동 거리/시간
        - 우선순위 높은 장소 방문 비율
        - 시간 활용도
        """
        if not segments:
            return 0.0
            
        # 이동 효율성 (이동시간 대비 방문시간)
        total_travel_time = sum(s.duration for s in segments)
        total_visit_time = sum(p.duration for p in places)
        travel_efficiency = total_visit_time / (total_travel_time + total_visit_time)
        
        # 우선순위 점수
        priority_score = sum(p.priority for p in places) / len(places) if places else 0
        
        # 종합 점수
        efficiency_score = travel_efficiency * 0.6 + priority_score * 0.4
        
        return min(1.0, max(0.0, efficiency_score))
    
    def _cluster_places_by_location(
        self,
        places: List[Dict[str, Any]],
        n_clusters: int
    ) -> List[List[Dict[str, Any]]]:
        """
        장소를 지리적 위치 기준으로 클러스터링
        
        간단한 구현: 위도/경도 기준 그리드 분할
        실제로는 K-means 등 사용 가능
        """
        if len(places) <= n_clusters:
            return [[p] for p in places]
            
        # 위도/경도 범위 계산
        lats = [p['latitude'] for p in places]
        lngs = [p['longitude'] for p in places]
        
        lat_min, lat_max = min(lats), max(lats)
        lng_min, lng_max = min(lngs), max(lngs)
        
        # 간단한 그리드 기반 분할
        clusters = [[] for _ in range(n_clusters)]
        
        for place in places:
            # 위도 기준으로 클러스터 할당
            lat_ratio = (place['latitude'] - lat_min) / (lat_max - lat_min + 0.0001)
            cluster_idx = min(int(lat_ratio * n_clusters), n_clusters - 1)
            clusters[cluster_idx].append(place)
            
        # 빈 클러스터 제거 및 재분배
        clusters = [c for c in clusters if c]
        
        # 균등 분배
        if len(clusters) < n_clusters:
            # 가장 큰 클러스터를 분할
            while len(clusters) < n_clusters and any(len(c) > 1 for c in clusters):
                largest = max(clusters, key=len)
                if len(largest) > 1:
                    mid = len(largest) // 2
                    clusters.append(largest[mid:])
                    largest[:] = largest[:mid]
                    
        return clusters[:n_clusters]


class KakaoRouteService:
    """카카오 API를 사용한 실제 경로 정보 서비스"""
    
    def __init__(self, local_key: str, mobility_key: str = None):
        self.local_key = local_key
        self.mobility_key = mobility_key
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def get_transit_route(
        self,
        origin: Location,
        destination: Location
    ) -> Dict[str, Any]:
        """대중교통 경로 조회"""
        # 카카오 로컬 API는 대중교통 경로를 직접 제공하지 않음
        # 대신 예상 시간과 거리를 계산
        distance = self._calculate_straight_distance(origin, destination)
        
        # 서울 기준 대중교통 평균 속도로 추정
        avg_speed = 20  # km/h (환승 포함)
        duration = int(distance * 60 / avg_speed)
        
        return {
            'distance': distance * 1.4,  # 실제 이동 거리 보정
            'duration': duration,
            'mode': 'transit',
            'segments': []  # 실제로는 상세 경로 정보
        }
        
    async def get_driving_route(
        self,
        origin: Location,
        destination: Location,
        waypoints: List[Location] = None
    ) -> Dict[str, Any]:
        """자동차 경로 조회 (카카오 모빌리티 API 필요)"""
        if not self.mobility_key:
            # 모빌리티 키가 없으면 추정값 반환
            distance = self._calculate_straight_distance(origin, destination)
            duration = int(distance * 60 / 25)  # 평균 25km/h
            
            return {
                'distance': distance * 1.3,
                'duration': duration,
                'mode': 'driving',
                'toll_fee': 0,
                'fuel_cost': int(distance * 150)  # 대략적인 유류비
            }
            
        # 실제 카카오 모빌리티 API 호출
        url = "https://apis-navi.kakaomobility.com/v1/directions"
        headers = {"Authorization": f"KakaoAK {self.mobility_key}"}
        
        params = {
            "origin": f"{origin.longitude},{origin.latitude}",
            "destination": f"{destination.longitude},{destination.latitude}",
            "priority": "RECOMMEND"
        }
        
        if waypoints:
            params["waypoints"] = "|".join([
                f"{wp.longitude},{wp.latitude}" for wp in waypoints
            ])
            
        async with self.session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                route = data['routes'][0]
                
                return {
                    'distance': route['summary']['distance'] / 1000,  # km
                    'duration': route['summary']['duration'] / 60,    # 분
                    'mode': 'driving',
                    'toll_fee': route['summary'].get('toll_fee', 0),
                    'fuel_cost': route['summary'].get('fuel_price', 0)
                }
            else:
                # 오류 시 추정값 반환
                return await self.get_driving_route(origin, destination)
                
    def _calculate_straight_distance(self, origin: Location, dest: Location) -> float:
        """직선 거리 계산 (km)"""
        R = 6371
        dlat = np.radians(dest.latitude - origin.latitude)
        dlon = np.radians(dest.longitude - origin.longitude)
        a = np.sin(dlat/2)**2 + np.cos(np.radians(origin.latitude)) * \
            np.cos(np.radians(dest.latitude)) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        return R * c