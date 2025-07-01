from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from datetime import datetime

from app.services.tour_api_service import get_festivals_from_tour_api

router = APIRouter(
    prefix="/events",
    tags=["events"],
)

@router.get("/{area_code}", response_model=List[Dict[str, Any]])
async def get_events_by_area(
    area_code: str = Query(..., description="TourAPI 지역 코드 (예: 1=서울, 31=경기도)"),
):
    """
    특정 지역의 현재 진행중인 축제/이벤트 목록을 조회합니다.
    - `eventStartDate`는 현재 날짜를 기준으로 자동 설정됩니다.
    - 현재는 SSL 이슈로 인해 실제 API를 호출하는 대신 목(mock) 데이터를 반환합니다.
    """
    try:
        # 항상 현재 날짜를 기준으로 진행중인 이벤트를 검색
        today_str = datetime.now().strftime('%Y%m%d')
        festivals = await get_festivals_from_tour_api(area_code=area_code, event_start_date=today_str)
        return festivals
    except Exception as e:
        # 실제 구현에서는 더 상세한 오류 처리가 필요합니다.
        raise HTTPException(status_code=500, detail=f"이벤트 정보를 가져오는 중 오류 발생: {str(e)}")
