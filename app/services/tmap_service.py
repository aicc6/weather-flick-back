"""
TMAP API 서비스
자동차 경로 안내 및 실시간 교통정보 제공
"""

import logging
from typing import Dict, Any, Optional, List
import httpx
from app.config import settings
import json

logger = logging.getLogger(__name__)


class TmapService:
    def __init__(self):
        self.api_key = settings.tmap_api_key
        self.base_url = settings.tmap_api_url
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
    
    async def get_car_route(self, start_x: float, start_y: float, 
                           end_x: float, end_y: float, 
                           route_option: str = "trafast") -> Dict[str, Any]:
        """자동차 경로 안내"""
        try:
            session = await self._get_session()
            
            url = f"{self.base_url}/routes"
            headers = {
                "appKey": self.api_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "startX": str(start_x),
                "startY": str(start_y),
                "endX": str(end_x),
                "endY": str(end_y),
                "reqCoordType": "WGS84GEO",
                "resCoordType": "WGS84GEO",
                "searchOption": route_option,  # trafast(빠른길), tracomfort(편한길), traoptimal(최적)
                "carType": 1  # 일반차량
            }
            
            response = await session.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("features"):
                # 경로 정보 추출
                route_info = self._extract_route_info(result["features"])
                
                return {
                    "success": True,
                    "duration": route_info["total_time"] // 60,  # 초 -> 분
                    "distance": route_info["total_distance"] / 1000,  # m -> km
                    "cost": self._calculate_fuel_cost(route_info["total_distance"]),
                    "toll_fee": route_info.get("toll_fee", 0),
                    "taxi_fee": route_info.get("taxi_fee", 0),
                    "route_data": {
                        "path_type": "car",
                        "total_time": route_info["total_time"],
                        "total_distance": route_info["total_distance"],
                        "toll_fee": route_info.get("toll_fee", 0),
                        "taxi_fee": route_info.get("taxi_fee", 0),
                        "guide_points": route_info.get("guide_points", []),
                        "detailed_guides": route_info.get("detailed_guides", []),
                        "geometry": route_info.get("geometry", []),
                        "source": "TMAP",
                        "route_summary": {
                            "total_steps": len(route_info.get("guide_points", [])),
                            "major_steps": len(route_info.get("detailed_guides", [])),
                            "estimated_fuel_cost": self._calculate_fuel_cost(route_info["total_distance"]),
                            "total_cost_estimate": self._calculate_fuel_cost(route_info["total_distance"]) + route_info.get("toll_fee", 0)
                        }
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "경로를 찾을 수 없습니다."
                }
                
        except Exception as e:
            logger.error(f"TMAP API 호출 실패: {e}")
            return {
                "success": False,
                "message": f"자동차 경로 검색 중 오류 발생: {str(e)}"
            }
    
    async def get_walk_route(self, start_x: float, start_y: float, 
                            end_x: float, end_y: float) -> Dict[str, Any]:
        """도보 경로 안내"""
        try:
            session = await self._get_session()
            
            url = f"{self.base_url}/routes/pedestrian"
            headers = {
                "appKey": self.api_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "startX": str(start_x),
                "startY": str(start_y),
                "endX": str(end_x),
                "endY": str(end_y),
                "reqCoordType": "WGS84GEO",
                "resCoordType": "WGS84GEO",
                "startName": "출발지",
                "endName": "도착지"
            }
            
            response = await session.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("features"):
                # 도보 경로 정보 추출
                route_info = self._extract_walk_route_info(result["features"])
                
                return {
                    "success": True,
                    "duration": route_info["total_time"] // 60,  # 초 -> 분
                    "distance": route_info["total_distance"] / 1000,  # m -> km
                    "cost": 0,  # 도보는 무료
                    "route_data": {
                        "path_type": "walk",
                        "total_time": route_info["total_time"],
                        "total_distance": route_info["total_distance"],
                        "guide_points": route_info.get("guide_points", []),
                        "geometry": route_info.get("geometry", [])
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "도보 경로를 찾을 수 없습니다."
                }
                
        except Exception as e:
            logger.error(f"TMAP 도보 경로 API 호출 실패: {e}")
            return {
                "success": False,
                "message": f"도보 경로 검색 중 오류 발생: {str(e)}"
            }
    
    def _extract_route_info(self, features: List[Dict]) -> Dict[str, Any]:
        """자동차 경로 정보 추출 (상세 안내점 포함)"""
        total_time = 0
        total_distance = 0
        toll_fee = 0
        taxi_fee = 0
        guide_points = []
        detailed_guides = []
        geometry = []
        
        for feature in features:
            props = feature.get("properties", {})
            geometry_data = feature.get("geometry", {})
            
            # 총 시간 및 거리
            if props.get("totalTime"):
                total_time = props["totalTime"]
            if props.get("totalDistance"):
                total_distance = props["totalDistance"]
            if props.get("totalFare"):
                toll_fee = props["totalFare"]
            if props.get("taxiFare"):
                taxi_fee = props["taxiFare"]
            
            # 상세 안내점 정보 추출
            if props.get("description"):
                guide_point = {
                    "step": len(guide_points) + 1,
                    "description": props["description"],
                    "distance": props.get("distance", 0),
                    "time": props.get("time", 0),
                    "point_type": props.get("pointType", ""),
                    "turn_type": props.get("turnType", 0),
                    "road_name": props.get("roadName", ""),
                    "facility_type": props.get("facilityType", ""),
                    "facility_name": props.get("facilityName", ""),
                    "direction": props.get("direction", ""),
                    "intersection_name": props.get("intersectionName", ""),
                    "guide_arrow": props.get("guideArrow", ""),
                    "speed_limit": props.get("speedLimit", 0)
                }
                
                # 턴 타입에 따른 상세 안내문 생성
                if props.get("turnType"):
                    turn_type = props["turnType"]
                    if turn_type == 11:
                        guide_point["turn_instruction"] = "직진"
                    elif turn_type == 12:
                        guide_point["turn_instruction"] = "좌회전"
                    elif turn_type == 13:
                        guide_point["turn_instruction"] = "우회전"
                    elif turn_type == 14:
                        guide_point["turn_instruction"] = "U턴"
                    elif turn_type == 15:
                        guide_point["turn_instruction"] = "좌측 방향"
                    elif turn_type == 16:
                        guide_point["turn_instruction"] = "우측 방향"
                    elif turn_type == 17:
                        guide_point["turn_instruction"] = "고속도로 진입"
                    elif turn_type == 18:
                        guide_point["turn_instruction"] = "고속도로 진출"
                    elif turn_type == 19:
                        guide_point["turn_instruction"] = "톨게이트"
                    elif turn_type == 20:
                        guide_point["turn_instruction"] = "분기점"
                    else:
                        guide_point["turn_instruction"] = "계속 진행"
                
                guide_points.append(guide_point)
                
                # 주요 안내점만 별도로 저장 (거리가 500m 이상인 경우)
                if props.get("distance", 0) >= 500:
                    detailed_guides.append({
                        "step": len(detailed_guides) + 1,
                        "description": props["description"],
                        "distance": f"{props.get('distance', 0):,.0f}m",
                        "time": f"{props.get('time', 0)//60}분" if props.get('time', 0) >= 60 else f"{props.get('time', 0)}초",
                        "instruction": guide_point.get("turn_instruction", "계속 진행")
                    })
            
            # 경로 geometry
            if geometry_data.get("coordinates"):
                geometry.extend(geometry_data["coordinates"])
        
        return {
            "total_time": total_time,
            "total_distance": total_distance,
            "toll_fee": toll_fee,
            "taxi_fee": taxi_fee,
            "guide_points": guide_points,
            "detailed_guides": detailed_guides,
            "geometry": geometry
        }
    
    def _extract_walk_route_info(self, features: List[Dict]) -> Dict[str, Any]:
        """도보 경로 정보 추출"""
        total_time = 0
        total_distance = 0
        guide_points = []
        geometry = []
        
        for feature in features:
            props = feature.get("properties", {})
            geometry_data = feature.get("geometry", {})
            
            # 총 시간 및 거리
            if props.get("totalTime"):
                total_time = props["totalTime"]
            if props.get("totalDistance"):
                total_distance = props["totalDistance"]
            
            # 안내점 정보
            if props.get("description"):
                guide_points.append({
                    "description": props["description"],
                    "distance": props.get("distance", 0),
                    "time": props.get("time", 0)
                })
            
            # 경로 geometry
            if geometry_data.get("coordinates"):
                geometry.extend(geometry_data["coordinates"])
        
        return {
            "total_time": total_time,
            "total_distance": total_distance,
            "guide_points": guide_points,
            "geometry": geometry
        }
    
    def _calculate_fuel_cost(self, distance_m: float) -> float:
        """연료비 계산 (거리 기반)"""
        distance_km = distance_m / 1000
        fuel_efficiency = 12  # km/L (평균 연비)
        fuel_price = 1600  # 원/L (평균 휘발유 가격)
        
        fuel_cost = (distance_km / fuel_efficiency) * fuel_price
        return round(fuel_cost, 0)
    
    async def get_poi_around(self, center_x: float, center_y: float, 
                            radius: int = 1000, 
                            categories: str = "parking") -> Dict[str, Any]:
        """주변 POI 검색 (주차장, 주유소 등)"""
        try:
            session = await self._get_session()
            
            url = f"{self.base_url}/pois"
            headers = {
                "appKey": self.api_key
            }
            
            params = {
                "centerLon": center_x,
                "centerLat": center_y,
                "radius": radius,
                "categories": categories,
                "resCoordType": "WGS84GEO",
                "searchtypCd": "R",
                "reqCoordType": "WGS84GEO",
                "count": 20
            }
            
            response = await session.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("searchPoiInfo"):
                pois = result["searchPoiInfo"].get("pois", {}).get("poi", [])
                return {
                    "success": True,
                    "pois": pois,
                    "total_count": result["searchPoiInfo"].get("totalCount", 0)
                }
            else:
                return {
                    "success": False,
                    "message": "주변 시설을 찾을 수 없습니다."
                }
                
        except Exception as e:
            logger.error(f"TMAP POI 검색 실패: {e}")
            return {
                "success": False,
                "message": f"주변 시설 검색 중 오류 발생: {str(e)}"
            }


# 싱글톤 인스턴스
tmap_service = TmapService()