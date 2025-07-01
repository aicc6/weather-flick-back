"""
TourAPI 연동을 위한 서비스 모듈
"""
import httpx
from typing import List, Dict, Any

# SSL 오류로 인한 테스트 제약으로, 실제 API 호출 대신 목(mock) 데이터를 반환합니다.
# 이 함수는 TourAPI의 'searchFestival1' API 응답과 동일한 구조를 가집니다.
async def get_festivals_from_tour_api(area_code: str, event_start_date: str) -> List[Dict[str, Any]]:
    """
    지정된 지역 코드와 시작일 기준으로 축제 정보를 가져옵니다. (목 데이터 사용)
    """
    print(f"Fetching mock festival data for areaCode: {area_code}, eventStartDate: {event_start_date}")

    # 실제 API가 성공적으로 응답했다고 가정한 가상의 데이터
    mock_response = {
        "response": {
            "header": {"resultCode": "0000", "resultMsg": "OK"},
            "body": {
                "items": {
                    "item": [
                        {
                            "addr1": "경기도 가평군 가평읍 자라섬로 60",
                            "addr2": "",
                            "booktour": "",
                            "cat1": "A02",
                            "cat2": "A0207",
                            "cat3": "A02070100",
                            "contentid": "2674251",
                            "contenttypeid": "15",
                            "createdtime": "20200831100253",
                            "eventenddate": "20241231",
                            "eventstartdate": "20240101",
                            "firstimage": "http://tong.visitkorea.or.kr/cms/resource/58/2674658_image2_1.jpg",
                            "firstimage2": "http://tong.visitkorea.or.kr/cms/resource/58/2674658_image3_1.jpg",
                            "cpyrhtDivCd": "Type3",
                            "mapx": "127.5098188101",
                            "mapy": "37.8189694268",
                            "mlevel": "6",
                            "modifiedtime": "20240523110101",
                            "areacode": "31",
                            "sigungucode": "1",
                            "tel": "031-580-2700",
                            "title": "자라섬 꽃 페스타 (가을)"
                        },
                        {
                            "addr1": "경기도 용인시 처인구 포곡읍 에버랜드로 199",
                            "addr2": "",
                            "booktour": "",
                            "cat1": "A02",
                            "cat2": "A0207",
                            "cat3": "A02070200",
                            "contentid": "1114945",
                            "contenttypeid": "15",
                            "createdtime": "20101130145226",
                            "eventenddate": "20241117",
                            "eventstartdate": "20240830",
                            "firstimage": "http://tong.visitkorea.or.kr/cms/resource/69/3103469_image2_1.jpg",
                            "firstimage2": "http://tong.visitkorea.or.kr/cms/resource/69/3103469_image3_1.jpg",
                            "cpyrhtDivCd": "Type3",
                            "mapx": "127.2037701449",
                            "mapy": "37.2952458971",
                            "mlevel": "6",
                            "modifiedtime": "20240523110101",
                            "areacode": "31",
                            "sigungucode": "19",
                            "tel": "031-320-5000",
                            "title": "에버랜드 장미축제"
                        }
                    ]
                },
                "numOfRows": 10,
                "pageNo": 1,
                "totalCount": 2
            }
        }
    }

    items = mock_response.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    return items
