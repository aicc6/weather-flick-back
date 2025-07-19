"""
실시간 여행 정보 API 라우터
실시간 정보 조회, 일정 최적화, 알림 등의 기능 제공
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.auth import get_current_user
from app.database import get_db
from app.models import User, TravelPlan
from app.services.realtime_info_service import realtime_info_service
from app.services.travel_plan_optimizer import travel_plan_optimizer
from app.utils import create_standard_response, create_error_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/realtime",
    tags=["realtime-travel"],
    responses={404: {"description": "Not found"}},
)


@router.get("/place/{place_id}")
async def get_place_realtime_info(
    place_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    특정 장소의 실시간 정보 조회
    
    - 영업시간 및 현재 영업 상태
    - 혼잡도 정보
    - 실시간 리뷰 평점
    - 연락처 및 웹사이트
    """
    try:
        realtime_info = await realtime_info_service.get_place_realtime_info(place_id)
        
        return create_standard_response(
            success=True,
            message="실시간 정보를 성공적으로 조회했습니다.",
            data=realtime_info
        )
    except Exception as e:
        logger.error(f"Error getting realtime info: {str(e)}")
        return create_error_response(
            error="REALTIME_INFO_ERROR",
            message="실시간 정보 조회 중 오류가 발생했습니다.",
            details=str(e)
        )


@router.post("/places/batch")
async def get_multiple_places_realtime_info(
    place_ids: List[str],
    current_user: User = Depends(get_current_user)
):
    """
    여러 장소의 실시간 정보 일괄 조회
    """
    try:
        results = {}
        for place_id in place_ids[:10]:  # 최대 10개 제한
            try:
                info = await realtime_info_service.get_place_realtime_info(place_id)
                results[place_id] = info
            except Exception as e:
                results[place_id] = {"error": str(e)}
        
        return create_standard_response(
            success=True,
            message=f"{len(results)}개 장소의 실시간 정보를 조회했습니다.",
            data=results
        )
    except Exception as e:
        logger.error(f"Error getting batch realtime info: {str(e)}")
        return create_error_response(
            error="BATCH_REALTIME_ERROR",
            message="일괄 실시간 정보 조회 중 오류가 발생했습니다.",
            details=str(e)
        )


@router.get("/holidays")
async def get_holidays(
    year: int = Query(..., description="조회할 연도"),
    month: Optional[int] = Query(None, description="조회할 월 (선택적)"),
    current_user: User = Depends(get_current_user)
):
    """
    공휴일 정보 조회
    """
    try:
        holidays = await realtime_info_service.get_holidays(year, month)
        
        return create_standard_response(
            success=True,
            message=f"{year}년{f' {month}월' if month else ''}의 공휴일 정보입니다.",
            data={
                "year": year,
                "month": month,
                "holidays": holidays
            }
        )
    except Exception as e:
        logger.error(f"Error getting holidays: {str(e)}")
        return create_error_response(
            error="HOLIDAY_ERROR",
            message="공휴일 정보 조회 중 오류가 발생했습니다.",
            details=str(e)
        )


@router.post("/optimize/{plan_id}")
async def optimize_travel_plan(
    plan_id: str,
    preferences: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    여행 계획 실시간 최적화
    
    - 영업시간에 따른 일정 재배치
    - 혼잡도 기반 시간 조정
    - 날씨 고려 실내/실외 조정
    - 경로 최적화
    """
    try:
        # 여행 계획 조회
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == plan_id,
            TravelPlan.user_id == current_user.id
        ).first()
        
        if not travel_plan:
            raise HTTPException(status_code=404, detail="여행 계획을 찾을 수 없습니다.")
        
        if not travel_plan.itinerary:
            return create_error_response(
                error="NO_ITINERARY",
                message="최적화할 일정이 없습니다."
            )
        
        # 일정 최적화
        optimization_result = await travel_plan_optimizer.optimize_daily_itinerary(
            itinerary=travel_plan.itinerary,
            date=travel_plan.start_date,
            preferences=preferences or {}
        )
        
        # 최적화된 일정 저장 옵션 (선택적)
        if optimization_result.get('changes'):
            # 변경사항이 있을 때만 업데이트
            pass  # 사용자 확인 후 저장하도록 구현
        
        return create_standard_response(
            success=True,
            message="여행 일정이 최적화되었습니다.",
            data=optimization_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing travel plan: {str(e)}")
        return create_error_response(
            error="OPTIMIZATION_ERROR",
            message="일정 최적화 중 오류가 발생했습니다.",
            details=str(e)
        )


@router.post("/check-conflicts/{plan_id}")
async def check_itinerary_conflicts(
    plan_id: str,
    check_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    여행 일정의 실시간 충돌 검사
    
    - 영업 상태 확인
    - 휴무일 확인
    - 특별 이벤트 충돌
    """
    try:
        # 여행 계획 조회
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == plan_id,
            TravelPlan.user_id == current_user.id
        ).first()
        
        if not travel_plan:
            raise HTTPException(status_code=404, detail="여행 계획을 찾을 수 없습니다.")
        
        if not travel_plan.itinerary:
            return create_standard_response(
                success=True,
                message="검사할 일정이 없습니다.",
                data={"has_conflicts": False, "conflicts": []}
            )
        
        # 충돌 검사
        conflicts = await realtime_info_service.check_itinerary_conflicts(
            itinerary=travel_plan.itinerary,
            check_date=check_date
        )
        
        return create_standard_response(
            success=True,
            message="일정 충돌 검사가 완료되었습니다.",
            data=conflicts
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking conflicts: {str(e)}")
        return create_error_response(
            error="CONFLICT_CHECK_ERROR",
            message="충돌 검사 중 오류가 발생했습니다.",
            details=str(e)
        )


@router.get("/weather-alerts")
async def get_weather_alerts_for_location(
    lat: float = Query(..., description="위도"),
    lon: float = Query(..., description="경도"),
    current_user: User = Depends(get_current_user)
):
    """
    특정 위치의 날씨 특보 및 경고 조회
    """
    try:
        alerts = await realtime_info_service.get_weather_alerts(lat, lon)
        
        return create_standard_response(
            success=True,
            message="날씨 특보 정보를 조회했습니다.",
            data={
                "location": {"lat": lat, "lon": lon},
                "alerts": alerts,
                "checked_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error getting weather alerts: {str(e)}")
        return create_error_response(
            error="WEATHER_ALERT_ERROR",
            message="날씨 특보 조회 중 오류가 발생했습니다.",
            details=str(e)
        )


@router.post("/suggest-alternatives")
async def suggest_alternative_places(
    place: Dict[str, Any],
    issue_type: str = Query(..., description="문제 유형 (closed, crowded, weather)"),
    current_user: User = Depends(get_current_user)
):
    """
    문제가 있는 장소에 대한 대체 장소 제안
    """
    try:
        alternatives = await realtime_info_service.suggest_alternatives(place, issue_type)
        
        return create_standard_response(
            success=True,
            message=f"{len(alternatives)}개의 대체 장소를 찾았습니다.",
            data={
                "original_place": place.get('name'),
                "issue_type": issue_type,
                "alternatives": alternatives
            }
        )
    except Exception as e:
        logger.error(f"Error suggesting alternatives: {str(e)}")
        return create_error_response(
            error="ALTERNATIVE_ERROR",
            message="대체 장소 제안 중 오류가 발생했습니다.",
            details=str(e)
        )


@router.post("/monitor/{plan_id}")
async def monitor_travel_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    여행 계획 실시간 모니터링 및 알림
    
    - 실시간 변경사항 감지
    - 중요 알림 생성
    - 최적화 제안
    """
    try:
        # 여행 계획 조회
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == plan_id,
            TravelPlan.user_id == current_user.id
        ).first()
        
        if not travel_plan:
            raise HTTPException(status_code=404, detail="여행 계획을 찾을 수 없습니다.")
        
        # 사용자 선호도 조회
        user_preferences = current_user.preferences or {}
        
        # 모니터링 수행
        monitoring_result = await travel_plan_optimizer.monitor_and_notify(
            plan_id=str(plan_id),
            itinerary=travel_plan.itinerary or {},
            user_preferences=user_preferences
        )
        
        return create_standard_response(
            success=True,
            message="여행 계획 모니터링이 완료되었습니다.",
            data=monitoring_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error monitoring travel plan: {str(e)}")
        return create_error_response(
            error="MONITORING_ERROR",
            message="모니터링 중 오류가 발생했습니다.",
            details=str(e)
        )


@router.put("/apply-optimization/{plan_id}")
async def apply_optimization_to_plan(
    plan_id: str,
    optimized_itinerary: Dict[str, List[Dict]],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    최적화된 일정을 실제 여행 계획에 적용
    """
    try:
        # 여행 계획 조회
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == plan_id,
            TravelPlan.user_id == current_user.id
        ).first()
        
        if not travel_plan:
            raise HTTPException(status_code=404, detail="여행 계획을 찾을 수 없습니다.")
        
        # 최적화된 일정 적용
        travel_plan.itinerary = optimized_itinerary
        travel_plan.updated_at = datetime.now()
        
        # 최적화 이력 저장 (선택적)
        if hasattr(travel_plan, 'optimization_history'):
            if not travel_plan.optimization_history:
                travel_plan.optimization_history = []
            travel_plan.optimization_history.append({
                'applied_at': datetime.now().isoformat(),
                'changes_count': len(optimized_itinerary)
            })
        
        db.commit()
        db.refresh(travel_plan)
        
        return create_standard_response(
            success=True,
            message="최적화된 일정이 성공적으로 적용되었습니다.",
            data={
                "plan_id": str(travel_plan.plan_id),
                "updated_at": travel_plan.updated_at.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying optimization: {str(e)}")
        db.rollback()
        return create_error_response(
            error="APPLY_OPTIMIZATION_ERROR",
            message="최적화 적용 중 오류가 발생했습니다.",
            details=str(e)
        )