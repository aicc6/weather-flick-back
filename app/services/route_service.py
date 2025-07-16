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

    async def calculate_walk_route(self, departure_lat: float, departure_lng: float,
                                 destination_lat: float, destination_lng: float) -> dict[str, Any]:
        """도보 경로 계산 (TMAP -> 구글 -> 기본 계산 순서)"""
        try:
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
            distance = self._calculate_distance(departure_lat, departure_lng,
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
            distance = self._calculate_distance(departure_lat, departure_lng,
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
            distance = self._calculate_distance(departure_lat, departure_lng,
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
            tasks = [
                self.calculate_walk_route(departure_lat, departure_lng, destination_lat, destination_lng),
                self.calculate_car_route(departure_lat, departure_lng, destination_lat, destination_lng),
                self.calculate_transit_route(departure_lat, departure_lng, destination_lat, destination_lng)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            return {
                "success": True,
                "routes": {
                    "walk": results[0] if not isinstance(results[0], Exception) else {"success": False, "message": str(results[0])},
                    "car": results[1] if not isinstance(results[1], Exception) else {"success": False, "message": str(results[1])},
                    "transit": results[2] if not isinstance(results[2], Exception) else {"success": False, "message": str(results[2])}
                }
            }

        except Exception as e:
            logger.error(f"다중 경로 계산 실패: {e}")
            return {
                "success": False,
                "message": f"다중 경로 계산 중 오류 발생: {str(e)}"
            }

    async def get_recommended_route(self, departure_lat: float, departure_lng: float,
                                  destination_lat: float, destination_lng: float,
                                  preferences: dict[str, Any] = None) -> dict[str, Any]:
        """상황에 맞는 최적 경로 추천"""
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
            distance = self._calculate_distance(departure_lat, departure_lng,
                                              destination_lat, destination_lng)

            recommended = None
            reason = ""

            if distance <= 1.0:  # 1km 이하
                if routes["walk"].get("success"):
                    recommended = routes["walk"]
                    reason = "1km 이하 거리로 도보 이동 추천"
            elif distance <= 10.0:  # 10km 이하
                if routes["transit"].get("success"):
                    recommended = routes["transit"]
                    reason = "중거리 이동으로 대중교통 추천"
                elif routes["car"].get("success"):
                    recommended = routes["car"]
                    reason = "대중교통 정보 없어 자동차 이동 추천"
            else:  # 10km 초과
                if routes["car"].get("success"):
                    recommended = routes["car"]
                    reason = "장거리 이동으로 자동차 이동 추천"
                elif routes["transit"].get("success"):
                    recommended = routes["transit"]
                    reason = "자동차 정보 없어 대중교통 추천"

            # 사용자 선호도 고려
            if preferences.get("prefer_cost") and routes["transit"].get("success"):
                recommended = routes["transit"]
                reason = "비용 절약을 위한 대중교통 추천"
            elif preferences.get("prefer_speed") and routes["car"].get("success"):
                recommended = routes["car"]
                reason = "빠른 이동을 위한 자동차 추천"
            elif preferences.get("prefer_eco") and routes["walk"].get("success") and distance <= 2.0:
                recommended = routes["walk"]
                reason = "친환경 이동을 위한 도보 추천"

            # 기본값 설정
            if not recommended:
                for transport_type in ["walk", "transit", "car"]:
                    if routes[transport_type].get("success"):
                        recommended = routes[transport_type]
                        reason = f"{transport_type} 경로만 사용 가능"
                        break

            return {
                "success": True,
                "recommended": recommended,
                "reason": reason,
                "all_routes": routes,
                "distance": distance
            }

        except Exception as e:
            logger.error(f"추천 경로 계산 실패: {e}")
            return {
                "success": False,
                "message": f"추천 경로 계산 중 오류 발생: {str(e)}"
            }


# 싱글톤 인스턴스
route_service = RouteService()
