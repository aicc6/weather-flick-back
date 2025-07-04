
import httpx

from app.config import settings


class NaverMapService:
    def __init__(self):
        self.client_id = getattr(settings, "naver_client_id", None)
        self.client_secret = getattr(settings, "naver_client_secret", None)
        self.map_api_url = "https://naveropenapi.apigw.ntruss.com/map-api/v1"

    async def search_places(
        self, query: str, location: str = None, category: str = None, limit: int = 20
    ) -> list[dict]:
        """네이버 지도 API를 사용한 장소 검색"""
        if not self.client_id or not self.client_secret:
            return []

        async with httpx.AsyncClient() as client:
            headers = {
                "X-NCP-APIGW-API-KEY-ID": self.client_id,
                "X-NCP-APIGW-API-KEY": self.client_secret,
            }

            params = {
                "query": query,
                "display": limit,
                "start": 1,
                "sort": "random",  # 정확도순 정렬
            }

            if location:
                params["location"] = location

            try:
                response = await client.get(
                    "https://openapi.naver.com/v1/search/local.json",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                return [
                    {
                        "title": item["title"].replace("<b>", "").replace("</b>", ""),
                        "address": item["address"],
                        "road_address": item.get("roadAddress", ""),
                        "category": item["category"],
                        "description": item["description"]
                        .replace("<b>", "")
                        .replace("</b>", ""),
                        "telephone": item.get("telephone", ""),
                        "link": item.get("link", ""),
                        "mapx": float(item["mapx"]),
                        "mapy": float(item["mapy"]),
                        "source": "네이버",
                    }
                    for item in data.get("items", [])
                ]
            except Exception as e:
                print(f"네이버 지도 API 오류: {e}")
                return []

    async def get_route_guidance(
        self, start: str, goal: str, mode: str = "driving"
    ) -> dict:
        """경로 안내 (네이버 지도 API)"""
        if not self.client_id or not self.client_secret:
            return {"error": "API 키가 설정되지 않았습니다."}

        # 네이버 지도 API는 직접적인 경로 안내를 제공하지 않으므로
        # 대신 지도 URL과 기본 정보를 반환
        return {
            "start": start,
            "goal": goal,
            "mode": mode,
            "map_url": f"https://map.naver.com/v5/directions/{start}/{goal}",
            "message": "네이버 지도에서 경로를 확인하세요.",
        }

    async def get_nearby_places(
        self,
        latitude: float,
        longitude: float,
        radius: float = 1000,
        category: str = None,
    ) -> list[dict]:
        """주변 장소 검색"""
        if not self.client_id or not self.client_secret:
            return []

        # 위도/경도를 주소로 변환
        location = f"{latitude},{longitude}"

        # 주변 검색을 위한 쿼리 구성
        query = "주변"
        if category:
            query += f" {category}"

        return await self.search_places(query, location, category, 20)

    async def get_place_details(self, place_id: str) -> dict | None:
        """장소 상세 정보 조회"""
        if not self.client_id or not self.client_secret:
            return None

        # 네이버 지도 API는 개별 장소 상세 정보를 직접 제공하지 않으므로
        # 기본 정보만 반환
        return {
            "place_id": place_id,
            "message": "상세 정보는 네이버 지도에서 확인하세요.",
        }

    async def get_map_embed_url(
        self,
        latitude: float,
        longitude: float,
        zoom: int = 15,
        width: int = 600,
        height: int = 400,
    ) -> str:
        """네이버 지도 임베드 URL 생성"""
        return f"https://map.naver.com/v5/embed/place/{latitude},{longitude}?zoom={zoom}&width={width}&height={height}"

    async def get_static_map_url(
        self,
        latitude: float,
        longitude: float,
        zoom: int = 15,
        width: int = 600,
        height: int = 400,
    ) -> str:
        """정적 지도 이미지 URL 생성"""
        # 네이버 지도는 정적 지도 API를 직접 제공하지 않으므로
        # 동적 지도 URL을 반환
        return f"https://map.naver.com/v5/staticmap?lat={latitude}&lng={longitude}&zoom={zoom}&size={width}x{height}"

    async def search_restaurants_nearby(
        self, latitude: float, longitude: float, radius: float = 1000
    ) -> list[dict]:
        """주변 맛집 검색"""
        return await self.get_nearby_places(latitude, longitude, radius, "맛집")

    async def search_hotels_nearby(
        self, latitude: float, longitude: float, radius: float = 1000
    ) -> list[dict]:
        """주변 숙소 검색"""
        return await self.get_nearby_places(latitude, longitude, radius, "호텔")

    async def search_transportation_nearby(
        self, latitude: float, longitude: float, radius: float = 1000
    ) -> list[dict]:
        """주변 교통 정보 검색"""
        return await self.get_nearby_places(latitude, longitude, radius, "지하철역")

    async def get_city_coordinates(self, city: str) -> dict | None:
        """도시의 좌표 정보"""
        city_coordinates = {
            "서울": {"latitude": 37.5665, "longitude": 126.9780},
            "부산": {"latitude": 35.1796, "longitude": 129.0756},
            "대구": {"latitude": 35.8714, "longitude": 128.6014},
            "인천": {"latitude": 37.4563, "longitude": 126.7052},
            "광주": {"latitude": 35.1595, "longitude": 126.8526},
            "대전": {"latitude": 36.3504, "longitude": 127.3845},
            "울산": {"latitude": 35.5384, "longitude": 129.3114},
            "세종": {"latitude": 36.4800, "longitude": 127.2890},
            "수원": {"latitude": 37.2636, "longitude": 127.0286},
            "고양": {"latitude": 37.6584, "longitude": 126.8320},
            "용인": {"latitude": 37.2411, "longitude": 127.1776},
            "창원": {"latitude": 35.2278, "longitude": 128.6817},
            "포항": {"latitude": 36.0320, "longitude": 129.3650},
            "제주": {"latitude": 33.4996, "longitude": 126.5312},
        }

        return city_coordinates.get(city)

    async def get_map_widget_html(
        self,
        latitude: float,
        longitude: float,
        zoom: int = 15,
        width: int = 600,
        height: int = 400,
    ) -> str:
        """네이버 지도 위젯 HTML 생성"""
        return f"""
        <div id="map" style="width:{width}px;height:{height}px;"></div>
        <script type="text/javascript" src="https://openapi.map.naver.com/openapi/v3/maps.js?ncpClientId={self.client_id}"></script>
        <script>
            var map = new naver.maps.Map('map', {{
                center: new naver.maps.LatLng({latitude}, {longitude}),
                zoom: {zoom}
            }});

            var marker = new naver.maps.Marker({{
                position: new naver.maps.LatLng({latitude}, {longitude}),
                map: map
            }});
        </script>
        """

    async def search_with_coordinates(
        self, latitude: float, longitude: float, query: str, limit: int = 20
    ) -> list[dict]:
        """좌표 기반 장소 검색"""
        location = f"{latitude},{longitude}"
        return await self.search_places(query, location, limit=limit)


naver_map_service = NaverMapService()
