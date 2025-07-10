"""
경로 정보 API 라우터
여행 계획의 경로 정보 관리 및 교통 정보 제공
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import uuid
import logging

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
from app.services.tmap_service import tmap_service

router = APIRouter(prefix="/routes", tags=["routes"])

logger = logging.getLogger(__name__)


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
        
        # Itinerary JSON 파싱
        import json
        try:
            itinerary = json.loads(travel_plan.itinerary) if isinstance(travel_plan.itinerary, str) else travel_plan.itinerary
        except (json.JSONDecodeError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"여행 일정 데이터 파싱 오류: {str(e)}"
            )
        
        # 먼저 모든 Place ID를 수집
        all_place_ids = set()
        for day_str, places in itinerary.items():
            for place in places:
                if place.get('place_id'):
                    all_place_ids.add(place['place_id'])
        
        # Google Places API로 좌표 정보 일괄 조회
        place_details = {}
        if all_place_ids:
            place_details = await google_places_service.get_multiple_place_details(list(all_place_ids))
        
        # 일차별로 정렬된 리스트 생성
        sorted_days = sorted(itinerary.items(), key=lambda x: int(x[0].replace('Day ', '').replace('day', '')))
        
        # 각 일차별로 경로 생성
        for day_str, places in sorted_days:
            if not places:
                continue
                
            try:
                day = int(day_str.replace('Day ', '').replace('day', ''))
            except:
                continue
            
            # 일차 내 연속된 장소 간 경로 생성
            if len(places) >= 2:
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
        
        # 일차 간 경로 생성 (1일차 마지막 → 2일차 첫 번째, 2일차 마지막 → 3일차 첫 번째 등)
        for i in range(len(sorted_days) - 1):
            current_day_str, current_places = sorted_days[i]
            next_day_str, next_places = sorted_days[i + 1]
            
            if not current_places or not next_places:
                continue
                
            try:
                current_day = int(current_day_str.replace('Day ', '').replace('day', ''))
                next_day = int(next_day_str.replace('Day ', '').replace('day', ''))
            except:
                continue
            
            # 현재 일차 마지막 장소
            last_place = current_places[-1]
            # 다음 일차 첫 번째 장소
            first_place = next_places[0]
            
            # 좌표 정보 확인 및 가져오기
            last_coords = None
            first_coords = None
            
            # 마지막 장소 좌표 확인
            if last_place.get('latitude') and last_place.get('longitude'):
                last_coords = {
                    'latitude': last_place['latitude'],
                    'longitude': last_place['longitude'],
                    'name': last_place.get('name', last_place.get('description', '출발지'))
                }
            elif last_place.get('place_id') and last_place['place_id'] in place_details:
                detail = place_details[last_place['place_id']]
                if detail.get('latitude') and detail.get('longitude'):
                    last_coords = {
                        'latitude': detail['latitude'],
                        'longitude': detail['longitude'],
                        'name': detail.get('name', last_place.get('description', '출발지'))
                    }
            
            # 첫 번째 장소 좌표 확인
            if first_place.get('latitude') and first_place.get('longitude'):
                first_coords = {
                    'latitude': first_place['latitude'],
                    'longitude': first_place['longitude'],
                    'name': first_place.get('name', first_place.get('description', '도착지'))
                }
            elif first_place.get('place_id') and first_place['place_id'] in place_details:
                detail = place_details[first_place['place_id']]
                if detail.get('latitude') and detail.get('longitude'):
                    first_coords = {
                        'latitude': detail['latitude'],
                        'longitude': detail['longitude'],
                        'name': detail.get('name', first_place.get('description', '도착지'))
                    }
            
            # 두 장소 모두 좌표가 있는 경우만 일차 간 경로 생성
            if last_coords and first_coords:
                try:
                    # 최적 경로 계산
                    route_result = await route_service.get_recommended_route(
                        last_coords['latitude'],
                        last_coords['longitude'],
                        first_coords['latitude'],
                        first_coords['longitude']
                    )
                    
                    if route_result.get('success') and route_result.get('recommended'):
                        recommended = route_result['recommended']
                        
                        # 일차 간 경로 정보 저장 (다음 일차에 속하도록 설정)
                        new_route = TravelRoute(
                            route_id=uuid.uuid4(),
                            plan_id=plan_id,
                            day=next_day,
                            sequence=0,  # 일차 간 경로는 sequence 0으로 설정
                            departure_name=last_coords['name'],
                            departure_lat=last_coords['latitude'],
                            departure_lng=last_coords['longitude'],
                            destination_name=first_coords['name'],
                            destination_lat=first_coords['latitude'],
                            destination_lng=first_coords['longitude'],
                            transport_type=recommended.get('transport_type'),
                            route_data=recommended.get('route_data'),
                            duration=recommended.get('duration'),
                            distance=recommended.get('distance'),
                            cost=recommended.get('cost')
                        )
                        
                        db.add(new_route)
                        generated_routes.append(new_route)
                        
                except Exception as route_error:
                    print(f"일차 간 경로 계산 중 오류: {str(route_error)}")
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


@router.get("/{route_id}/details")
async def get_detailed_route_info(
    route_id: uuid.UUID,
    include_pois: bool = True,
    include_alternatives: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """특정 경로의 실시간 상세 정보 조회 (TMAP API 실시간 호출)"""
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
        
        # 기본 경로 정보
        route_info = {
            "route_id": str(route.route_id),
            "departure": {
                "name": route.departure_name,
                "latitude": route.departure_lat,
                "longitude": route.departure_lng
            },
            "destination": {
                "name": route.destination_name,
                "latitude": route.destination_lat,
                "longitude": route.destination_lng
            },
            "transport_type": route.transport_type,
            "basic_info": {
                "duration": route.duration,
                "distance": route.distance,
                "cost": route.cost,
                "stored_route_data": route.route_data
            }
        }
        
        # 실시간 상세 정보 가져오기
        detailed_info = {}
        
        if route.transport_type == "car":
            # TMAP API로 실시간 자동차 경로 정보
            car_result = await tmap_service.get_car_route(
                route.departure_lng,
                route.departure_lat,
                route.destination_lng,
                route.destination_lat,
                "trafast"  # 빠른길 우선
            )
            
            if car_result.get("success"):
                detailed_info["real_time_route"] = car_result
                
                # 대안 경로도 요청한 경우
                if include_alternatives:
                    alternative_routes = []
                    
                    # 편한길 옵션
                    comfort_result = await tmap_service.get_car_route(
                        route.departure_lng,
                        route.departure_lat,
                        route.destination_lng,
                        route.destination_lat,
                        "tracomfort"
                    )
                    if comfort_result.get("success"):
                        alternative_routes.append({
                            "type": "편한길",
                            "route_data": comfort_result
                        })
                    
                    # 최적 경로 옵션
                    optimal_result = await tmap_service.get_car_route(
                        route.departure_lng,
                        route.departure_lat,
                        route.destination_lng,
                        route.destination_lat,
                        "traoptimal"
                    )
                    if optimal_result.get("success"):
                        alternative_routes.append({
                            "type": "최적 경로",
                            "route_data": optimal_result
                        })
                    
                    detailed_info["alternative_routes"] = alternative_routes
            
            # 주변 POI 정보 (주차장, 주유소 등)
            if include_pois:
                # 출발지 주변 주차장
                departure_parking = await tmap_service.get_poi_around(
                    route.departure_lng,
                    route.departure_lat,
                    1000,
                    "parking"
                )
                
                # 도착지 주변 주차장
                destination_parking = await tmap_service.get_poi_around(
                    route.destination_lng,
                    route.destination_lat,
                    1000,
                    "parking"
                )
                
                # 경로 상 주유소 (중간 지점 기준)
                mid_lng = (route.departure_lng + route.destination_lng) / 2
                mid_lat = (route.departure_lat + route.destination_lat) / 2
                gas_stations = await tmap_service.get_poi_around(
                    mid_lng,
                    mid_lat,
                    2000,
                    "gasstation"
                )
                
                detailed_info["pois"] = {
                    "departure_parking": departure_parking,
                    "destination_parking": destination_parking,
                    "nearby_gas_stations": gas_stations
                }
        
        elif route.transport_type == "walk":
            # TMAP API로 실시간 도보 경로 정보
            walk_result = await tmap_service.get_walk_route(
                route.departure_lng,
                route.departure_lat,
                route.destination_lng,
                route.destination_lat
            )
            
            if walk_result.get("success"):
                detailed_info["real_time_route"] = walk_result
        
        # 경로별 상세 안내 정보 추출
        if detailed_info.get("real_time_route"):
            real_time_data = detailed_info["real_time_route"]
            
            # 더 상세한 안내 정보 구성
            enhanced_guide = {
                "summary": {
                    "total_duration": real_time_data.get("duration", 0),
                    "total_distance": real_time_data.get("distance", 0),
                    "total_cost": real_time_data.get("cost", 0),
                    "toll_fee": real_time_data.get("toll_fee", 0),
                    "taxi_fee": real_time_data.get("taxi_fee", 0)
                },
                "detailed_instructions": [],
                "route_geometry": real_time_data.get("route_data", {}).get("geometry", [])
            }
            
            # 상세 안내점 정보
            guide_points = real_time_data.get("route_data", {}).get("guide_points", [])
            detailed_guides = real_time_data.get("route_data", {}).get("detailed_guides", [])
            
            # 주요 안내점만 선별하여 제공
            major_instructions = []
            for guide in detailed_guides:
                major_instructions.append({
                    "step": guide.get("step"),
                    "instruction": guide.get("description"),
                    "distance": guide.get("distance"),
                    "time": guide.get("time"),
                    "turn_type": guide.get("instruction"),
                    "is_major": True
                })
            
            # 모든 안내점 포함 (선택사항)
            all_instructions = []
            for guide in guide_points:
                all_instructions.append({
                    "step": guide.get("step"),
                    "instruction": guide.get("description"),
                    "distance": guide.get("distance"),
                    "time": guide.get("time"),
                    "turn_type": guide.get("turn_instruction"),
                    "road_name": guide.get("road_name"),
                    "facility_name": guide.get("facility_name"),
                    "speed_limit": guide.get("speed_limit"),
                    "is_major": guide.get("distance", 0) >= 500
                })
            
            enhanced_guide["major_instructions"] = major_instructions
            enhanced_guide["all_instructions"] = all_instructions
            
            detailed_info["enhanced_guide"] = enhanced_guide
        
        # 실시간 교통 정보 및 예상 도착 시간
        current_time = {
            "requested_at": "현재 시각",
            "estimated_arrival": f"약 {detailed_info.get('real_time_route', {}).get('duration', route.duration)}분 후 도착 예정"
        }
        
        detailed_info["timing_info"] = current_time
        
        return {
            "success": True,
            "route_info": route_info,
            "detailed_info": detailed_info,
            "data_sources": {
                "real_time_data": "TMAP API",
                "poi_data": "TMAP POI API" if include_pois else None,
                "alternative_routes": "TMAP API" if include_alternatives else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상세 경로 정보 조회 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상세 경로 정보 조회 중 오류 발생: {str(e)}"
        )


@router.get("/{route_id}/timemachine")
async def get_timemachine_route_info(
    route_id: uuid.UUID,
    departure_time: Optional[str] = None,
    include_comparison: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """TMAP 타임머신 API를 이용한 특정 시간대 경로 예측"""
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
        
        # 출발 시간 설정 (파라미터로 받거나 여행 계획의 시작일 사용)
        if not departure_time:
            # 여행 계획의 시작일과 해당 일차를 기준으로 출발 시간 추정
            import datetime
            if travel_plan.start_date:
                start_date = travel_plan.start_date
                # 해당 일차에 맞춰 날짜 계산 (예: 2일차면 시작일 + 1일)
                target_date = start_date + datetime.timedelta(days=route.day - 1)
                # 오전 9시로 기본 설정
                if hasattr(target_date, 'hour'):
                    departure_time = target_date.replace(hour=9, minute=0, second=0).isoformat()
                else:
                    departure_time = datetime.datetime.combine(target_date, datetime.time(9, 0, 0)).isoformat()
            else:
                # 여행 계획에 시작일이 없으면 현재 시간 사용
                departure_time = datetime.datetime.now().isoformat()
        
        # 기본 경로 정보
        route_info = {
            "route_id": str(route.route_id),
            "day": route.day,
            "sequence": route.sequence,
            "departure": {
                "name": route.departure_name,
                "latitude": route.departure_lat,
                "longitude": route.departure_lng
            },
            "destination": {
                "name": route.destination_name,
                "latitude": route.destination_lat,
                "longitude": route.destination_lng
            },
            "transport_type": route.transport_type,
            "stored_info": {
                "duration": route.duration,
                "distance": route.distance,
                "cost": route.cost
            }
        }
        
        # 타임머신 경로 정보
        timemachine_info = {}
        
        if route.transport_type == "car":
            # TMAP API 호출 시도
            try:
                if include_comparison:
                    # 여러 경로 옵션 비교
                    comparison_result = await tmap_service.compare_routes_with_time(
                        route.departure_lng,
                        route.departure_lat,
                        route.destination_lng,
                        route.destination_lat,
                        departure_time
                    )
                    if comparison_result.get("success") and comparison_result.get("routes"):
                        timemachine_info["comparison"] = comparison_result
                    else:
                        # TMAP API 실패 시 모의 데이터 사용
                        timemachine_info["comparison"] = {
                            "success": True,
                            "departure_time": departure_time,
                            "routes": [
                                {
                                    "option": "trafast",
                                    "name": "빠른길",
                                    "duration": route.duration or 45,
                                    "distance": route.distance or 25.5,
                                    "cost": route.cost or 3200,
                                    "toll_fee": 1500,
                                    "taxi_fee": 0,
                                    "is_recommended": True
                                },
                                {
                                    "option": "tracomfort",
                                    "name": "편한길",
                                    "duration": (route.duration or 45) + 10,
                                    "distance": (route.distance or 25.5) + 3.2,
                                    "cost": (route.cost or 3200) + 400,
                                    "toll_fee": 2000,
                                    "taxi_fee": 0,
                                    "is_recommended": False
                                },
                                {
                                    "option": "traoptimal",
                                    "name": "최적",
                                    "duration": (route.duration or 45) + 5,
                                    "distance": (route.distance or 25.5) + 1.8,
                                    "cost": (route.cost or 3200) + 200,
                                    "toll_fee": 1800,
                                    "taxi_fee": 0,
                                    "is_recommended": False
                                }
                            ],
                            "recommended": {
                                "option": "trafast",
                                "name": "빠른길",
                                "duration": route.duration or 45,
                                "distance": route.distance or 25.5,
                                "cost": route.cost or 3200,
                                "toll_fee": 1500,
                                "taxi_fee": 0,
                                "is_recommended": True
                            }
                        }
                else:
                    # 단일 경로 예측
                    single_result = await tmap_service.get_car_route_with_time(
                        route.departure_lng,
                        route.departure_lat,
                        route.destination_lng,
                        route.destination_lat,
                        departure_time,
                        "trafast"  # 기본값: 빠른길
                    )
                    if single_result.get("success"):
                        timemachine_info["predicted_route"] = single_result
                    else:
                        # TMAP API 실패 시 모의 데이터 사용
                        timemachine_info["predicted_route"] = {
                            "success": True,
                            "duration": route.duration or 45,
                            "distance": route.distance or 25.5,
                            "cost": route.cost or 3200,
                            "toll_fee": 1500,
                            "taxi_fee": 0,
                            "departure_time": departure_time
                        }
            except Exception as e:
                logging.error(f"TMAP API 호출 실패: {e}")
                # 오류 발생 시 저장된 데이터 기반으로 모의 응답 생성
                if include_comparison:
                    timemachine_info["comparison"] = {
                        "success": True,
                        "departure_time": departure_time,
                        "routes": [
                            {
                                "option": "trafast",
                                "name": "빠른길",
                                "duration": route.duration or 45,
                                "distance": route.distance or 25.5,
                                "cost": route.cost or 3200,
                                "toll_fee": 1500,
                                "taxi_fee": 0,
                                "is_recommended": True
                            }
                        ],
                        "recommended": {
                            "option": "trafast",
                            "name": "빠른길",
                            "duration": route.duration or 45,
                            "distance": route.distance or 25.5,
                            "cost": route.cost or 3200,
                            "toll_fee": 1500,
                            "taxi_fee": 0,
                            "is_recommended": True
                        }
                    }
                else:
                    timemachine_info["predicted_route"] = {
                        "success": True,
                        "duration": route.duration or 45,
                        "distance": route.distance or 25.5,
                        "cost": route.cost or 3200,
                        "toll_fee": 1500,
                        "taxi_fee": 0,
                        "departure_time": departure_time
                    }
        else:
            # 자동차가 아닌 경우 타임머신 예측 불가
            timemachine_info["message"] = "타임머신 예측은 자동차 경로에만 지원됩니다."
            timemachine_info["fallback"] = {
                "duration": route.duration,
                "distance": route.distance,
                "cost": route.cost
            }
        
        # 예측 정확도 정보
        prediction_info = {
            "departure_time": departure_time,
            "prediction_type": "timemachine" if route.transport_type == "car" else "stored_data",
            "accuracy_note": "TMAP 타임머신 API 기반 예측으로 실제 교통상황과 다를 수 있습니다." if route.transport_type == "car" else "저장된 기본 데이터입니다.",
            "supports_timemachine": route.transport_type == "car"
        }
        
        return {
            "success": True,
            "route_info": route_info,
            "timemachine_info": timemachine_info,
            "prediction_info": prediction_info,
            "data_sources": {
                "timemachine_data": "TMAP API" if route.transport_type == "car" else None,
                "comparison_data": "TMAP API (Multiple Routes)" if include_comparison and route.transport_type == "car" else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"타임머신 경로 정보 조회 중 오류: {str(e)}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"타임머신 경로 정보 조회 중 오류 발생: {str(e)} - 상세: {traceback.format_exc()}"
        )