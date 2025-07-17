"""
통합 경로 서비스
ODsay, TMAP, 구글 API를 통합하여 최적의 경로 정보 제공
"""

import asyncio
import logging
import math
from typing import Any

import httpx

from app.config import settings
from app.services.odsay_service import odsay_service
from app.services.tmap_service import tmap_service

logger = logging.getLogger(__name__)


class RouteService:
    def __init__(self):
        self.google_api_key = settings.google_api_key
        self.session = None

    async def _get_session(self) -> httpx.AsyncClient:
        """HTTP 세션 생성"""
        if self.session is None or self.session.is_closed:
            self.session = httpx.AsyncClient(timeout=30.0)
        return self.session

    async def close(self):
        """세션 종료"""
        if self.session and not self.session.is_closed:
            await self.session.aclose()

    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """두 지점 간 직선 거리 계산 (하버사인 공식)"""
        R = 6371  # 지구 반지름 (km)

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)

        a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng / 2) * math.sin(delta_lng / 2))

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        return distance

    def _estimate_road_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """실제 도로망 거리 추정 (직선거리 기반 보정)"""
        straight_distance = self._calculate_distance(lat1, lng1, lat2, lng2)
        
        # 지역별 도로망 특성을 고려한 보정 계수
        # 1. 도시 지역: 격자형 도로망으로 인한 우회 (1.3배)
        # 2. 산간 지역: 지형으로 인한 우회 (1.5배)
        # 3. 섬 지역: 해안선 따라 우회 (1.4배)
        # 4. 고속도로 주행 가능 구간: 직선에 가까운 경로 (1.1배)
        
        # 제주도 지역 확인
        is_jeju = (33.1 <= lat1 <= 33.6 and 126.1 <= lng1 <= 126.9) or \
                  (33.1 <= lat2 <= 33.6 and 126.1 <= lng2 <= 126.9)
        
        # 울릉도 지역 확인
        is_ulleung = (37.4 <= lat1 <= 37.6 and 130.8 <= lng1 <= 131.0) or \
                     (37.4 <= lat2 <= 37.6 and 130.8 <= lng2 <= 131.0)
        
        # 서울 수도권 지역 확인 (격자형 도로망)
        is_seoul_metro = (37.4 <= lat1 <= 37.7 and 126.8 <= lng1 <= 127.2) or \
                        (37.4 <= lat2 <= 37.7 and 126.8 <= lng2 <= 127.2)
        
        # 부산 광역시 지역 확인
        is_busan = (35.0 <= lat1 <= 35.3 and 128.9 <= lng1 <= 129.3) or \
                   (35.0 <= lat2 <= 35.3 and 128.9 <= lng2 <= 129.3)
        
        # 거리별 보정 계수 적용
        if straight_distance > 200:  # 200km 이상 - 고속도로 주행 가능
            correction_factor = 1.15
        elif straight_distance > 100:  # 100-200km - 고속도로 + 일반도로 혼용
            correction_factor = 1.25
        elif straight_distance > 50:  # 50-100km - 일반도로 주행
            correction_factor = 1.35
        elif straight_distance > 20:  # 20-50km - 지역 도로
            correction_factor = 1.4
        elif straight_distance > 5:  # 5-20km - 시내도로
            correction_factor = 1.5
        else:  # 5km 이하 - 근거리 시내
            correction_factor = 1.6
        
        # 지역별 추가 보정
        if is_jeju or is_ulleung:
            correction_factor *= 1.2  # 섬 지역 해안선 우회
        elif is_seoul_metro:
            correction_factor *= 1.1  # 수도권 격자형 도로망
        elif is_busan:
            correction_factor *= 1.15  # 부산 산지 지형
        
        # 산간 지역 추정 (고도차가 클 것으로 예상되는 지역)
        # 강원도 산간 지역 (대략적 좌표)
        if (37.0 <= lat1 <= 38.6 and 127.5 <= lng1 <= 129.0) or \
           (37.0 <= lat2 <= 38.6 and 127.5 <= lng2 <= 129.0):
            correction_factor *= 1.2  # 산간 지역 우회
        
        # 경상북도 산간 지역
        if (35.4 <= lat1 <= 37.0 and 128.0 <= lng1 <= 129.5) or \
           (35.4 <= lat2 <= 37.0 and 128.0 <= lng2 <= 129.5):
            correction_factor *= 1.15  # 산간 지역 우회
        
        estimated_distance = straight_distance * correction_factor
        
        # 최소 거리 보장 (직선거리보다 작을 수 없음)
        return max(estimated_distance, straight_distance)

    def _is_island_region(self, lat: float, lng: float) -> bool:
        """섬 지역 여부 판단"""
        # 제주도 (33.1-33.6도, 126.1-126.9도)
        if 33.1 <= lat <= 33.6 and 126.1 <= lng <= 126.9:
            return True
        # 울릉도 (37.4-37.6도, 130.8-131.0도)
        if 37.4 <= lat <= 37.6 and 130.8 <= lng <= 131.0:
            return True
        # 기타 섬 지역 추가 가능
        return False

    def _get_regional_transport_info(self, dep_lat: float, dep_lng: float, 
                                   dest_lat: float, dest_lng: float) -> dict[str, Any]:
        """지역별 교통 특성 정보 반환"""
        dep_is_island = self._is_island_region(dep_lat, dep_lng)
        dest_is_island = self._is_island_region(dest_lat, dest_lng)
        distance = self._estimate_road_distance(dep_lat, dep_lng, dest_lat, dest_lng)
        
        # 섬 지역 간 이동 또는 본토-섬 간 이동
        if dep_is_island or dest_is_island:
            if dep_is_island and dest_is_island:
                # 섬 - 섬 간 이동 (같은 섬 내부 이동 제외)
                if distance > 50:  # 50km 이상이면 다른 섬으로 간주
                    return {
                        "primary_transport": "air",
                        "available_transports": ["air", "ferry"],
                        "walking_feasible": False,
                        "transit_feasible": False,
                        "driving_feasible": False,
                        "reason": "섬 간 이동은 항공기 또는 여객선 이용 필요"
                    }
            elif not dep_is_island and dest_is_island:
                # 본토 → 섬 이동
                return {
                    "primary_transport": "air",
                    "available_transports": ["air", "ferry"],
                    "walking_feasible": False,
                    "transit_feasible": False,
                    "driving_feasible": False,
                    "reason": "본토에서 섬으로 이동 시 항공기 또는 여객선 이용 필요"
                }
            elif dep_is_island and not dest_is_island:
                # 섬 → 본토 이동
                return {
                    "primary_transport": "air",
                    "available_transports": ["air", "ferry"],
                    "walking_feasible": False,
                    "transit_feasible": False,
                    "driving_feasible": False,
                    "reason": "섬에서 본토로 이동 시 항공기 또는 여객선 이용 필요"
                }
        
        # 일반 지역 간 이동
        if distance > 300:  # 300km 이상 장거리 이동
            return {
                "primary_transport": "air",
                "available_transports": ["air", "train", "bus"],
                "walking_feasible": False,
                "transit_feasible": True,
                "driving_feasible": True,
                "reason": "장거리 이동 시 항공기 또는 고속교통 이용 권장"
            }
        elif distance > 100:  # 100km 이상 중거리 이동
            return {
                "primary_transport": "train",
                "available_transports": ["train", "bus", "car"],
                "walking_feasible": False,
                "transit_feasible": True,
                "driving_feasible": True,
                "reason": "중거리 이동 시 KTX, 고속버스 이용 권장"
            }
        elif distance > 10:  # 10km 이상 단거리 이동
            return {
                "primary_transport": "transit",
                "available_transports": ["transit", "car", "taxi"],
                "walking_feasible": False,
                "transit_feasible": True,
                "driving_feasible": True,
                "reason": "단거리 이동 시 대중교통 이용 권장"
            }
        else:  # 10km 이하 근거리 이동
            return {
                "primary_transport": "walk",
                "available_transports": ["walk", "transit", "car", "taxi"],
                "walking_feasible": True,
                "transit_feasible": True,
                "driving_feasible": True,
                "reason": "근거리 이동 시 모든 교통수단 이용 가능"
            }

    async def calculate_walk_route(self, departure_lat: float, departure_lng: float,
                                 destination_lat: float, destination_lng: float) -> dict[str, Any]:
        """도보 경로 계산 (TMAP -> 구글 -> 기본 계산 순서)"""
        try:
            # 지역별 교통 특성 확인
            transport_info = self._get_regional_transport_info(departure_lat, departure_lng, 
                                                             destination_lat, destination_lng)
            
            if not transport_info["walking_feasible"]:
                return {
                    "success": False,
                    "message": f"도보 이동 불가능: {transport_info['reason']}",
                    "reason": transport_info["reason"],
                    "recommended_transports": transport_info["available_transports"]
                }
            
            # 1. TMAP API 시도
            tmap_result = await tmap_service.get_walk_route(
                departure_lng, departure_lat, destination_lng, destination_lat
            )

            if tmap_result.get("success"):
                tmap_result["source"] = "TMAP"
                tmap_result["transport_type"] = "walk"
                return tmap_result

            # 2. 구글 API 시도
            google_result = await self._get_google_directions(
                departure_lat, departure_lng, destination_lat, destination_lng, "walking"
            )

            if google_result.get("success"):
                google_result["source"] = "Google"
                google_result["transport_type"] = "walk"
                google_result["cost"] = 0
                return google_result

            # 3. 기본 계산
            distance = self._estimate_road_distance(departure_lat, departure_lng,
                                                   destination_lat, destination_lng)
            duration = int(distance * 12)  # 평균 도보 속도 5km/h

            return {
                "success": True,
                "duration": duration,
                "distance": distance,
                "cost": 0,
                "transport_type": "walk",
                "source": "calculation",
                "route_data": {
                    "method": "direct_calculation",
                    "departure": {"lat": departure_lat, "lng": departure_lng},
                    "destination": {"lat": destination_lat, "lng": destination_lng}
                },
                "message": "직선 거리 기반 도보 경로 계산"
            }

        except Exception as e:
            logger.error(f"도보 경로 계산 실패: {e}")
            return {
                "success": False,
                "message": f"도보 경로 계산 중 오류 발생: {str(e)}"
            }

    async def calculate_car_route(self, departure_lat: float, departure_lng: float,
                                destination_lat: float, destination_lng: float) -> dict[str, Any]:
        """자동차 경로 계산 (TMAP -> 구글 -> 기본 계산 순서)"""
        try:
            # 지역별 교통 특성 확인
            transport_info = self._get_regional_transport_info(departure_lat, departure_lng, 
                                                             destination_lat, destination_lng)
            
            if not transport_info["driving_feasible"]:
                return {
                    "success": False,
                    "message": f"자동차 이동 불가능: {transport_info['reason']}",
                    "reason": transport_info["reason"],
                    "recommended_transports": transport_info["available_transports"]
                }
            
            # 1. TMAP API 시도
            tmap_result = await tmap_service.get_car_route(
                departure_lng, departure_lat, destination_lng, destination_lat
            )

            if tmap_result.get("success"):
                tmap_result["source"] = "TMAP"
                tmap_result["transport_type"] = "car"
                return tmap_result

            # 2. 구글 API 시도
            google_result = await self._get_google_directions(
                departure_lat, departure_lng, destination_lat, destination_lng, "driving"
            )

            if google_result.get("success"):
                duration = google_result.get("duration", 0)
                distance = google_result.get("distance", 0)
                fuel_cost = distance * 150 if distance > 0 else 0  # 100km당 15,000원

                google_result["source"] = "Google"
                google_result["transport_type"] = "car"
                google_result["cost"] = fuel_cost
                return google_result

            # 3. 기본 계산 (더 상세한 mock 데이터)
            distance = self._estimate_road_distance(departure_lat, departure_lng,
                                                   destination_lat, destination_lng)
            duration = int(distance * 1.5)  # 자동차 평균 속도 고려
            fuel_cost = distance * 150

            # 거리에 따른 mock 경로 안내점 생성 (지역 특성 반영)
            guide_points = []
            
            # 좌표로 지역 판단 (제주도: 33.1-33.6도, 126.1-126.9도)
            is_jeju = (33.1 <= departure_lat <= 33.6 and 126.1 <= departure_lng <= 126.9) or \
                      (33.1 <= destination_lat <= 33.6 and 126.1 <= destination_lng <= 126.9)
            
            if distance > 5:  # 5km 이상인 경우
                if is_jeju:
                    guide_points = [
                        {"description": "출발지에서 주요 도로로 진입", "distance": 500, "time": 2},
                        {"description": "제주도 내 주요 도로 이용 (1100번도 또는 1132번도)", "distance": int(distance * 800), "time": int(duration * 0.7)},
                        {"description": "목적지 근처 도로로 진입", "distance": 300, "time": 1}
                    ]
                else:
                    guide_points = [
                        {"description": "출발지에서 주요 도로로 진입", "distance": 500, "time": 2},
                        {"description": "고속도로 또는 간선도로 이용", "distance": int(distance * 800), "time": int(duration * 0.7)},
                        {"description": "목적지 근처 도로로 진입", "distance": 300, "time": 1}
                    ]
            elif distance > 1:  # 1km 이상인 경우
                road_type = "지역 도로" if is_jeju else "일반 도로"
                guide_points = [
                    {"description": "출발지에서 도로로 진입", "distance": 200, "time": 1},
                    {"description": f"{road_type}를 통해 목적지까지 이동", "distance": int(distance * 800), "time": int(duration * 0.8)},
                    {"description": "목적지 도착", "distance": 100, "time": 1}
                ]

            return {
                "success": True,
                "duration": duration,
                "distance": distance,
                "cost": fuel_cost,
                "transport_type": "car",
                "source": "calculation",
                "route_data": {
                    "method": "estimated_calculation",
                    "departure": {"lat": departure_lat, "lng": departure_lng},
                    "destination": {"lat": destination_lat, "lng": destination_lng},
                    "guide_points": guide_points if guide_points else [],
                    "toll_fee": max(0, int(distance * 100 - 500)) if distance > 5 else 0,  # 5km 초과 시 통행료
                    "taxi_fee": int(distance * 1000 + 3000),  # 택시 기본요금 + 거리요금
                    "source": "calculation"
                },
                "message": "추정 계산 기반 자동차 경로"
            }

        except Exception as e:
            logger.error(f"자동차 경로 계산 실패: {e}")
            return {
                "success": False,
                "message": f"자동차 경로 계산 중 오류 발생: {str(e)}"
            }

    async def calculate_transit_route(self, departure_lat: float, departure_lng: float,
                                    destination_lat: float, destination_lng: float) -> dict[str, Any]:
        """대중교통 경로 계산 (ODsay -> 구글 -> 기본 계산 순서)"""
        try:
            # 지역별 교통 특성 확인
            transport_info = self._get_regional_transport_info(departure_lat, departure_lng, 
                                                             destination_lat, destination_lng)
            
            if not transport_info["transit_feasible"]:
                return {
                    "success": False,
                    "message": f"대중교통 이동 불가능: {transport_info['reason']}",
                    "reason": transport_info["reason"],
                    "recommended_transports": transport_info["available_transports"]
                }
            
            # 1. ODsay API 시도
            odsay_result = await odsay_service.search_pub_trans_path(
                departure_lng, departure_lat, destination_lng, destination_lat
            )

            if odsay_result.get("success"):
                odsay_result["source"] = "ODsay"
                odsay_result["transport_type"] = "transit"
                return odsay_result

            # 2. 구글 API 시도 (한국에서는 제한적)
            google_result = await self._get_google_directions(
                departure_lat, departure_lng, destination_lat, destination_lng, "transit"
            )

            if google_result.get("success"):
                duration = google_result.get("duration", 0)
                distance = google_result.get("distance", 0)
                base_fare = 1500
                distance_fare = max(0, (distance - 10) * 100) if distance > 10 else 0
                total_cost = base_fare + distance_fare

                google_result["source"] = "Google"
                google_result["transport_type"] = "transit"
                google_result["cost"] = total_cost
                google_result["message"] = "구글 API 기반 대중교통 경로 (제한적)"
                return google_result

            # 3. 기본 추정
            distance = self._estimate_road_distance(departure_lat, departure_lng,
                                                   destination_lat, destination_lng)
            duration = int(distance * 3)  # 대중교통은 환승 시간 포함
            cost = 1500 + max(0, (distance - 10) * 100)

            return {
                "success": True,
                "duration": duration,
                "distance": distance,
                "cost": cost,
                "transport_type": "transit",
                "source": "calculation",
                "route_data": {
                    "method": "estimated_calculation",
                    "departure": {"lat": departure_lat, "lng": departure_lng},
                    "destination": {"lat": destination_lat, "lng": destination_lng},
                    "note": "ODsay API 연동 실패로 추정 계산 사용"
                },
                "message": "추정 계산 기반 대중교통 경로"
            }

        except Exception as e:
            logger.error(f"대중교통 경로 계산 실패: {e}")
            return {
                "success": False,
                "message": f"대중교통 경로 계산 중 오류 발생: {str(e)}"
            }

    async def _get_google_directions(self, departure_lat: float, departure_lng: float,
                                   destination_lat: float, destination_lng: float,
                                   mode: str = "walking") -> dict[str, Any]:
        """구글 Directions API 호출 (대중교통 모드 우선 사용)"""
        try:
            session = await self._get_session()

            url = "https://maps.googleapis.com/maps/api/directions/json"
            
            # 대중교통이 가능한지 먼저 확인
            if mode in ["driving", "walking"]:
                # 대중교통 모드로 먼저 시도
                transit_params = {
                    "origin": f"{departure_lat},{departure_lng}",
                    "destination": f"{destination_lat},{destination_lng}",
                    "mode": "transit",
                    "key": self.google_api_key,
                    "language": "ko",
                    "region": "kr"
                }
                
                try:
                    transit_response = await session.get(url, params=transit_params)
                    transit_response.raise_for_status()
                    transit_data = transit_response.json()
                    
                    if transit_data.get("status") == "OK" and transit_data.get("routes"):
                        route = transit_data["routes"][0]
                        leg = route["legs"][0]
                        
                        # 대중교통 정보를 자동차/도보로 변환
                        duration = leg["duration"]["value"] // 60  # 초 -> 분
                        distance = leg["distance"]["value"] / 1000  # m -> km
                        
                        # 모드에 따라 시간 조정
                        if mode == "driving":
                            duration = max(int(duration * 0.4), 5)  # 자동차는 대중교통의 40% 시간
                        elif mode == "walking":
                            duration = max(int(duration * 1.2), 10)  # 도보는 대중교통의 120% 시간
                        
                        return {
                            "success": True,
                            "duration": duration,
                            "distance": distance,
                            "route_data": {
                                "overview_polyline": route.get("overview_polyline", {}),
                                "steps": leg.get("steps", []),
                                "start_address": leg.get("start_address", ""),
                                "end_address": leg.get("end_address", ""),
                                "warnings": route.get("warnings", []),
                                "summary": route.get("summary", ""),
                                "bounds": route.get("bounds", {}),
                                "copyrights": route.get("copyrights", ""),
                                "source_mode": "transit_converted",
                                "target_mode": mode
                            }
                        }
                except Exception as e:
                    logger.info(f"대중교통 모드 변환 실패, 기본 모드로 시도: {e}")
            
            # 기본 모드로 시도
            params = {
                "origin": f"{departure_lat},{departure_lng}",
                "destination": f"{destination_lat},{destination_lng}",
                "mode": mode,
                "key": self.google_api_key,
                "language": "ko",
                "region": "kr"
            }

            response = await session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("status") == "OK" and data.get("routes"):
                route = data["routes"][0]
                leg = route["legs"][0]

                duration = leg["duration"]["value"] // 60  # 초 -> 분
                distance = leg["distance"]["value"] / 1000  # m -> km

                return {
                    "success": True,
                    "duration": duration,
                    "distance": distance,
                    "route_data": {
                        "overview_polyline": route.get("overview_polyline", {}),
                        "steps": leg.get("steps", []),
                        "start_address": leg.get("start_address", ""),
                        "end_address": leg.get("end_address", ""),
                        "warnings": route.get("warnings", []),
                        "summary": route.get("summary", ""),
                        "bounds": route.get("bounds", {}),
                        "copyrights": route.get("copyrights", ""),
                        "source_mode": mode
                    }
                }
            else:
                logger.warning(f"구글 Directions API 응답 오류: {data.get('status')}")
                return {"success": False, "message": data.get("error_message", "알 수 없는 오류")}

        except Exception as e:
            logger.error(f"구글 Directions API 호출 실패: {e}")
            return {"success": False, "message": str(e)}

    async def calculate_route(self, departure_lat: float, departure_lng: float,
                            destination_lat: float, destination_lng: float,
                            transport_type: str = "walk") -> dict[str, Any]:
        """교통수단별 경로 계산"""
        try:
            if transport_type == "walk":
                return await self.calculate_walk_route(departure_lat, departure_lng,
                                                     destination_lat, destination_lng)
            elif transport_type == "car":
                return await self.calculate_car_route(departure_lat, departure_lng,
                                                    destination_lat, destination_lng)
            elif transport_type == "transit":
                return await self.calculate_transit_route(departure_lat, departure_lng,
                                                        destination_lat, destination_lng)
            else:
                return {
                    "success": False,
                    "message": f"지원하지 않는 교통수단: {transport_type}"
                }

        except Exception as e:
            logger.error(f"경로 계산 실패: {e}")
            return {
                "success": False,
                "message": f"경로 계산 중 오류 발생: {str(e)}"
            }

    async def get_multiple_routes(self, departure_lat: float, departure_lng: float,
                                destination_lat: float, destination_lng: float) -> dict[str, Any]:
        """여러 교통수단 경로 동시 계산"""
        try:
            # 지역별 교통 특성 확인
            transport_info = self._get_regional_transport_info(departure_lat, departure_lng, 
                                                             destination_lat, destination_lng)
            
            tasks = []
            
            # 이용 가능한 교통수단만 계산
            if transport_info["walking_feasible"]:
                tasks.append(('walk', self.calculate_walk_route(departure_lat, departure_lng, destination_lat, destination_lng)))
            
            if transport_info["driving_feasible"]:
                tasks.append(('car', self.calculate_car_route(departure_lat, departure_lng, destination_lat, destination_lng)))
            
            if transport_info["transit_feasible"]:
                tasks.append(('transit', self.calculate_transit_route(departure_lat, departure_lng, destination_lat, destination_lng)))
            
            # 병렬 처리
            if tasks:
                results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
                
                routes = {}
                for i, (transport_type, _) in enumerate(tasks):
                    if not isinstance(results[i], Exception):
                        routes[transport_type] = results[i]
                    else:
                        routes[transport_type] = {"success": False, "message": str(results[i])}
                
                # 이용 불가능한 교통수단에 대한 메시지 추가
                if not transport_info["walking_feasible"]:
                    routes["walk"] = {
                        "success": False, 
                        "message": f"도보 이동 불가능: {transport_info['reason']}",
                        "reason": transport_info["reason"]
                    }
                
                if not transport_info["driving_feasible"]:
                    routes["car"] = {
                        "success": False, 
                        "message": f"자동차 이동 불가능: {transport_info['reason']}",
                        "reason": transport_info["reason"]
                    }
                
                if not transport_info["transit_feasible"]:
                    routes["transit"] = {
                        "success": False, 
                        "message": f"대중교통 이동 불가능: {transport_info['reason']}",
                        "reason": transport_info["reason"]
                    }
                
                return {
                    "success": True,
                    "routes": routes,
                    "transport_info": transport_info
                }
            else:
                return {
                    "success": False,
                    "message": f"이용 가능한 교통수단이 없습니다: {transport_info['reason']}",
                    "transport_info": transport_info
                }

        except Exception as e:
            logger.error(f"다중 경로 계산 실패: {e}")
            return {
                "success": False,
                "message": f"다중 경로 계산 중 오류 발생: {str(e)}"
            }

    def _validate_route_realism(self, route_data: dict[str, Any], transport_type: str, 
                               distance: float, duration: int) -> dict[str, Any]:
        """경로의 현실성 검증"""
        warnings = []
        filtered = False
        
        # 교통수단별 현실성 검증
        if transport_type == "walk":
            # 도보 현실성 검증
            if distance > 50:  # 50km 이상 도보는 비현실적
                warnings.append(f"도보 이동 거리가 {distance:.1f}km로 너무 깁니다")
                filtered = True
            elif duration > 600:  # 10시간 이상 도보는 비현실적
                warnings.append(f"도보 이동 시간이 {duration}분으로 너무 깁니다")
                filtered = True
            elif distance > 20 and duration < distance * 10:  # 20km 초과 시 최소 도보 시간 확인
                warnings.append("도보 이동 시간이 비현실적으로 짧습니다")
                filtered = True
                
        elif transport_type == "car":
            # 자동차 현실성 검증
            if distance > 1000:  # 1000km 이상은 비현실적
                warnings.append(f"자동차 이동 거리가 {distance:.1f}km로 너무 깁니다")
                filtered = True
            elif duration > 720:  # 12시간 이상 운전은 비현실적
                warnings.append(f"자동차 이동 시간이 {duration}분으로 너무 깁니다")
                filtered = True
            elif distance > 100 and duration < distance * 0.5:  # 100km 초과 시 최소 시간 확인
                warnings.append("자동차 이동 시간이 비현실적으로 짧습니다")
                filtered = True
            elif distance < 0.5 and duration > 30:  # 0.5km 미만인데 30분 이상은 비현실적
                warnings.append("짧은 거리에 비해 이동 시간이 너무 깁니다")
                filtered = True
                
        elif transport_type == "transit":
            # 대중교통 현실성 검증
            if distance > 500:  # 500km 이상은 비현실적
                warnings.append(f"대중교통 이동 거리가 {distance:.1f}km로 너무 깁니다")
                filtered = True
            elif duration > 480:  # 8시간 이상은 비현실적
                warnings.append(f"대중교통 이동 시간이 {duration}분으로 너무 깁니다")
                filtered = True
            elif distance > 50 and duration < distance * 1.5:  # 50km 초과 시 최소 시간 확인
                warnings.append("대중교통 이동 시간이 비현실적으로 짧습니다")
                filtered = True
            elif distance < 0.3 and duration > 60:  # 0.3km 미만인데 60분 이상은 비현실적
                warnings.append("짧은 거리에 비해 이동 시간이 너무 깁니다")
                filtered = True
        
        # 비용 현실성 검증
        cost = route_data.get("cost", 0)
        if cost < 0:
            warnings.append("음수 비용이 계산되었습니다")
            filtered = True
        elif transport_type == "car" and cost > distance * 1000:  # 1km당 1000원 초과는 비현실적
            warnings.append(f"자동차 이동 비용이 {cost}원으로 너무 높습니다")
            filtered = True
        elif transport_type == "transit" and cost > 10000:  # 대중교통 10,000원 초과는 비현실적
            warnings.append(f"대중교통 비용이 {cost}원으로 너무 높습니다")
            filtered = True
        
        return {
            "is_realistic": not filtered,
            "warnings": warnings,
            "filtered": filtered
        }

    async def get_recommended_route(self, departure_lat: float, departure_lng: float,
                                  destination_lat: float, destination_lng: float,
                                  preferences: dict[str, Any] = None) -> dict[str, Any]:
        """상황에 맞는 최적 경로 추천 (현실성 검증 포함)"""
        try:
            # 모든 교통수단 경로 계산
            all_routes = await self.get_multiple_routes(
                departure_lat, departure_lng, destination_lat, destination_lng
            )

            if not all_routes.get("success"):
                return all_routes

            routes = all_routes["routes"]
            preferences = preferences or {}

            # 거리에 따른 기본 추천
            distance = self._estimate_road_distance(departure_lat, departure_lng,
                                                   destination_lat, destination_lng)

            # 각 경로의 현실성 검증
            validated_routes = {}
            for transport_type, route_data in routes.items():
                if route_data.get("success"):
                    validation = self._validate_route_realism(
                        route_data, transport_type, 
                        route_data.get("distance", 0),
                        route_data.get("duration", 0)
                    )
                    route_data["validation"] = validation
                    
                    # 비현실적인 경로는 제외하거나 경고 표시
                    if not validation["is_realistic"]:
                        route_data["success"] = False
                        route_data["message"] = f"비현실적인 경로: {', '.join(validation['warnings'])}"
                        logger.warning(f"{transport_type} 경로 필터링: {route_data['message']}")
                
                validated_routes[transport_type] = route_data

            # 현실적인 경로 중에서 추천
            recommended = None
            reason = ""

            if distance <= 1.0:  # 1km 이하
                if validated_routes["walk"].get("success"):
                    recommended = validated_routes["walk"]
                    reason = "1km 이하 거리로 도보 이동 추천"
            elif distance <= 10.0:  # 10km 이하
                if validated_routes["transit"].get("success"):
                    recommended = validated_routes["transit"]
                    reason = "중거리 이동으로 대중교통 추천"
                elif validated_routes["car"].get("success"):
                    recommended = validated_routes["car"]
                    reason = "대중교통 정보 없어 자동차 이동 추천"
            else:  # 10km 초과
                if validated_routes["car"].get("success"):
                    recommended = validated_routes["car"]
                    reason = "장거리 이동으로 자동차 이동 추천"
                elif validated_routes["transit"].get("success"):
                    recommended = validated_routes["transit"]
                    reason = "자동차 정보 없어 대중교통 추천"

            # 사용자 선호도 고려
            if preferences.get("prefer_cost") and validated_routes["transit"].get("success"):
                recommended = validated_routes["transit"]
                reason = "비용 절약을 위한 대중교통 추천"
            elif preferences.get("prefer_speed") and validated_routes["car"].get("success"):
                recommended = validated_routes["car"]
                reason = "빠른 이동을 위한 자동차 추천"
            elif preferences.get("prefer_eco") and validated_routes["walk"].get("success") and distance <= 2.0:
                recommended = validated_routes["walk"]
                reason = "친환경 이동을 위한 도보 추천"

            # 기본값 설정
            if not recommended:
                for transport_type in ["walk", "transit", "car"]:
                    if validated_routes[transport_type].get("success"):
                        recommended = validated_routes[transport_type]
                        reason = f"{transport_type} 경로만 사용 가능"
                        break

            # 모든 경로가 필터링된 경우 원본 중 최선 선택
            if not recommended:
                logger.warning("모든 경로가 현실성 검증에서 실패, 원본 경로 중 최선 선택")
                for transport_type in ["walk", "transit", "car"]:
                    original_route = routes.get(transport_type, {})
                    if original_route.get("success"):
                        recommended = original_route
                        recommended["validation"] = {"is_realistic": False, "warnings": ["검증 실패로 제한적 사용"], "filtered": True}
                        reason = f"{transport_type} 경로 (검증 실패했지만 유일한 옵션)"
                        break

            if not recommended:
                return {
                    "success": False,
                    "message": "이용 가능한 경로를 찾을 수 없습니다",
                    "all_routes": validated_routes,
                    "distance": distance,
                    "validation_applied": True
                }

            return {
                "success": True,
                "recommended": recommended,
                "reason": reason,
                "all_routes": validated_routes,
                "distance": distance,
                "validation_applied": True
            }

        except Exception as e:
            logger.error(f"추천 경로 계산 실패: {e}")
            return {
                "success": False,
                "message": f"추천 경로 계산 중 오류 발생: {str(e)}"
            }


# 싱글톤 인스턴스
route_service = RouteService()
