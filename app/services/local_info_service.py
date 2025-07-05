import httpx
from sqlalchemy.orm import Session
from typing import Any, Optional

from app.config import settings
from app.models import Region


class LocalInfoService:
    def __init__(self):
        self.kakao_api_key = getattr(settings, "kakao_api_key", None)
        self.naver_client_id = getattr(settings, "naver_client_id", None)
        self.naver_client_secret = getattr(settings, "naver_client_secret", None)
        self.google_api_key = getattr(settings, "google_api_key", None)
        self.public_data_api_key = getattr(settings, "public_data_api_key", None)
        self.korea_tourism_api_key = getattr(settings, "korea_tourism_api_key", None)

    async def _search_db_restaurants(
        self,
        db: Session,
        city: Optional[str],
        region: Optional[str] = None,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """DB restaurants 테이블에서 직접 맛집 검색"""
        from app.models import Restaurant
        query = db.query(Restaurant)
        if city:
            query = query.filter(Restaurant.address.ilike(f"%{city}%"))
        if region:
            query = query.filter(Restaurant.address.ilike(f"%{region}%"))
        if category:
            query = query.filter(Restaurant.category_code == category)
        if keyword:
            query = query.filter(Restaurant.restaurant_name.ilike(f"%{keyword}%"))
        results = query.limit(limit).all()
        return [
            {
                "content_id": r.content_id,
                "region_code": r.region_code,
                "restaurant_name": r.restaurant_name,
                "category_code": r.category_code,
                "sub_category_code": r.sub_category_code,
                "address": r.address,
                "detail_address": r.detail_address,
                "zipcode": r.zipcode,
                "tel": r.tel,
                "homepage": r.homepage,
                "overview": r.overview,
                "first_image": r.first_image,
                "first_image_small": r.first_image_small,
                "cuisine_type": r.cuisine_type,
                "specialty_dish": r.specialty_dish,
                "operating_hours": r.operating_hours,
                "rest_date": r.rest_date,
                "reservation_info": r.reservation_info,
                "credit_card": r.credit_card,
                "smoking": r.smoking,
                "parking": r.parking,
                "room_available": r.room_available,
                "children_friendly": r.children_friendly,
                "takeout": r.takeout,
                "delivery": r.delivery,
                "latitude": float(r.latitude) if r.latitude is not None else None,
                "longitude": float(r.longitude) if r.longitude is not None else None,
                "data_quality_score": float(r.data_quality_score) if r.data_quality_score is not None else None,
                "raw_data_id": str(r.raw_data_id) if r.raw_data_id else None,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "last_sync_at": r.last_sync_at,
                "processing_status": r.processing_status,
            }
            for r in results
        ]

    async def search_restaurants(
        self,
        city: Optional[str],
        region: Optional[str] = None,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 20,
        db: Optional[Session] = None,
    ) -> list[dict[str, Any]]:
        """맛집 검색 (DB → 외부 API → 내장 데이터)"""
        results = []
        if db is not None:
            db_results = await self._search_db_restaurants(
                db, city, region, category, keyword, limit
            )
            results.extend(db_results)
        # 기존 외부 API/내장 데이터 로직 유지
        if not results:
            # 카카오 API로 맛집 검색
            if self.kakao_api_key:
                kakao_results = await self._search_kakao_restaurants(
                    city or "", category or "", keyword or "", limit
                )
                results.extend(kakao_results)
            # 한국관광공사 API로 맛집 검색
            if self.korea_tourism_api_key:
                tourism_results = await self._search_korea_tourism_restaurants(
                    city or "", keyword or "", limit
                )
                results.extend(tourism_results)
            # 내장 데이터로 보완
            if not results:
                results = await self._search_local_restaurants(
                    city or "", region or "", category or "", keyword or "", limit
                )
        unique_results = self._remove_duplicates(results)
        return unique_results[:limit]

    async def search_transportation(
        self, city: str, region: str = None, transport_type: str = None, limit: int = 20
    ) -> list[dict]:
        """교통 정보 검색 (공공데이터포털 API 사용)"""
        results = []

        # 공공데이터포털 API로 교통 정보 검색
        if self.public_data_api_key:
            public_results = await self._search_public_transportation(
                city, transport_type, limit
            )
            results.extend(public_results)

        # 내장 데이터로 보완
        if not results:
            results = await self._search_local_transportation(
                city, region, transport_type, limit
            )

        return results[:limit]

    async def search_accommodations(
        self,
        city: str,
        region: str = None,
        accommodation_type: str = None,
        limit: int = 20,
    ) -> list[dict]:
        """숙소 정보 검색 (한국관광공사 API 사용)"""
        results = []

        # 한국관광공사 API로 숙소 검색
        if self.korea_tourism_api_key:
            tourism_results = await self._search_korea_tourism_accommodations(
                city, accommodation_type, limit
            )
            results.extend(tourism_results)

        # 내장 데이터로 보완
        if not results:
            results = await self._search_local_accommodations(
                city, region, accommodation_type, limit
            )

        return results[:limit]

    async def get_city_info(self, city: str) -> dict | None:
        """도시 정보 조회 (한국관광공사 API 사용)"""
        # 한국관광공사 API로 도시 정보 검색
        if self.korea_tourism_api_key:
            tourism_info = await self._get_korea_tourism_city_info(city)
            if tourism_info:
                return tourism_info

        # 내장 데이터로 보완
        return await self._get_local_city_info(city)

    async def _search_kakao_restaurants(
        self, city: str, category: str = None, keyword: str = None, limit: int = 20
    ) -> list[dict]:
        """카카오 API를 사용한 맛집 검색"""
        if not self.kakao_api_key:
            return []

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
            params = {
                "query": f"{city} {keyword or ''} 맛집",
                "category_group_code": "FD6",  # 음식점 카테고리
                "size": limit,
            }

            try:
                response = await client.get(
                    "https://dapi.kakao.com/v2/local/search/keyword.json",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                return [
                    {
                        "name": place["place_name"],
                        "address": place["address_name"],
                        "phone": place.get("phone", ""),
                        "category": self._categorize_restaurant(
                            place.get("category_name", "")
                        ),
                        "rating": None,
                        "price_range": "보통",
                        "description": f"{place.get('category_name', '')}",
                        "operating_hours": "",
                        "latitude": float(place["y"]),
                        "longitude": float(place["x"]),
                        "city": city,
                        "region": (
                            place.get("address_name", "").split()[0]
                            if place.get("address_name")
                            else ""
                        ),
                        "source": "카카오",
                    }
                    for place in data.get("documents", [])
                ]
            except Exception as e:
                print(f"카카오 API 오류: {e}")
                return []

    async def _search_korea_tourism_restaurants(
        self, city: str, keyword: str = None, limit: int = 20
    ) -> list[dict]:
        """한국관광공사 API를 사용한 맛집 검색"""
        if not self.korea_tourism_api_key:
            return []

        async with httpx.AsyncClient() as client:
            params = {
                "serviceKey": self.korea_tourism_api_key,
                "numOfRows": limit,
                "pageNo": 1,
                "MobileOS": "ETC",
                "MobileApp": "WeatherFlick",
                "_type": "json",
                "listYN": "Y",
                "arrange": "A",  # 이름순 정렬
                "contentTypeId": "39",  # 음식점
                "areaCode": self._get_area_code(city),
                "keyword": keyword or "",
            }

            try:
                response = await client.get(
                    "http://api.visitkorea.or.kr/openapi/service/rest/KorService/searchKeyword",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                items = (
                    data.get("response", {})
                    .get("body", {})
                    .get("items", {})
                    .get("item", [])
                )
                if not isinstance(items, list):
                    items = [items]

                return [
                    {
                        "name": item.get("title", "")
                        .replace("<b>", "")
                        .replace("</b>", ""),
                        "address": item.get("addr1", ""),
                        "phone": item.get("tel", ""),
                        "category": "한식",  # 기본값
                        "rating": None,
                        "price_range": "보통",
                        "description": item.get("overview", ""),
                        "operating_hours": "",
                        "latitude": float(item.get("mapY", 0)),
                        "longitude": float(item.get("mapX", 0)),
                        "city": city,
                        "region": "",
                        "source": "한국관광공사",
                    }
                    for item in items
                ]
            except Exception as e:
                print(f"한국관광공사 API 오류: {e}")
                return []

    async def _search_public_transportation(
        self, city: str, transport_type: str = None, limit: int = 20
    ) -> list[dict]:
        """공공데이터포털 API를 사용한 교통 정보 검색"""
        if not self.public_data_api_key:
            return []

        # 지하철 정보 검색
        if not transport_type or transport_type == "지하철":
            subway_results = await self._search_subway_info(city, limit)
            return subway_results

        return []

    async def _search_subway_info(self, city: str, limit: int = 20) -> list[dict]:
        """지하철 정보 검색"""
        subway_data = {
            "서울": [
                {
                    "name": "서울 지하철 1호선",
                    "type": "지하철",
                    "description": "서울 도심을 관통하는 주요 지하철 노선",
                    "route_info": "소요산 ↔ 인천",
                    "operating_hours": "05:30-24:00",
                    "fare_info": "기본요금 1,250원",
                    "contact": "02-6110-1234",
                    "city": "서울",
                    "region": "전체",
                    "source": "공공데이터",
                },
                {
                    "name": "서울 지하철 2호선",
                    "type": "지하철",
                    "description": "순환선 형태의 지하철 노선",
                    "route_info": "순환선",
                    "operating_hours": "05:30-24:00",
                    "fare_info": "기본요금 1,250원",
                    "contact": "02-6110-1234",
                    "city": "서울",
                    "region": "전체",
                    "source": "공공데이터",
                },
            ],
            "부산": [
                {
                    "name": "부산 지하철 1호선",
                    "type": "지하철",
                    "description": "부산 도심을 관통하는 지하철",
                    "route_info": "노포 ↔ 다대포해수욕장",
                    "operating_hours": "05:30-24:00",
                    "fare_info": "기본요금 1,300원",
                    "contact": "051-123-4567",
                    "city": "부산",
                    "region": "전체",
                    "source": "공공데이터",
                }
            ],
        }

        return subway_data.get(city, [])

    async def _search_korea_tourism_accommodations(
        self, city: str, accommodation_type: str = None, limit: int = 20
    ) -> list[dict]:
        """한국관광공사 API를 사용한 숙소 검색"""
        if not self.korea_tourism_api_key:
            return []

        async with httpx.AsyncClient() as client:
            params = {
                "serviceKey": self.korea_tourism_api_key,
                "numOfRows": limit,
                "pageNo": 1,
                "MobileOS": "ETC",
                "MobileApp": "WeatherFlick",
                "_type": "json",
                "listYN": "Y",
                "arrange": "A",
                "contentTypeId": "32",  # 숙박
                "areaCode": self._get_area_code(city),
            }

            try:
                response = await client.get(
                    "http://api.visitkorea.or.kr/openapi/service/rest/KorService/areaBasedList",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                items = (
                    data.get("response", {})
                    .get("body", {})
                    .get("items", {})
                    .get("item", [])
                )
                if not isinstance(items, list):
                    items = [items]

                return [
                    {
                        "name": item.get("title", "")
                        .replace("<b>", "")
                        .replace("</b>", ""),
                        "address": item.get("addr1", ""),
                        "phone": item.get("tel", ""),
                        "type": self._categorize_accommodation(item.get("cat3", "")),
                        "rating": None,
                        "price_range": "보통",
                        "amenities": [],
                        "description": item.get("overview", ""),
                        "check_in": "15:00",
                        "check_out": "11:00",
                        "latitude": float(item.get("mapY", 0)),
                        "longitude": float(item.get("mapX", 0)),
                        "city": city,
                        "region": "",
                        "source": "한국관광공사",
                    }
                    for item in items
                ]
            except Exception as e:
                print(f"한국관광공사 숙소 API 오류: {e}")
                return []

    async def _get_korea_tourism_city_info(self, city: str) -> dict | None:
        """한국관광공사 API로 도시 정보 조회"""
        if not self.korea_tourism_api_key:
            return None

        # 내장 데이터 반환 (API 호출 대신)
        return await self._get_local_city_info(city)

    def _categorize_restaurant(self, category_name: str) -> str:
        """카테고리명을 기반으로 맛집 분류"""
        category_name = category_name.lower()
        if any(
            keyword in category_name for keyword in ["한식", "국밥", "김치", "비빔밥"]
        ):
            return "한식"
        elif any(
            keyword in category_name
            for keyword in ["중식", "짜장면", "탕수육", "마파두부"]
        ):
            return "중식"
        elif any(
            keyword in category_name for keyword in ["일식", "초밥", "라멘", "우동"]
        ):
            return "일식"
        elif any(
            keyword in category_name
            for keyword in ["양식", "파스타", "피자", "스테이크"]
        ):
            return "양식"
        elif any(keyword in category_name for keyword in ["카페", "커피", "디저트"]):
            return "카페"
        else:
            return "기타"

    def _categorize_accommodation(self, category_name: str) -> str:
        """카테고리명을 기반으로 숙소 분류"""
        category_name = category_name.lower()
        if "호텔" in category_name:
            return "호텔"
        elif "펜션" in category_name:
            return "펜션"
        elif "게스트" in category_name:
            return "게스트하우스"
        elif "모텔" in category_name:
            return "모텔"
        elif "리조트" in category_name:
            return "리조트"
        else:
            return "호텔"

    def _get_area_code(self, city: str) -> str:
        """도시명을 기반으로 지역 코드 반환"""
        area_codes = {
            "서울": "1",
            "인천": "2",
            "대전": "3",
            "대구": "4",
            "광주": "5",
            "부산": "6",
            "울산": "7",
            "세종": "8",
            "경기": "31",
            "강원": "32",
            "충북": "33",
            "충남": "34",
            "경북": "35",
            "경남": "36",
            "전북": "37",
            "전남": "38",
            "제주": "39",
        }
        return area_codes.get(city, "1")

    def _remove_duplicates(self, results: list[dict]) -> list[dict]:
        """중복 결과 제거"""
        seen = set()
        unique_results = []

        for result in results:
            # DB 결과는 restaurant_name, 외부/내장 데이터는 name
            name = result.get("restaurant_name") or result.get("name")
            address = result.get("address")
            key = (name, address)
            if key not in seen:
                seen.add(key)
                unique_results.append(result)

        return unique_results

    async def _search_local_restaurants(
        self,
        city: str,
        region: str = None,
        category: str = None,
        keyword: str = None,
        limit: int = 20,
    ) -> list[dict]:
        """내장 맛집 데이터 검색"""
        # 주요 도시별 맛집 데이터
        restaurants_data = {
            "서울": [
                {
                    "name": "광장시장 빈대떡",
                    "address": "서울특별시 종로구 창경궁로 88",
                    "phone": "02-2267-0291",
                    "category": "한식",
                    "rating": 4.5,
                    "price_range": "저렴",
                    "description": "전통 빈대떡과 막걸리",
                    "operating_hours": "09:00-22:00",
                    "latitude": 37.5704,
                    "longitude": 126.9997,
                    "city": "서울",
                    "region": "종로구",
                },
                {
                    "name": "명동교자",
                    "address": "서울특별시 중구 명동10길 29",
                    "phone": "02-776-5348",
                    "category": "한식",
                    "rating": 4.3,
                    "price_range": "보통",
                    "description": "유명한 칼국수와 만두",
                    "operating_hours": "10:30-21:30",
                    "latitude": 37.5636,
                    "longitude": 126.9834,
                    "city": "서울",
                    "region": "중구",
                },
            ],
            "부산": [
                {
                    "name": "해운대 해물탕",
                    "address": "부산광역시 해운대구 해운대해변로 264",
                    "phone": "051-749-1234",
                    "category": "한식",
                    "rating": 4.4,
                    "price_range": "고급",
                    "description": "신선한 해산물 요리",
                    "operating_hours": "11:00-22:00",
                    "latitude": 35.1586,
                    "longitude": 129.1603,
                    "city": "부산",
                    "region": "해운대구",
                }
            ],
            "대구": [
                {
                    "name": "대구막창",
                    "address": "대구광역시 중구 동성로 123",
                    "phone": "053-123-4567",
                    "category": "한식",
                    "rating": 4.2,
                    "price_range": "보통",
                    "description": "대구 대표 음식 막창",
                    "operating_hours": "17:00-02:00",
                    "latitude": 35.8714,
                    "longitude": 128.6014,
                    "city": "대구",
                    "region": "중구",
                }
            ],
        }

        results = restaurants_data.get(city, [])

        # 필터링
        if region:
            results = [r for r in results if r["region"] == region]
        if category:
            results = [r for r in results if r["category"] == category]
        if keyword:
            results = [
                r
                for r in results
                if keyword.lower() in r["name"].lower()
                or keyword.lower() in r["description"].lower()
            ]

        return results[:limit]

    async def _search_local_transportation(
        self, city: str, region: str = None, transport_type: str = None, limit: int = 20
    ) -> list[dict]:
        """내장 교통 정보 데이터 검색"""
        transportation_data = {
            "서울": [
                {
                    "name": "서울 지하철 1호선",
                    "type": "지하철",
                    "description": "서울 도심을 관통하는 주요 지하철 노선",
                    "route_info": "소요산 ↔ 인천",
                    "operating_hours": "05:30-24:00",
                    "fare_info": "기본요금 1,250원",
                    "contact": "02-6110-1234",
                    "city": "서울",
                    "region": "전체",
                },
                {
                    "name": "공항철도",
                    "type": "기차",
                    "description": "서울시내와 인천공항을 연결하는 전철",
                    "route_info": "서울역 ↔ 인천공항",
                    "operating_hours": "05:20-24:00",
                    "fare_info": "기본요금 4,150원",
                    "contact": "02-6110-1234",
                    "city": "서울",
                    "region": "전체",
                },
            ],
            "부산": [
                {
                    "name": "부산 지하철 1호선",
                    "type": "지하철",
                    "description": "부산 도심을 관통하는 지하철",
                    "route_info": "노포 ↔ 다대포해수욕장",
                    "operating_hours": "05:30-24:00",
                    "fare_info": "기본요금 1,300원",
                    "contact": "051-123-4567",
                    "city": "부산",
                    "region": "전체",
                }
            ],
        }

        results = transportation_data.get(city, [])

        if transport_type:
            results = [t for t in results if t["type"] == transport_type]

        return results[:limit]

    async def _search_local_accommodations(
        self,
        city: str,
        region: str = None,
        accommodation_type: str = None,
        limit: int = 20,
    ) -> list[dict]:
        """내장 숙소 정보 데이터 검색"""
        accommodation_data = {
            "서울": [
                {
                    "name": "롯데호텔 서울",
                    "address": "서울특별시 중구 을지로 30",
                    "phone": "02-771-1000",
                    "type": "호텔",
                    "rating": 4.8,
                    "price_range": "럭셔리",
                    "amenities": ["수영장", "피트니스", "레스토랑", "스파"],
                    "description": "5성급 럭셔리 호텔",
                    "check_in": "15:00",
                    "check_out": "11:00",
                    "latitude": 37.5644,
                    "longitude": 126.9819,
                    "city": "서울",
                    "region": "중구",
                },
                {
                    "name": "명동 게스트하우스",
                    "address": "서울특별시 중구 명동2길 25",
                    "phone": "02-777-1234",
                    "type": "게스트하우스",
                    "rating": 4.2,
                    "price_range": "저렴",
                    "amenities": ["무료 와이파이", "공용 주방", "세탁기"],
                    "description": "친근한 분위기의 게스트하우스",
                    "check_in": "14:00",
                    "check_out": "11:00",
                    "latitude": 37.5636,
                    "longitude": 126.9834,
                    "city": "서울",
                    "region": "중구",
                },
            ],
            "부산": [
                {
                    "name": "해운대 마린뷰 호텔",
                    "address": "부산광역시 해운대구 해운대해변로 264",
                    "phone": "051-749-1234",
                    "type": "호텔",
                    "rating": 4.5,
                    "price_range": "고급",
                    "amenities": ["오션뷰", "레스토랑", "피트니스"],
                    "description": "해운대 해변 전망 호텔",
                    "check_in": "15:00",
                    "check_out": "11:00",
                    "latitude": 35.1586,
                    "longitude": 129.1603,
                    "city": "부산",
                    "region": "해운대구",
                }
            ],
        }

        results = accommodation_data.get(city, [])

        if accommodation_type:
            results = [a for a in results if a["type"] == accommodation_type]

        return results[:limit]

    async def _get_local_city_info(self, city: str) -> dict | None:
        """내장 도시 정보 데이터"""
        city_info_data = {
            "서울": {
                "city": "서울",
                "region": "수도권",
                "description": "대한민국의 수도이자 최대 도시",
                "attractions": ["경복궁", "남산타워", "홍대", "강남", "명동"],
                "best_time_to_visit": "3월-5월, 9월-11월",
                "population": 9700000,
                "area": 605.2,
            },
            "부산": {
                "city": "부산",
                "region": "경상남도",
                "description": "해양도시이자 제2의 도시",
                "attractions": ["해운대", "광안대교", "감천문화마을", "태종대"],
                "best_time_to_visit": "6월-8월 (해수욕장)",
                "population": 3400000,
                "area": 770.0,
            },
            "대구": {
                "city": "대구",
                "region": "경상북도",
                "description": "내륙의 중심도시",
                "attractions": ["동성로", "수성못", "팔공산", "앞산공원"],
                "best_time_to_visit": "4월-5월 (벚꽃), 10월-11월",
                "population": 2400000,
                "area": 884.0,
            },
            "인천": {
                "city": "인천",
                "region": "수도권",
                "description": "항구도시이자 공항도시",
                "attractions": ["인천공항", "월미도", "차이나타운", "송도"],
                "best_time_to_visit": "4월-10월",
                "population": 2900000,
                "area": 1062.6,
            },
            "광주": {
                "city": "광주",
                "region": "전라남도",
                "description": "예향의 도시",
                "attractions": ["무등산", "광주비엔날레", "상무지구", "양림동"],
                "best_time_to_visit": "3월-5월, 9월-11월",
                "population": 1500000,
                "area": 501.2,
            },
        }

        return city_info_data.get(city)

    async def get_supported_cities(self) -> list[str]:
        """지원되는 도시 목록"""
        return [
            "서울",
            "부산",
            "대구",
            "인천",
            "광주",
            "대전",
            "울산",
            "세종",
            "수원",
            "고양",
            "용인",
            "창원",
            "포항",
            "제주",
        ]

    async def get_regions_with_si_gun(self, db):
        """
        region_name이 '시' 또는 '군'으로 끝나는 지역만 조회
        """
        query = db.query(Region).filter(
            (Region.region_name.like('%시')) | (Region.region_name.like('%군'))
        )
        regions = query.all()
        return [
            {
                "region_code": r.region_code,
                "region_name": r.region_name,
                "parent_region_code": r.parent_region_code,
                "latitude": r.latitude,
                "longitude": r.longitude,
            }
            for r in regions
        ]

    async def get_regions_point(self, db):
        """
        region_level이 1인 지역만 조회
        """
        query = db.query(Region).filter(Region.region_level == 1)
        regions = query.all()
        return [
            {
                "region_code": r.region_code,
                "region_name": r.region_name,
                "parent_region_code": r.parent_region_code,
                "latitude": r.latitude,
                "longitude": r.longitude,
            }
            for r in regions
        ]

    async def get_unified_regions_level1(self, db: Session):
        """
        unified_regions 테이블에서 region_level=1인 지역만 조회
        """
        from app.models import UnifiedRegion
        query = db.query(UnifiedRegion).filter(UnifiedRegion.region_level == 1)
        regions = query.all()
        return [
            {
                "region_id": str(r.region_id),
                "region_code": r.region_code,
                "region_name": r.region_name,
                "region_name_full": r.region_name_full,
                "region_name_en": r.region_name_en,
                "center_latitude": r.center_latitude,
                "center_longitude": r.center_longitude,
                "administrative_code": r.administrative_code,
                "is_active": r.is_active,
            }
            for r in regions
        ]


local_info_service = LocalInfoService()
