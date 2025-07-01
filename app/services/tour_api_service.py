"""
TourAPI 연동을 위한 서비스 모듈
"""
import httpx
import os
from typing import List, Dict, Any
from urllib.parse import unquote

def get_mock_festivals() -> List[Dict[str, Any]]:
    """
    API 호출 실패 시 사용할 가상의 축제 데이터(목 데이터)를 반환합니다.
    """
    print("Returning mock festival data.")
    # 실제 API가 성공적으로 응답했다고 가정한 가상의 데이터
    mock_response = {
        "response": {
            "header": {"resultCode": "0000", "resultMsg": "OK"},
            "body": {
                "items": {
                    "item": [
                        {
                            "addr1": "경기도 가평군 가평읍 자라섬로 60", "title": "자라섬 꽃 페스타 (가을)",
                            "contentid": "2674251", "eventstartdate": "20240101", "eventenddate": "20241231",
                        },
                        {
                            "addr1": "경기도 용인시 처인구 포곡읍 에버랜드로 199", "title": "에버랜드 장미축제",
                             "contentid": "1114945", "eventstartdate": "20240830", "eventenddate": "20241117",
                        }
                    ]
                }, "totalCount": 2
            }
        }
    }
    return mock_response.get("response", {}).get("body", {}).get("items", {}).get("item", [])


async def get_festivals_from_tour_api(area_code: str, event_start_date: str) -> List[Dict[str, Any]]:
    """
    (비동기) 지정된 지역 코드와 시작일 기준으로 축제 정보를 가져옵니다.
    먼저 실제 TourAPI 호출을 시도하고, 모든 종류의 예외 발생 시 목 데이터를 안전하게 반환합니다.
    """
    service_key_encoded = os.getenv("TOUR_API_KEY")
    if not service_key_encoded:
        print("--- 경고: TourAPI 인증키가 없습니다. 목 데이터를 사용합니다. ---")
        return get_mock_festivals()

    try:
        service_key_decoded = unquote(service_key_encoded)
        base_url = "https://apis.data.go.kr/B551011/KorService1/searchFestival1"
        params = {
            "serviceKey": service_key_decoded,
            "MobileOS": "ETC",
            "MobileApp": "WeatherFlick",
            "_type": "json",
            "listYN": "Y",
            "arrange": "A",
            "areaCode": area_code,
            "eventStartDate": event_start_date
        }

        async with httpx.AsyncClient() as client:
            print(f"Requesting REAL festival data from TourAPI for areaCode: {area_code}")
            response = await client.get(base_url, params=params, timeout=15.0)
            response.raise_for_status()

        data = response.json()
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        if not items:
            print("TourAPI에서 해당 조건의 축제 정보를 찾지 못했습니다.")

        return items

    except Exception as e:
        print(f"--- TourAPI 호출 오류 발생: {e} ---")
        print("--- API 호출에 실패하여 목(mock) 데이터를 대신 반환합니다. ---")
        return get_mock_festivals()
