"""
경로 최적화 라우터
여행 일정의 경로를 최적화하는 API 엔드포인트
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user_optional
from app.database import get_db
from app.services.route_optimizer import (
    Location,
    OptimizedRoute,
    RouteOptimizer,
)
from app.utils import create_error_response, create_standard_response

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/route-optimization",
    tags=["route-optimization"],
)


class PlaceInput(BaseModel):
    """장소 입력 모델"""
    id: str
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    type: str = "attraction"
    duration: int = 120  # 분
    priority: float = 1.0


class OptimizeRouteRequest(BaseModel):
    """경로 최적화 요청"""
    places: List[PlaceInput]
    start_location: Optional[Location] = None
    preferences: Optional[dict] = None


class OptimizeMultiDayRequest(BaseModel):
    """여러 날 경로 최적화 요청"""
    places: List[PlaceInput]
    days: int
    accommodation: Optional[Location] = None
    preferences: Optional[dict] = None


@router.post("/optimize-daily", response_model=dict)
async def optimize_daily_route(
    request: OptimizeRouteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    하루 일정의 경로 최적화
    
    장소 목록을 받아 최적의 방문 순서와 경로를 계산합니다.
    """
    try:
        optimizer = RouteOptimizer(db)
        
        # 장소 데이터 변환
        places_data = [place.dict() for place in request.places]
        
        # 경로 최적화 실행
        optimized_route = await optimizer.optimize_daily_route(
            places_data,
            request.start_location,
            request.preferences
        )
        
        if not optimized_route:
            return create_error_response(
                code="OPTIMIZATION_FAILED",
                message="경로 최적화에 실패했습니다."
            )
        
        # 응답 데이터 구성
        response_data = {
            "day": optimized_route.day,
            "places": [
                {
                    "id": p.id,
                    "name": p.name,
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                    "address": p.address,
                    "type": p.place_type,
                    "duration": p.duration,
                    "priority": p.priority
                }
                for p in optimized_route.places
            ],
            "segments": [
                {
                    "from": {
                        "id": s.from_place.id,
                        "name": s.from_place.name,
                        "latitude": s.from_place.latitude,
                        "longitude": s.from_place.longitude
                    },
                    "to": {
                        "id": s.to_place.id,
                        "name": s.to_place.name,
                        "latitude": s.to_place.latitude,
                        "longitude": s.to_place.longitude
                    },
                    "transport_mode": s.transport_mode,
                    "distance": round(s.distance, 2),
                    "duration": s.duration,
                    "departure_time": s.departure_time,
                    "arrival_time": s.arrival_time,
                    "cost": s.cost
                }
                for s in optimized_route.segments
            ],
            "statistics": {
                "total_distance": round(optimized_route.total_distance, 2),
                "total_duration": optimized_route.total_duration,
                "total_cost": optimized_route.total_cost,
                "efficiency_score": round(optimized_route.efficiency_score, 2),
                "places_count": len(optimized_route.places),
                "average_travel_time": round(
                    optimized_route.total_duration / len(optimized_route.segments)
                ) if optimized_route.segments else 0
            }
        }
        
        logger.info(
            f"경로 최적화 완료 - 장소: {len(optimized_route.places)}개, "
            f"총 거리: {optimized_route.total_distance:.1f}km, "
            f"효율성: {optimized_route.efficiency_score:.2f}"
        )
        
        return create_standard_response(
            success=True,
            data=response_data,
            message="경로가 성공적으로 최적화되었습니다."
        )
        
    except Exception as e:
        logger.error(f"경로 최적화 오류: {str(e)}")
        return create_error_response(
            code="OPTIMIZATION_ERROR",
            message="경로 최적화 중 오류가 발생했습니다.",
            details=[{"field": "general", "message": str(e)}]
        )


@router.post("/optimize-multi-day", response_model=dict)
async def optimize_multi_day_route(
    request: OptimizeMultiDayRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    여러 날 여행 일정의 경로 최적화
    
    전체 장소를 일별로 클러스터링하고 각 날의 경로를 최적화합니다.
    """
    try:
        optimizer = RouteOptimizer(db)
        
        # 장소 데이터 변환
        places_data = [place.dict() for place in request.places]
        
        # 여러 날 경로 최적화 실행
        daily_routes = await optimizer.optimize_multi_day_itinerary(
            places_data,
            request.days,
            request.accommodation,
            request.preferences
        )
        
        if not daily_routes:
            return create_error_response(
                code="OPTIMIZATION_FAILED",
                message="여행 일정 최적화에 실패했습니다."
            )
        
        # 응답 데이터 구성
        response_data = {
            "days": request.days,
            "daily_routes": [],
            "summary": {
                "total_places": 0,
                "total_distance": 0,
                "total_duration": 0,
                "average_efficiency": 0
            }
        }
        
        for route in daily_routes:
            day_data = {
                "day": route.day,
                "places": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "latitude": p.latitude,
                        "longitude": p.longitude,
                        "type": p.place_type,
                        "duration": p.duration
                    }
                    for p in route.places
                ],
                "segments": [
                    {
                        "from_name": s.from_place.name,
                        "to_name": s.to_place.name,
                        "transport_mode": s.transport_mode,
                        "distance": round(s.distance, 2),
                        "duration": s.duration,
                        "time": f"{s.departure_time} - {s.arrival_time}"
                    }
                    for s in route.segments
                ],
                "statistics": {
                    "total_distance": round(route.total_distance, 2),
                    "total_duration": route.total_duration,
                    "efficiency_score": round(route.efficiency_score, 2),
                    "places_count": len(route.places)
                }
            }
            response_data["daily_routes"].append(day_data)
            
            # 전체 통계 업데이트
            response_data["summary"]["total_places"] += len(route.places)
            response_data["summary"]["total_distance"] += route.total_distance
            response_data["summary"]["total_duration"] += route.total_duration
            response_data["summary"]["average_efficiency"] += route.efficiency_score
        
        # 평균 효율성 계산
        if daily_routes:
            response_data["summary"]["average_efficiency"] /= len(daily_routes)
            response_data["summary"]["average_efficiency"] = round(
                response_data["summary"]["average_efficiency"], 2
            )
        
        response_data["summary"]["total_distance"] = round(
            response_data["summary"]["total_distance"], 2
        )
        
        logger.info(
            f"여행 일정 최적화 완료 - {request.days}일, "
            f"총 {response_data['summary']['total_places']}개 장소, "
            f"총 거리: {response_data['summary']['total_distance']:.1f}km"
        )
        
        return create_standard_response(
            success=True,
            data=response_data,
            message="여행 일정이 성공적으로 최적화되었습니다."
        )
        
    except Exception as e:
        logger.error(f"여행 일정 최적화 오류: {str(e)}")
        return create_error_response(
            code="OPTIMIZATION_ERROR",
            message="여행 일정 최적화 중 오류가 발생했습니다.",
            details=[{"field": "general", "message": str(e)}]
        )


@router.post("/compare-routes", response_model=dict)
async def compare_routes(
    request: OptimizeRouteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    다양한 옵션으로 경로 비교
    
    원본 순서와 최적화된 순서를 비교하여 개선 효과를 보여줍니다.
    """
    try:
        optimizer = RouteOptimizer(db)
        
        # 장소 데이터 변환
        places_data = [place.dict() for place in request.places]
        
        # 원본 순서로 경로 계산
        original_segments = []
        original_distance = 0
        original_duration = 0
        
        current_location = request.start_location
        for place_data in places_data:
            if current_location:
                # 실제로는 API 호출하여 정확한 거리/시간 계산
                distance = optimizer._haversine_distance(
                    current_location.latitude,
                    current_location.longitude,
                    place_data["latitude"],
                    place_data["longitude"]
                ) * 1.3  # 도로 거리 보정
                duration = int(distance * 60 / 25)  # 평균 25km/h
                
                original_distance += distance
                original_duration += duration
                
            current_location = Location(
                id=place_data["id"],
                name=place_data["name"],
                latitude=place_data["latitude"],
                longitude=place_data["longitude"]
            )
        
        # 최적화된 경로 계산
        optimized_route = await optimizer.optimize_daily_route(
            places_data,
            request.start_location,
            request.preferences
        )
        
        # 개선율 계산
        distance_improvement = (
            (original_distance - optimized_route.total_distance) / original_distance * 100
        ) if original_distance > 0 else 0
        
        time_improvement = (
            (original_duration - optimized_route.total_duration) / original_duration * 100
        ) if original_duration > 0 else 0
        
        response_data = {
            "original": {
                "order": [p.name for p in request.places],
                "total_distance": round(original_distance, 2),
                "total_duration": original_duration
            },
            "optimized": {
                "order": [p.name for p in optimized_route.places],
                "total_distance": round(optimized_route.total_distance, 2),
                "total_duration": optimized_route.total_duration,
                "efficiency_score": round(optimized_route.efficiency_score, 2)
            },
            "improvement": {
                "distance_saved": round(original_distance - optimized_route.total_distance, 2),
                "time_saved": original_duration - optimized_route.total_duration,
                "distance_improvement_percent": round(distance_improvement, 1),
                "time_improvement_percent": round(time_improvement, 1)
            }
        }
        
        logger.info(
            f"경로 비교 완료 - 거리 절감: {distance_improvement:.1f}%, "
            f"시간 절감: {time_improvement:.1f}%"
        )
        
        return create_standard_response(
            success=True,
            data=response_data,
            message="경로 비교가 완료되었습니다."
        )
        
    except Exception as e:
        logger.error(f"경로 비교 오류: {str(e)}")
        return create_error_response(
            code="COMPARISON_ERROR",
            message="경로 비교 중 오류가 발생했습니다.",
            details=[{"field": "general", "message": str(e)}]
        )