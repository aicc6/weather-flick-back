"""
ODsay LAB API 서비스
대중교통 통합 정보 제공
"""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OdsayService:
    def __init__(self):
        self.api_key = settings.odsay_api_key
        self.base_url = settings.odsay_api_url
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

    async def search_pub_trans_path(self, start_x: float, start_y: float,
                                   end_x: float, end_y: float) -> dict[str, Any]:
        """대중교통 경로 검색"""
        try:
            session = await self._get_session()

            url = f"{self.base_url}/searchPubTransPathT"
            params = {
                "SX": start_x,
                "SY": start_y,
                "EX": end_x,
                "EY": end_y,
                "apiKey": self.api_key
            }

            response = await session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("result"):
                result = data["result"]
                paths = result.get("path", [])

                if paths:
                    # 가장 빠른 경로 선택 (paths가 리스트인지 확인)
                    if isinstance(paths, list) and len(paths) > 0:
                        best_path = min(paths, key=lambda x: x.get("info", {}).get("totalTime", float('inf')) if isinstance(x, dict) else float('inf'))
                    else:
                        return {
                            "success": False,
                            "message": "경로 데이터 형식이 올바르지 않습니다."
                        }

                    path_info = best_path.get("info", {})
                    sub_paths = best_path.get("subPath", [])

                    return {
                        "success": True,
                        "duration": path_info.get("totalTime", 0),
                        "distance": path_info.get("totalDistance", 0) / 1000,  # m to km
                        "cost": path_info.get("payment", 0),
                        "transfer_count": path_info.get("busTransitCount", 0) + path_info.get("subwayTransitCount", 0),
                        "walk_time": path_info.get("totalWalk", 0),
                        "route_data": {
                            "path_type": "public_transit",
                            "sub_paths": self._process_sub_paths(sub_paths),
                            "summary": {
                                "total_time": path_info.get("totalTime", 0),
                                "total_distance": path_info.get("totalDistance", 0),
                                "payment": path_info.get("payment", 0),
                                "bus_transit_count": path_info.get("busTransitCount", 0),
                                "subway_transit_count": path_info.get("subwayTransitCount", 0)
                            }
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": "경로를 찾을 수 없습니다."
                    }
            else:
                error_msg = data.get("error", {}).get("msg", "알 수 없는 오류")
                return {
                    "success": False,
                    "message": f"ODsay API 오류: {error_msg}"
                }

        except Exception as e:
            logger.error(f"ODsay API 호출 실패: {e}")
            return {
                "success": False,
                "message": f"대중교통 경로 검색 중 오류 발생: {str(e)}"
            }

    def _process_sub_paths(self, sub_paths: list[dict]) -> list[dict]:
        """세부 경로 정보 처리"""
        processed_paths = []

        for sub_path in sub_paths:
            path_type = sub_path.get("trafficType")

            if path_type == 1:  # 지하철
                lane_info = sub_path.get("lane", [{}])[0] if sub_path.get("lane") else {}
                processed_paths.append({
                    "type": "subway",
                    "lane": {
                        "name": lane_info.get("name", "지하철"),
                        "busNo": lane_info.get("busNo", ""),
                        "type": lane_info.get("type", ""),
                        "cityCode": lane_info.get("cityCode", ""),
                        "cityName": lane_info.get("cityName", "")
                    },
                    "start_station": sub_path.get("startName", ""),
                    "end_station": sub_path.get("endName", ""),
                    "station_count": sub_path.get("stationCount", 0),
                    "section_time": sub_path.get("sectionTime", 0),
                    "way": sub_path.get("way", ""),
                    "way_code": sub_path.get("wayCode", 0),
                    "door": sub_path.get("door", "")
                })
            elif path_type == 2:  # 버스
                lane_info = sub_path.get("lane", [{}])[0] if sub_path.get("lane") else {}
                processed_paths.append({
                    "type": "bus",
                    "lane": {
                        "name": lane_info.get("name", "버스"),
                        "busNo": lane_info.get("busNo", ""),
                        "type": lane_info.get("type", ""),
                        "cityCode": lane_info.get("cityCode", ""),
                        "cityName": lane_info.get("cityName", "")
                    },
                    "start_station": sub_path.get("startName", ""),
                    "end_station": sub_path.get("endName", ""),
                    "station_count": sub_path.get("stationCount", 0),
                    "section_time": sub_path.get("sectionTime", 0),
                    "way": sub_path.get("way", ""),
                    "way_code": sub_path.get("wayCode", 0)
                })
            elif path_type == 3:  # 도보
                processed_paths.append({
                    "type": "walk",
                    "distance": sub_path.get("distance", 0),
                    "section_time": sub_path.get("sectionTime", 0)
                })

        return processed_paths

    async def search_station(self, station_name: str, city_code: int = 1000) -> dict[str, Any]:
        """지하철역 검색"""
        try:
            session = await self._get_session()

            url = f"{self.base_url}/searchStation"
            params = {
                "stationName": station_name,
                "CID": city_code,
                "apiKey": self.api_key
            }

            response = await session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("result"):
                stations = data["result"].get("station", [])
                return {
                    "success": True,
                    "stations": stations
                }
            else:
                return {
                    "success": False,
                    "message": "역을 찾을 수 없습니다."
                }

        except Exception as e:
            logger.error(f"ODsay 역 검색 실패: {e}")
            return {
                "success": False,
                "message": f"역 검색 중 오류 발생: {str(e)}"
            }

    async def get_bus_lane_info(self, bus_id: str) -> dict[str, Any]:
        """버스 노선 정보 조회"""
        try:
            session = await self._get_session()

            url = f"{self.base_url}/busLaneDetail"
            params = {
                "busID": bus_id,
                "apiKey": self.api_key
            }

            response = await session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("result"):
                return {
                    "success": True,
                    "bus_info": data["result"]
                }
            else:
                return {
                    "success": False,
                    "message": "버스 정보를 찾을 수 없습니다."
                }

        except Exception as e:
            logger.error(f"ODsay 버스 정보 조회 실패: {e}")
            return {
                "success": False,
                "message": f"버스 정보 조회 중 오류 발생: {str(e)}"
            }


# 싱글톤 인스턴스
odsay_service = OdsayService()
