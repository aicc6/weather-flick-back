"""
Google Places API 서비스
Place ID로부터 장소 정보 및 좌표를 조회하는 기능 제공
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import requests

from app.config import settings
import httpx



class GooglePlacesService:
    def __init__(self):
        self.api_key = settings.google_api_key
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        self.executor = ThreadPoolExecutor(max_workers=10)

    def _get_place_details_sync(self, place_id: str) -> dict[str, Any] | None:
        """
        Place ID로부터 장소의 상세 정보(좌표 포함)를 동기적으로 조회
        """
        if not self.api_key:
            print("Google Maps API 키가 설정되지 않았습니다.")
            return None

        url = f"{self.base_url}/details/json"
        params = {
            'place_id': place_id,
            'fields': 'name,formatted_address,geometry,place_id',
            'key': self.api_key,
            'language': 'ko'
        }

        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get('status') == 'OK' and 'result' in data:
                    result = data['result']
                    geometry = result.get('geometry', {})
                    location = geometry.get('location', {})

                    return {
                        'place_id': result.get('place_id'),
                        'name': result.get('name'),
                        'formatted_address': result.get('formatted_address'),
                        'latitude': location.get('lat'),
                        'longitude': location.get('lng')
                    }
                else:
                    print(f"Google Places API 오류: {data.get('status')}")
                    return None
            else:
                print(f"HTTP 오류: {response.status_code}")
                return None

        except Exception as e:
            print(f"Google Places API 호출 중 오류: {str(e)}")
            return None

    async def get_place_details(self, place_id: str) -> dict[str, Any] | None:
        """
        Place ID로부터 장소의 상세 정보(좌표 포함)를 조회

        Args:
            place_id: Google Place ID

        Returns:
            장소 정보 딕셔너리 (좌표, 이름, 주소 등)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._get_place_details_sync, place_id)

    async def get_place_reviews_and_rating(self, place_id: str) -> Dict[str, Any]:
        """
        구글 Places API에서 리뷰 및 평점 정보를 가져옵니다.
        """
        api_key = self.api_key  # settings.google_api_key로 통일
        url = (
            "https://maps.googleapis.com/maps/api/place/details/json"
            f"?place_id={place_id}&fields=rating,reviews,user_ratings_total&language=ko&key={api_key}"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result", {})
            return {
                "google_rating": result.get("rating"),
                "google_reviews": result.get("reviews", []),
                "google_user_ratings_total": result.get("user_ratings_total"),
            }


    async def get_multiple_place_details(self, place_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        여러 Place ID의 상세 정보를 동시에 조회

        Args:
            place_ids: Google Place ID 리스트

        Returns:
            place_id를 키로 하는 장소 정보 딕셔너리
        """
        tasks = [self.get_place_details(place_id) for place_id in place_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        place_details: Dict[str, Dict[str, Any]] = {}
        for place_id, result in zip(place_ids, results, strict=False):
            if result is not None and isinstance(result, dict):
                place_details[place_id] = result
            else:
                print(f"Place ID {place_id}의 정보를 가져올 수 없습니다.")

        return place_details

    def _search_place_by_text_sync(self, text: str) -> dict[str, Any] | None:
        """
        텍스트로 장소를 검색하여 첫 번째 결과의 좌표를 동기적으로 조회
        """
        if not self.api_key:
            print("Google Maps API 키가 설정되지 않았습니다.")
            return None

        url = f"{self.base_url}/textsearch/json"
        params = {
            'query': text,
            'fields': 'name,formatted_address,geometry,place_id',
            'key': self.api_key,
            'language': 'ko'
        }

        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get('status') == 'OK' and 'results' in data and len(data['results']) > 0:
                    result = data['results'][0]  # 첫 번째 결과 사용
                    geometry = result.get('geometry', {})
                    location = geometry.get('location', {})

                    return {
                        'place_id': result.get('place_id'),
                        'name': result.get('name'),
                        'formatted_address': result.get('formatted_address'),
                        'latitude': location.get('lat'),
                        'longitude': location.get('lng')
                    }
                else:
                    print(f"Google Places Text Search API 오류: {data.get('status')}")
                    return None
            else:
                print(f"HTTP 오류: {response.status_code}")
                return None

        except Exception as e:
            print(f"Google Places Text Search API 호출 중 오류: {str(e)}")
            return None

    async def search_place_by_text(self, text: str) -> dict[str, Any] | None:
        """
        텍스트로 장소를 검색하여 첫 번째 결과의 좌표를 조회

        Args:
            text: 검색할 장소 텍스트 (예: "서울역", "인천공항")

        Returns:
            장소 정보 딕셔너리 (좌표, 이름, 주소 등)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._search_place_by_text_sync, text)

# 전역 인스턴스
google_places_service = GooglePlacesService()
