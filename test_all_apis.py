import asyncio
import os
import sys
from collections.abc import Coroutine

import httpx

# 프로젝트 루트를 경로에 추가하여 app 모듈을 찾을 수 있도록 함
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.services import tour_api_service
from app.services.kma_weather_service import KMAWeatherService
from app.services.local_info_service import LocalInfoService
from app.services.weather_service import WeatherService
from app.utils.kma_utils import CITY_COORDINATES

# --- 테스트 설정 ---
TEST_CITY = "Seoul"
TEST_LOCATION_QUERY = "강남역"
TEST_KMA_CITY_NAME = "서울"
TEST_KMA_CITY_COORDS = CITY_COORDINATES.get(TEST_KMA_CITY_NAME)
TEST_TOUR_AREA_CODE = "1"  # (서울)
TEST_TOUR_START_DATE = "20240101"

# --- 서비스 초기화 ---
weather_service = WeatherService()
kma_service = KMAWeatherService()
local_info_service = LocalInfoService()


async def run_test(name: str, coro: Coroutine):
    """테스트를 실행하고 결과를 출력하는 헬퍼 함수"""
    print(f"--- [START] {name} 테스트 ---")
    try:
        result = await coro
        if result and (isinstance(result, list) and result or isinstance(result, dict) and result):
            print(f"✅ [SUCCESS] {name}: API 호출에 성공했으며, 유효한 데이터를 수신했습니다.")
        elif result is None or (isinstance(result, list) and not result) or (isinstance(result, dict) and not result):
            print(f"⚠️ [WARNING] {name}: API 호출은 성공했으나, 반환된 데이터가 없습니다. (입력 값 또는 API 키 권한 확인 필요)")
        else:
            print(f"❌ [FAIL] {name}: API가 예상치 못한 응답을 반환했습니다. 응답: {result}")
    except Exception as e:
        print(f"❌ [ERROR] {name}: API 호출 중 오류 발생 - {type(e).__name__}: {e}")
    finally:
        print(f"--- [END] {name} 테스트 ---\n")


async def main():
    """모든 API 서비스를 테스트하는 메인 함수"""
    print("=========================================")
    print("   모든 API 서비스 연결 상태 테스트 시작   ")
    print("=========================================\n")

    # 1. WeatherAPI 테스트
    if settings.weather_api_key:
        await run_test("WeatherAPI", weather_service.get_current_weather(TEST_CITY))
    else:
        print("⚠️ [SKIP] WeatherAPI: API 키가 설정되지 않았습니다.\n")

    # 2. 기상청(KMA) API 테스트
    if settings.kma_api_key and TEST_KMA_CITY_COORDS:
        await run_test(
            "기상청(KMA) API",
            kma_service.get_current_weather(nx=TEST_KMA_CITY_COORDS['nx'], ny=TEST_KMA_CITY_COORDS['ny'])
        )
    elif not settings.kma_api_key:
        print("⚠️ [SKIP] 기상청(KMA) API: API 키가 설정되지 않았습니다.\n")
    else:
        print(f"❌ [FAIL] 기상청(KMA) API: 테스트 도시 '{TEST_KMA_CITY_NAME}'의 좌표를 찾을 수 없습니다.\n")

    # 3. 카카오(Kakao) API 테스트 (맛집 검색)
    if settings.kakao_api_key:
        await run_test(
            "카카오(Kakao) 맛집 검색 API",
            local_info_service._search_kakao_restaurants(city=TEST_KMA_CITY_NAME, keyword=TEST_LOCATION_QUERY)
        )
    else:
        print("⚠️ [SKIP] 카카오(Kakao) 맛집 검색 API: API 키가 설정되지 않았습니다.\n")

    # 4. 네이버(Naver) API 테스트 (블로그 검색)
    # 네이버 블로그 검색 기능이 local_info_service에 없으므로, 관련 함수를 직접 여기에 정의합니다.
    async def _search_naver_blog_test(query: str):
        if not settings.naver_client_id or not settings.naver_client_secret:
            return None
        async with httpx.AsyncClient() as client:
            headers = {
                "X-Naver-Client-Id": settings.naver_client_id,
                "X-Naver-Client-Secret": settings.naver_client_secret,
            }
            params = {"query": query, "display": 5}
            try:
                response = await client.get("https://openapi.naver.com/v1/search/blog.json", headers=headers, params=params)
                response.raise_for_status()
                return response.json().get("items", [])
            except Exception as e:
                print(f"네이버 API 오류: {e}")
                return []

    if settings.naver_client_id and settings.naver_client_secret:
        await run_test("네이버(Naver) 블로그 검색 API", _search_naver_blog_test(TEST_LOCATION_QUERY))
    else:
        print("⚠️ [SKIP] 네이버(Naver) 블로그 검색 API: Client ID 또는 Secret이 설정되지 않았습니다.\n")

    # 5. 공공데이터포털(Tour API) 테스트
    if os.getenv("KOREA_TOURISM_API_KEY"):
        await run_test(
            "공공데이터포털(Tour API)",
            tour_api_service.get_festivals_from_tour_api(
                area_code=TEST_TOUR_AREA_CODE,
                event_start_date=TEST_TOUR_START_DATE
            )
        )
    else:
        print("⚠️ [SKIP] 공공데이터포털(Tour API): KOREA_TOURISM_API_KEY 환경 변수가 설정되지 않았습니다.\n")

    print("=========================================")
    print("          모든 API 테스트 완료           ")
    print("=========================================")


if __name__ == "__main__":
    asyncio.run(main())
