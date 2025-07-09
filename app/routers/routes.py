"""
경로 정보 API 라우터
여행 계획의 경로 정보 관리 및 교통 정보 제공
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import uuid

from app.database import get_db
from app.models import (
    TravelRoute, TransportationDetail, TravelPlan,
    TravelRouteCreate, TravelRouteUpdate, TravelRouteResponse,
    TransportationDetailCreate, TransportationDetailResponse,
    RouteCalculationRequest, RouteCalculationResponse,
    User
)
from app.auth import get_current_user
from app.services.route_service import route_service
from app.services.google_places_service import google_places_service

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/calculate", response_model=RouteCalculationResponse)
async def calculate_route(
    request: RouteCalculationRequest,
    current_user: User = Depends(get_current_user)
):
    """경로 계산 API"""
    try:
        result = await route_service.calculate_route(
            request.departure_lat,
            request.departure_lng,
            request.destination_lat,
            request.destination_lng,
            request.transport_type
        )
        
        return RouteCalculationResponse(
            success=result.get("success", False),
            duration=result.get("duration"),
            distance=result.get("distance"),
            cost=result.get("cost"),
            route_data=result.get("route_data"),
            transport_type=result.get("transport_type", request.transport_type),
            message=result.get("message")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"경로 계산 중 오류 발생: {str(e)}"
        )


@router.post("/calculate/multiple")
async def calculate_multiple_routes(
    request: RouteCalculationRequest,
    current_user: User = Depends(get_current_user)
):
    """여러 교통수단 경로 동시 계산"""
    try:
        result = await route_service.get_multiple_routes(
            request.departure_lat,
            request.departure_lng,
            request.destination_lat,
            request.destination_lng
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"다중 경로 계산 중 오류 발생: {str(e)}"
        )


@router.post("/recommend")
async def get_recommended_route(
    request: RouteCalculationRequest,
    preferences: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user)
):
    """상황에 맞는 최적 경로 추천"""
    try:
        result = await route_service.get_recommended_route(
            request.departure_lat,
            request.departure_lng,
            request.destination_lat,
            request.destination_lng,
            preferences
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"추천 경로 계산 중 오류 발생: {str(e)}"
        )


@router.post("/", response_model=TravelRouteResponse)
async def create_travel_route(
    route_data: TravelRouteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """여행 경로 생성"""
    try:
        # 여행 계획 소유권 확인
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route_data.plan_id,
            TravelPlan.user_id == current_user.user_id
        ).first()
        
        if not travel_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="여행 계획을 찾을 수 없거나 접근 권한이 없습니다."
            )
        
        # 새 경로 생성
        new_route = TravelRoute(
            route_id=uuid.uuid4(),
            **route_data.dict()
        )
        
        db.add(new_route)
        db.commit()
        db.refresh(new_route)
        
        return new_route
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"경로 생성 중 오류 발생: {str(e)}"
        )


@router.get("/plan/{plan_id}", response_model=List[TravelRouteResponse])
async def get_travel_plan_routes(
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """특정 여행 계획의 모든 경로 조회"""
    try:
        # 여행 계획 소유권 확인
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == plan_id,
            TravelPlan.user_id == current_user.user_id
        ).first()
        
        if not travel_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="여행 계획을 찾을 수 없거나 접근 권한이 없습니다."
            )
        
        # 경로 조회 (일차 및 순서별 정렬)
        routes = db.query(TravelRoute).filter(
            TravelRoute.plan_id == plan_id
        ).order_by(TravelRoute.day, TravelRoute.sequence).all()
        
        return routes
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"경로 조회 중 오류 발생: {str(e)}"
        )


@router.get("/{route_id}", response_model=TravelRouteResponse)
async def get_travel_route(
    route_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """특정 경로 상세 조회"""
    try:
        route = db.query(TravelRoute).filter(
            TravelRoute.route_id == route_id
        ).first()
        
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="경로를 찾을 수 없습니다."
            )
        
        # 소유권 확인
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route.plan_id,
            TravelPlan.user_id == current_user.user_id
        ).first()
        
        if not travel_plan:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 경로에 접근할 권한이 없습니다."
            )
        
        return route
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"경로 조회 중 오류 발생: {str(e)}"
        )


@router.put("/{route_id}", response_model=TravelRouteResponse)
async def update_travel_route(
    route_id: uuid.UUID,
    route_data: TravelRouteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """여행 경로 수정"""
    try:
        route = db.query(TravelRoute).filter(
            TravelRoute.route_id == route_id
        ).first()
        
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="경로를 찾을 수 없습니다."
            )
        
        # 소유권 확인
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route.plan_id,
            TravelPlan.user_id == current_user.user_id
        ).first()
        
        if not travel_plan:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 경로를 수정할 권한이 없습니다."
            )
        
        # 경로 정보 업데이트
        update_data = route_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(route, field, value)
        
        db.commit()
        db.refresh(route)
        
        return route
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"경로 수정 중 오류 발생: {str(e)}"
        )


@router.delete("/{route_id}")
async def delete_travel_route(
    route_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """여행 경로 삭제"""
    try:
        route = db.query(TravelRoute).filter(
            TravelRoute.route_id == route_id
        ).first()
        
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="경로를 찾을 수 없습니다."
            )
        
        # 소유권 확인
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route.plan_id,
            TravelPlan.user_id == current_user.user_id
        ).first()
        
        if not travel_plan:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 경로를 삭제할 권한이 없습니다."
            )
        
        # 관련된 교통수단 상세 정보도 함께 삭제
        db.query(TransportationDetail).filter(
            TransportationDetail.route_id == route_id
        ).delete()
        
        # 경로 삭제
        db.delete(route)
        db.commit()
        
        return {"message": "경로가 성공적으로 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"경로 삭제 중 오류 발생: {str(e)}"
        )


@router.post("/plan/{plan_id}/auto-generate")
async def auto_generate_routes(
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """여행 계획의 일정을 기반으로 자동 경로 생성"""
    try:
        # 여행 계획 조회 및 소유권 확인
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == plan_id,
            TravelPlan.user_id == current_user.user_id
        ).first()
        
        if not travel_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="여행 계획을 찾을 수 없거나 접근 권한이 없습니다."
            )
        
        if not travel_plan.itinerary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="여행 일정이 없어 경로를 생성할 수 없습니다."
            )
        
        # 기존 경로들을 먼저 삭제 (중복 방지)
        existing_routes = db.query(TravelRoute).filter(
            TravelRoute.plan_id == plan_id
        ).all()
        
        if existing_routes:
            # 관련된 교통수단 상세 정보도 함께 삭제
            for route in existing_routes:
                db.query(TransportationDetail).filter(
                    TransportationDetail.route_id == route.route_id
                ).delete()
            
            # 기존 경로 삭제
            db.query(TravelRoute).filter(
                TravelRoute.plan_id == plan_id
            ).delete()
            
            db.commit()
        
        generated_routes = []
        
        # 먼저 모든 Place ID를 수집
        all_place_ids = set()
        for day_str, places in travel_plan.itinerary.items():
            for place in places:
                if place.get('place_id'):
                    all_place_ids.add(place['place_id'])
        
        # Google Places API로 좌표 정보 일괄 조회
        place_details = {}
        if all_place_ids:
            place_details = await google_places_service.get_multiple_place_details(list(all_place_ids))
        
        # 각 일차별로 경로 생성
        for day_str, places in travel_plan.itinerary.items():
            if not places or len(places) < 2:
                continue
                
            try:
                day = int(day_str.replace('Day ', '').replace('day', ''))
            except:
                continue
            
            # 연속된 장소 간 경로 생성
            for i in range(len(places) - 1):
                current_place = places[i]
                next_place = places[i + 1]
                
                # 좌표 정보 확인 및 가져오기
                current_coords = None
                next_coords = None
                
                # 기존 좌표 정보가 있으면 사용
                if current_place.get('latitude') and current_place.get('longitude'):
                    current_coords = {
                        'latitude': current_place['latitude'],
                        'longitude': current_place['longitude'],
                        'name': current_place.get('name', current_place.get('description', '출발지'))
                    }
                # Place ID로 좌표 조회
                elif current_place.get('place_id') and current_place['place_id'] in place_details:
                    detail = place_details[current_place['place_id']]
                    if detail.get('latitude') and detail.get('longitude'):
                        current_coords = {
                            'latitude': detail['latitude'],
                            'longitude': detail['longitude'],
                            'name': detail.get('name', current_place.get('description', '출발지'))
                        }
                
                # 다음 장소 좌표 확인
                if next_place.get('latitude') and next_place.get('longitude'):
                    next_coords = {
                        'latitude': next_place['latitude'],
                        'longitude': next_place['longitude'],
                        'name': next_place.get('name', next_place.get('description', '도착지'))
                    }
                elif next_place.get('place_id') and next_place['place_id'] in place_details:
                    detail = place_details[next_place['place_id']]
                    if detail.get('latitude') and detail.get('longitude'):
                        next_coords = {
                            'latitude': detail['latitude'],
                            'longitude': detail['longitude'],
                            'name': detail.get('name', next_place.get('description', '도착지'))
                        }
                
                # 두 장소 모두 좌표가 있는 경우만 경로 생성
                if current_coords and next_coords:
                    try:
                        # 최적 경로 계산
                        route_result = await route_service.get_recommended_route(
                            current_coords['latitude'],
                            current_coords['longitude'],
                            next_coords['latitude'],
                            next_coords['longitude']
                        )
                        
                        if route_result.get('success') and route_result.get('recommended'):
                            recommended = route_result['recommended']
                            
                            # 경로 정보 저장
                            new_route = TravelRoute(
                                route_id=uuid.uuid4(),
                                plan_id=plan_id,
                                day=day,
                                sequence=i + 1,
                                departure_name=current_coords['name'],
                                departure_lat=current_coords['latitude'],
                                departure_lng=current_coords['longitude'],
                                destination_name=next_coords['name'],
                                destination_lat=next_coords['latitude'],
                                destination_lng=next_coords['longitude'],
                                transport_type=recommended.get('transport_type'),
                                route_data=recommended.get('route_data'),
                                duration=recommended.get('duration'),
                                distance=recommended.get('distance'),
                                cost=recommended.get('cost')
                            )
                            
                            db.add(new_route)
                            generated_routes.append(new_route)
                            
                    except Exception as route_error:
                        print(f"경로 계산 중 오류: {str(route_error)}")
                        continue
        
        if generated_routes:
            db.commit()
            
            # 생성된 경로들을 새로고침
            for route in generated_routes:
                db.refresh(route)
        
        return {
            "message": f"{len(generated_routes)}개의 경로가 자동 생성되었습니다.",
            "routes": generated_routes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"자동 경로 생성 중 오류 발생: {str(e)}"
        )


# 교통수단 상세 정보 관련 API
@router.post("/transportation", response_model=TransportationDetailResponse)
async def create_transportation_detail(
    detail_data: TransportationDetailCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """교통수단 상세 정보 생성"""
    try:
        # 경로 존재 확인 및 소유권 검증
        route = db.query(TravelRoute).filter(
            TravelRoute.route_id == detail_data.route_id
        ).first()
        
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="경로를 찾을 수 없습니다."
            )
        
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route.plan_id,
            TravelPlan.user_id == current_user.user_id
        ).first()
        
        if not travel_plan:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 경로에 접근할 권한이 없습니다."
            )
        
        # 교통수단 상세 정보 생성
        new_detail = TransportationDetail(
            detail_id=uuid.uuid4(),
            **detail_data.dict()
        )
        
        db.add(new_detail)
        db.commit()
        db.refresh(new_detail)
        
        return new_detail
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"교통수단 상세 정보 생성 중 오류 발생: {str(e)}"
        )


@router.get("/{route_id}/transportation", response_model=List[TransportationDetailResponse])
async def get_transportation_details(
    route_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """특정 경로의 교통수단 상세 정보 조회"""
    try:
        # 경로 존재 확인 및 소유권 검증
        route = db.query(TravelRoute).filter(
            TravelRoute.route_id == route_id
        ).first()
        
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="경로를 찾을 수 없습니다."
            )
        
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route.plan_id,
            TravelPlan.user_id == current_user.user_id
        ).first()
        
        if not travel_plan:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 경로에 접근할 권한이 없습니다."
            )
        
        # 교통수단 상세 정보 조회
        details = db.query(TransportationDetail).filter(
            TransportationDetail.route_id == route_id
        ).all()
        
        return details
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"교통수단 상세 정보 조회 중 오류 발생: {str(e)}"
        )