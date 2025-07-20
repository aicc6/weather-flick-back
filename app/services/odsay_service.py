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
        
        # ODsay API 지역별 CID (City ID) 매핑
        self.city_id_mapping = {
            "서울": 1000,
            "부산": 2000,
            "대구": 2200,
            "인천": 1100,
            "광주": 2300,
            "대전": 2100,
            "울산": 2400,
            "경기": 1200,
            "강원": 3100,
            "충북": 3300,
            "충남": 3400,
            "전북": 3700,
            "전남": 3800,
            "경북": 3500,
            "경남": 3600,
            "제주": 3900,
            "세종": 3200
        }

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
        """대중교통 경로 검색 (지역별 CID 자동 적용)"""
        try:
            # 출발지와 목적지 지역 확인
            departure_region = self._get_region_from_coordinates(start_y, start_x)
            destination_region = self._get_region_from_coordinates(end_y, end_x)
            
            # 주요 지역의 CID 결정 (출발지 우선, 없으면 목적지, 둘 다 없으면 서울)
            target_city = departure_region if departure_region != "기타" else destination_region
            if target_city == "기타":
                target_city = "서울"  # 기본값
                
            city_id = self.city_id_mapping.get(target_city, 1000)  # 기본값: 서울
            
            logger.info(f"🚌 ODsay API 요청 시작 - 지역: {target_city} (CID: {city_id})")
            logger.info(f"📍 좌표: ({start_y}, {start_x}) -> ({end_y}, {end_x})")
            
            session = await self._get_session()

            url = f"{self.base_url}/searchPubTransPathT"
            params = {
                "SX": start_x,
                "SY": start_y,
                "EX": end_x,
                "EY": end_y,
                "CID": city_id,  # 지역별 도시 코드 추가
                "apiKey": self.api_key
            }
            
            logger.info(f"🔗 요청 URL: {url}")
            logger.info(f"📝 요청 파라미터: {params}")

            response = await session.get(url, params=params)
            logger.info(f"📊 ODsay API 응답 상태: {response.status_code}")
            response.raise_for_status()

            data = response.json()

            # ODsay API가 리스트를 반환하는 경우 처리
            if isinstance(data, list):
                if data and len(data) > 0:
                    data = data[0]
                else:
                    return {
                        "success": False,
                        "message": "빈 응답을 받았습니다."
                    }

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

                    processed_sub_paths = self._process_sub_paths(sub_paths)
                    
                    # 응답에서 반환된 교통수단 정보 로깅
                    transport_summary = []
                    for path in processed_sub_paths:
                        if path['type'] in ['bus', 'subway']:
                            lane_info = path.get('lane', {})
                            transport_summary.append({
                                'type': path['type'],
                                'line': lane_info.get('busNo', lane_info.get('name', '')),
                                'city': lane_info.get('cityName', '')
                            })
                    
                    logger.info(f"✅ ODsay API 성공 - 응답된 교통수단:")
                    for transport in transport_summary:
                        logger.info(f"   🚌 {transport['type']}: {transport['line']} (지역: {transport['city']})")
                    
                    return {
                        "success": True,
                        "duration": path_info.get("totalTime", 0),
                        "distance": path_info.get("totalDistance", 0) / 1000,  # m to km
                        "cost": path_info.get("payment", 0),
                        "transfer_count": path_info.get("busTransitCount", 0) + path_info.get("subwayTransitCount", 0),
                        "walk_time": path_info.get("totalWalk", 0),
                        "route_data": {
                            "path_type": "public_transit",
                            "sub_paths": processed_sub_paths,
                            "summary": {
                                "total_time": path_info.get("totalTime", 0),
                                "total_distance": path_info.get("totalDistance", 0),
                                "payment": path_info.get("payment", 0),
                                "bus_transit_count": path_info.get("busTransitCount", 0),
                                "subway_transit_count": path_info.get("subwayTransitCount", 0),
                                "requested_city": target_city,
                                "city_id": city_id
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

    def _get_region_from_coordinates(self, lat: float, lng: float) -> str:
        """좌표로부터 지역 코드 추출"""
        # 주요 도시별 좌표 범위 (좁은 범위부터 넓은 범위 순으로 검사)
        
        # 광역시 (좁은 범위)
        if 35.0 <= lat <= 35.3 and 128.9 <= lng <= 129.3:
            return "부산"
        elif 37.45 <= lat <= 37.70 and 126.8 <= lng <= 127.2:
            return "서울"
        elif 35.8 <= lat <= 36.0 and 128.5 <= lng <= 128.7:
            return "대구"
        elif 37.3 <= lat <= 37.5 and 126.4 <= lng <= 126.8:
            return "인천"
        elif 35.1 <= lat <= 35.2 and 126.8 <= lng <= 127.0:
            return "광주"
        elif 36.2 <= lat <= 36.4 and 127.3 <= lng <= 127.5:
            return "대전"
        elif 35.5 <= lat <= 35.6 and 129.2 <= lng <= 129.4:
            return "울산"
        elif 33.1 <= lat <= 33.6 and 126.1 <= lng <= 126.9:
            return "제주"
        elif 36.4 <= lat <= 36.5 and 127.2 <= lng <= 127.3:
            return "세종"
        
        # 도 단위 (넓은 범위)
        elif 37.0 <= lat <= 38.3 and 126.4 <= lng <= 127.5:
            return "경기"
        elif 37.1 <= lat <= 38.8 and 127.6 <= lng <= 129.5:
            return "강원"
        elif 36.0 <= lat <= 37.2 and 127.2 <= lng <= 129.0:
            return "충북"
        elif 35.7 <= lat <= 37.0 and 126.1 <= lng <= 127.8:
            return "충남"
        elif 35.6 <= lat <= 36.8 and 126.4 <= lng <= 127.8:
            return "전북"
        elif 34.2 <= lat <= 35.8 and 126.0 <= lng <= 127.5:
            return "전남"
        elif 35.4 <= lat <= 37.2 and 128.0 <= lng <= 130.0:
            return "경북"
        elif 34.5 <= lat <= 36.0 and 127.4 <= lng <= 129.5:
            return "경남"
        else:
            return "기타"

    def _process_sub_paths(self, sub_paths: list[dict]) -> list[dict]:
        """세부 경로 정보 처리"""
        processed_paths = []

        for i, sub_path in enumerate(sub_paths):
            path_type = sub_path.get("trafficType")

            if path_type == 1:  # 지하철
                lane_info = sub_path.get("lane", [{}])[0] if sub_path.get("lane") else {}
                # 중간 정거장 정보 추출
                stations = []
                pass_stop_list = sub_path.get("passStopList", {})
                if pass_stop_list and pass_stop_list.get("stations"):
                    stations = [
                        {
                            "index": station.get("index", 0),
                            "station_id": station.get("stationID", ""),
                            "station_name": station.get("stationName", ""),
                            "x": station.get("x", ""),
                            "y": station.get("y", "")
                        }
                        for station in pass_stop_list["stations"]
                    ]

                processed_paths.append({
                    "type": "subway",
                    "lane": {
                        "name": lane_info.get("name", "지하철"),
                        "busNo": lane_info.get("busNo", ""),
                        "type": lane_info.get("type", ""),
                        "cityCode": lane_info.get("cityCode", ""),
                        "cityName": lane_info.get("cityName", ""),
                        "subway_code": lane_info.get("subwayCode", ""),
                        "subway_city_code": lane_info.get("subwayCityCode", "")
                    },
                    "start_station": sub_path.get("startName", ""),
                    "end_station": sub_path.get("endName", ""),
                    "station_count": sub_path.get("stationCount", 0),
                    "section_time": sub_path.get("sectionTime", 0),
                    "way": sub_path.get("way", ""),
                    "way_code": sub_path.get("wayCode", 0),
                    "door": sub_path.get("door", ""),
                    "stations": stations,  # 중간 정거장 목록 추가
                    "start_exit_no": sub_path.get("startExitNo", ""),
                    "end_exit_no": sub_path.get("endExitNo", "")
                })
            elif path_type == 2:  # 버스
                lane_info = sub_path.get("lane", [{}])[0] if sub_path.get("lane") else {}
                
                # 중간 정류장 정보 추출
                stations = []
                pass_stop_list = sub_path.get("passStopList", {})
                if pass_stop_list and pass_stop_list.get("stations"):
                    stations = [
                        {
                            "index": station.get("index", 0),
                            "station_id": station.get("stationID", ""),
                            "station_name": station.get("stationName", ""),
                            "x": station.get("x", ""),
                            "y": station.get("y", ""),
                            "ars_id": station.get("arsID", ""),
                            "local_station_id": station.get("localStationID", ""),
                            "is_non_stop": station.get("isNonStop", "N") == "Y"
                        }
                        for station in pass_stop_list["stations"]
                    ]

                processed_paths.append({
                    "type": "bus",
                    "lane": {
                        "name": lane_info.get("name", "버스"),
                        "busNo": lane_info.get("busNo", ""),
                        "type": lane_info.get("type", ""),
                        "cityCode": lane_info.get("cityCode", ""),
                        "cityName": lane_info.get("cityName", ""),
                        "bus_id": lane_info.get("busID", ""),
                        "bus_local_bl_id": lane_info.get("busLocalBlID", "")
                    },
                    "start_station": sub_path.get("startName", ""),
                    "end_station": sub_path.get("endName", ""),
                    "station_count": sub_path.get("stationCount", 0),
                    "section_time": sub_path.get("sectionTime", 0),
                    "way": sub_path.get("way", ""),
                    "way_code": sub_path.get("wayCode", 0),
                    "stations": stations,  # 중간 정류장 목록 추가
                    "start_ars_id": sub_path.get("startArsID", ""),
                    "end_ars_id": sub_path.get("endArsID", "")
                })
            elif path_type == 3:  # 도보
                # 도보 구간의 출발지/도착지 추론
                start_location = ""
                end_location = ""
                
                # 이전/다음 교통수단으로부터 위치 추론
                if i > 0:  # 이전 구간이 있는 경우
                    prev_path = sub_paths[i-1]
                    if prev_path.get("trafficType") in [1, 2]:  # 지하철 또는 버스
                        start_location = prev_path.get("endName", "")
                
                if i < len(sub_paths) - 1:  # 다음 구간이 있는 경우
                    next_path = sub_paths[i+1]
                    if next_path.get("trafficType") in [1, 2]:  # 지하철 또는 버스
                        end_location = next_path.get("startName", "")
                
                # 첫 번째 도보구간이면 출발지, 마지막 도보구간이면 목적지
                if i == 0:
                    start_location = "출발지"
                if i == len(sub_paths) - 1:
                    end_location = "목적지"
                
                processed_paths.append({
                    "type": "walk",
                    "start_station": start_location,
                    "end_station": end_location,
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
