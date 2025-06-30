from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json
import math

from app.database import get_db
from app.models import (
    Destination, DestinationResponse, RecommendationRequest, RecommendationResponse,
    User, StandardResponse
)
from app.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/recommendations",
    tags=["recommendations"],
    responses={404: {"description": "Not found"}},
)

def create_standard_response(success: bool, data=None, error=None, pagination=None):
    """표준 응답 형식 생성"""
    return {
        "success": success,
        "data": data,
        "error": error,
        "pagination": pagination,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

def convert_uuids_to_strings(obj):
    """UUID 객체를 문자열로 변환하는 헬퍼 함수"""
    if hasattr(obj, 'dict'):
        data = obj.dict()
    else:
        data = obj
    
    if isinstance(data, dict):
        for key, value in data.items():
            if hasattr(value, 'hex'):  # UUID 객체인 경우
                data[key] = str(value)
    elif isinstance(data, list):
        for item in data:
            convert_uuids_to_strings(item)
    
    return data

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 지점 간의 거리 계산 (km)"""
    R = 6371  # 지구 반지름 (km)
    
    # 위도/경도를 라디안으로 변환
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # 위도/경도 차이
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine 공식
    a = (math.sin(dlat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance = R * c
    return distance

def calculate_recommendation_score(destination, weather_data, user_preferences, origin) -> float:
    """여행지 추천 점수 계산"""
    base_score = destination.popularity_score or 0
    recommendation_weight = destination.recommendation_weight or 1.0
    
    # 기본 점수 (인기도)
    score = base_score * 0.3
    
    # 추천 가중치 적용
    score *= recommendation_weight
    
    # 거리 점수 (가까울수록 높은 점수)
    if destination.latitude and destination.longitude and origin:
        distance = calculate_distance(
            origin.get('latitude', 0),
            origin.get('longitude', 0),
            destination.latitude,
            destination.longitude
        )
        # 100km 이내는 만점, 그 이후는 거리에 반비례
        distance_score = max(0, 1 - (distance / 500)) * 0.2
        score += distance_score
    
    # 날씨 점수 (추후 구체적인 날씨 매칭 로직 추가)
    weather_score = 0.3  # 기본값
    score += weather_score
    
    # 사용자 선호도 점수 (추후 구체적인 매칭 로직 추가)
    preference_score = 0.2  # 기본값
    score += preference_score
    
    return min(max(score, 0), 1)  # 0-1 사이로 정규화

@router.post("/destinations", response_model=dict)
async def get_destination_recommendations(
    request: RecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """날씨 기반 여행지 추천"""
    try:
        # 기본 쿼리 - 활성 상태인 여행지만
        query = db.query(Destination).filter(Destination.status == "active")
        
        # 거리 필터링 (origin 정보가 있는 경우)
        destinations = query.all()
        
        if request.origin and request.max_distance:
            origin_lat = request.origin.get('latitude')
            origin_lon = request.origin.get('longitude')
            
            if origin_lat and origin_lon:
                filtered_destinations = []
                for dest in destinations:
                    if dest.latitude and dest.longitude:
                        distance = calculate_distance(
                            origin_lat, origin_lon,
                            dest.latitude, dest.longitude
                        )
                        if distance <= request.max_distance:
                            filtered_destinations.append(dest)
                destinations = filtered_destinations
        
        # 추천 점수 계산 및 정렬
        scored_destinations = []
        for dest in destinations:
            score = calculate_recommendation_score(
                dest, None, request.preferences, request.origin
            )
            scored_destinations.append((dest, score))
        
        # 점수 기준으로 정렬
        scored_destinations.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 20개만 선택
        top_destinations = [dest for dest, score in scored_destinations[:20]]
        
        # 응답 데이터 구성
        destination_responses = []
        for dest in top_destinations:
            dest_response = convert_uuids_to_strings(DestinationResponse.from_orm(dest))
            destination_responses.append(dest_response)
        
        # 날씨 예보 정보 (추후 실제 날씨 API 연동)
        weather_forecast = {
            "dates": request.travel_dates,
            "summary": "예측된 날씨 정보가 여기에 포함됩니다."
        }
        
        response_data = {
            "destinations": destination_responses,
            "weather_forecast": weather_forecast,
            "total_results": len(destination_responses),
            "recommendation_score": scored_destinations[0][1] if scored_destinations else 0
        }
        
        return create_standard_response(
            success=True,
            data=response_data
        )
        
    except Exception as e:
        return create_standard_response(
            success=False,
            error={
                "code": "RECOMMENDATION_ERROR",
                "message": "여행지 추천에 실패했습니다.",
                "details": [{"field": "general", "message": str(e)}]
            }
        )

@router.get("/destinations", response_model=dict)
async def get_destinations(
    region: Optional[str] = None,
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """여행지 목록 조회 (필터링 가능)"""
    try:
        # 기본 쿼리
        query = db.query(Destination).filter(Destination.status == "active")
        
        # 지역 필터
        if region:
            query = query.filter(Destination.region.ilike(f"%{region}%"))
        
        # 카테고리 필터
        if category:
            query = query.filter(Destination.category == category)
        
        # 총 개수 조회
        total = query.count()
        
        # 페이지네이션 적용
        offset = (page - 1) * limit
        destinations = query.order_by(Destination.popularity_score.desc()).offset(offset).limit(limit).all()
        
        # 응답 데이터 구성
        response_data = [convert_uuids_to_strings(DestinationResponse.from_orm(dest)) for dest in destinations]
        
        # 페이지네이션 정보
        pagination = {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
        
        return create_standard_response(
            success=True,
            data=response_data,
            pagination=pagination
        )
        
    except Exception as e:
        return create_standard_response(
            success=False,
            error={
                "code": "QUERY_ERROR",
                "message": "여행지 조회에 실패했습니다.",
                "details": [{"field": "general", "message": str(e)}]
            }
        )

@router.get("/destinations/{destination_id}", response_model=dict)
async def get_destination_detail(
    destination_id: str,
    db: Session = Depends(get_db)
):
    """특정 여행지 상세 정보 조회"""
    try:
        destination = db.query(Destination).filter(
            Destination.id == destination_id,
            Destination.status == "active"
        ).first()
        
        if not destination:
            return create_standard_response(
                success=False,
                error={
                    "code": "NOT_FOUND",
                    "message": "여행지를 찾을 수 없습니다."
                }
            )
        
        response_data = convert_uuids_to_strings(DestinationResponse.from_orm(destination))
        
        return create_standard_response(
            success=True,
            data=response_data
        )
        
    except Exception as e:
        return create_standard_response(
            success=False,
            error={
                "code": "QUERY_ERROR",
                "message": "여행지 조회에 실패했습니다.",
                "details": [{"field": "general", "message": str(e)}]
            }
        )

@router.get("/popular", response_model=dict)
async def get_popular_destinations(
    limit: int = Query(10, ge=1, le=50),
    region: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """인기 여행지 조회"""
    try:
        # 기본 쿼리
        query = db.query(Destination).filter(Destination.status == "active")
        
        # 지역 필터
        if region:
            query = query.filter(Destination.region.ilike(f"%{region}%"))
        
        # 인기도 순으로 정렬
        destinations = query.order_by(Destination.popularity_score.desc()).limit(limit).all()
        
        # 응답 데이터 구성
        response_data = [convert_uuids_to_strings(DestinationResponse.from_orm(dest)) for dest in destinations]
        
        return create_standard_response(
            success=True,
            data=response_data
        )
        
    except Exception as e:
        return create_standard_response(
            success=False,
            error={
                "code": "QUERY_ERROR",
                "message": "인기 여행지 조회에 실패했습니다.",
                "details": [{"field": "general", "message": str(e)}]
            }
        )