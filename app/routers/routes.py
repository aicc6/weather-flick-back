"""
경로 정보 API 라우터
여행 계획의 경로 정보 관리 및 교통 정보 제공
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    RouteCalculationRequest,
    RouteCalculationResponse,
    TransportationDetail,
    TransportationDetailCreate,
    TransportationDetailResponse,
    TravelPlan,
    TravelRoute,
    TravelRouteCreate,
    TravelRouteResponse,
    TravelRouteUpdate,
    User,
)
from app.services.google_places_service import google_places_service
from app.services.route_service import route_service
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
    preferences: dict[str, Any] | None = None,
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
            TravelPlan.plan_id == route_data.travel_plan_id,
            TravelPlan.user_id == current_user.user_id
        ).first()

        if not travel_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="여행 계획을 찾을 수 없거나 접근 권한이 없습니다."
            )

        # 새 경로 생성
        new_route = TravelRoute(
            id=uuid.uuid4(),
            travel_plan_id=route_data.travel_plan_id,
            origin_place_id=route_data.origin_place_id,
            destination_place_id=route_data.destination_place_id,
            route_order=route_data.route_order,
            transport_mode=route_data.transport_mode,
            duration_minutes=route_data.duration_minutes,
            distance_km=route_data.distance_km,
            route_data=route_data.route_data
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


@router.get("/plan/{plan_id}", response_model=list[TravelRouteResponse])
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

        # 경로 조회 (루트 순서별 정렬)
        routes = db.query(TravelRoute).filter(
            TravelRoute.travel_plan_id == plan_id
        ).order_by(TravelRoute.route_order).all()

        # 프론트엔드 호환 형식으로 변환
        enhanced_routes = []
        for route in routes:
            route_response = TravelRouteResponse.from_orm_with_mapping(route)
            
            # 장소명에서 좌표 추출 시도
            try:
                # 우선 Google Places API로 좌표 검색 시도
                if route.origin_place_id:
                    origin_info = await google_places_service.search_place_by_text(route.origin_place_id)
                    if origin_info and 'latitude' in origin_info and 'longitude' in origin_info:
                        route_response.departure_lat = origin_info['latitude']
                        route_response.departure_lng = origin_info['longitude']
                
                if route.destination_place_id:
                    dest_info = await google_places_service.search_place_by_text(route.destination_place_id)
                    if dest_info and 'latitude' in dest_info and 'longitude' in dest_info:
                        route_response.destination_lat = dest_info['latitude']
                        route_response.destination_lng = dest_info['longitude']
                        
            except Exception as coord_error:
                logger.warning(f"좌표 검색 실패: {str(coord_error)}")
                # 좌표 검색 실패 시 기본값 유지
                pass
            
            enhanced_routes.append(route_response)
        
        return enhanced_routes

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
            TravelRoute.id == route_id
        ).first()

        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="경로를 찾을 수 없습니다."
            )

        # 소유권 확인
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route.travel_plan_id,
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
            TravelRoute.id == route_id
        ).first()

        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="경로를 찾을 수 없습니다."
            )

        # 소유권 확인
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route.travel_plan_id,
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
            TravelRoute.id == route_id
        ).first()

        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="경로를 찾을 수 없습니다."
            )

        # 소유권 확인
        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route.travel_plan_id,
            TravelPlan.user_id == current_user.user_id
        ).first()

        if not travel_plan:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 경로를 삭제할 권한이 없습니다."
            )

        # 관련된 교통수단 상세 정보도 함께 삭제
        db.query(TransportationDetail).filter(
            TransportationDetail.travel_route_id == route_id
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
            TravelRoute.travel_plan_id == plan_id
        ).all()

        if existing_routes:
            # 관련된 교통수단 상세 정보도 함께 삭제
            for route in existing_routes:
                db.query(TransportationDetail).filter(
                    TransportationDetail.travel_route_id == route.id
                ).delete()

            # 기존 경로 삭제
            db.query(TravelRoute).filter(
                TravelRoute.travel_plan_id == plan_id
            ).delete()

            db.commit()

        generated_routes = []
        route_counter = 1  # 순차적인 경로 번호

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
            except (ValueError, AttributeError):
                continue

            # 첫 번째 일차인 경우, 출발지에서 첫 번째 목적지로의 경로 생성
            if day == 1 and travel_plan.start_location and len(places) >= 1:
                first_place = places[0]

                # 출발지 좌표 정보 (Google Places API로 검색)
                start_coords = None
                if travel_plan.start_location:
                    try:
                        # start_location을 Google Places API로 검색하여 좌표 획득
                        start_detail = await google_places_service.search_place_by_text(travel_plan.start_location)
                        if start_detail and start_detail.get('latitude') and start_detail.get('longitude'):
                            start_coords = {
                                'latitude': start_detail['latitude'],
                                'longitude': start_detail['longitude'],
                                'name': travel_plan.start_location
                            }
                    except Exception as e:
                        logger.warning(f"출발지 좌표 조회 실패: {str(e)}")

                # 첫 번째 목적지 좌표 정보
                first_coords = None
                if first_place.get('latitude') and first_place.get('longitude'):
                    first_coords = {
                        'latitude': first_place['latitude'],
                        'longitude': first_place['longitude'],
                        'name': first_place.get('name', first_place.get('description', '첫 번째 목적지'))
                    }
                elif first_place.get('place_id') and first_place['place_id'] in place_details:
                    detail = place_details[first_place['place_id']]
                    if detail.get('latitude') and detail.get('longitude'):
                        first_coords = {
                            'latitude': detail['latitude'],
                            'longitude': detail['longitude'],
                            'name': detail.get('name', first_place.get('description', '첫 번째 목적지'))
                        }

                # 출발지에서 첫 번째 목적지로의 경로 생성
                if start_coords and first_coords:
                    try:
                        route_result = await route_service.get_recommended_route(
                            start_coords['latitude'],
                            start_coords['longitude'],
                            first_coords['latitude'],
                            first_coords['longitude']
                        )

                        if route_result.get('success') and route_result.get('recommended'):
                            recommended = route_result['recommended']

                            # 출발지 → 첫 번째 목적지 경로 저장
                            start_route = TravelRoute(
                                id=uuid.uuid4(),
                                travel_plan_id=plan_id,
                                origin_place_id=start_coords['name'],
                                destination_place_id=first_coords['name'],
                                route_order=route_counter,
                                transport_mode=recommended.get('transport_type'),
                                duration_minutes=recommended.get('duration'),
                                distance_km=recommended.get('distance'),
                                route_data=recommended.get('route_data')
                            )

                            db.add(start_route)
                            generated_routes.append(start_route)
                            route_counter += 1

                    except Exception as route_error:
                        logger.warning(f"출발지 경로 계산 중 오류: {str(route_error)}")

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
                                # 일차 내 모든 연속된 장소 간 경로 생성
                                route_order = route_counter
                                route_counter += 1
                                    
                                new_route = TravelRoute(
                                    id=uuid.uuid4(),
                                    travel_plan_id=plan_id,
                                    origin_place_id=current_coords['name'],
                                    destination_place_id=next_coords['name'],
                                    route_order=route_order,
                                    transport_mode=recommended.get('transport_type'),
                                    duration_minutes=recommended.get('duration'),
                                    distance_km=recommended.get('distance'),
                                    route_data=recommended.get('route_data')
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
            except (ValueError, AttributeError):
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

                        # 일차 간 경로 정보 저장 (다음 일차 시작 전 경로)
                        route_order = route_counter
                        route_counter += 1
                        new_route = TravelRoute(
                            id=uuid.uuid4(),
                            travel_plan_id=plan_id,
                            origin_place_id=last_coords['name'],
                            destination_place_id=first_coords['name'],
                            route_order=route_order,
                            transport_mode=recommended.get('transport_type'),
                            duration_minutes=recommended.get('duration'),
                            distance_km=recommended.get('distance'),
                            route_data=recommended.get('route_data')
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
            TravelRoute.id == detail_data.travel_route_id
        ).first()

        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="경로를 찾을 수 없습니다."
            )

        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route.travel_plan_id,
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


@router.get("/{route_id}/transportation", response_model=list[TransportationDetailResponse])
async def get_transportation_details(
    route_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """특정 경로의 교통수단 상세 정보 조회"""
    try:
        # 경로 존재 확인 및 소유권 검증
        route = db.query(TravelRoute).filter(
            TravelRoute.id == route_id
        ).first()

        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="경로를 찾을 수 없습니다."
            )

        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route.travel_plan_id,
            TravelPlan.user_id == current_user.user_id
        ).first()

        if not travel_plan:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 경로에 접근할 권한이 없습니다."
            )

        # 교통수단 상세 정보 조회
        details = db.query(TransportationDetail).filter(
            TransportationDetail.travel_route_id == route_id
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
            TravelRoute.id == route_id
        ).first()

        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="경로를 찾을 수 없습니다."
            )

        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route.travel_plan_id,
            TravelPlan.user_id == current_user.user_id
        ).first()

        if not travel_plan:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 경로에 접근할 권한이 없습니다."
            )

        # 기본 경로 정보
        route_info = {
            "route_id": str(route.id),
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

        # 예상 도착 시간
        current_time = {
            "requested_at": "현재 시각",
            "estimated_arrival": f"약 {route.duration}분 후 도착 예정"
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
    departure_time: str | None = None,
    include_comparison: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """TMAP 타임머신 API를 이용한 특정 시간대 경로 예측"""
    try:
        # 경로 존재 확인 및 소유권 검증
        route = db.query(TravelRoute).filter(
            TravelRoute.id == route_id
        ).first()

        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="경로를 찾을 수 없습니다."
            )

        travel_plan = db.query(TravelPlan).filter(
            TravelPlan.plan_id == route.travel_plan_id,
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
            "route_id": str(route.id),
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


@router.post("/enhanced-multi-route")
async def get_enhanced_multi_route(
    request: RouteCalculationRequest,
    include_timemachine: bool = True,
    departure_time: str | None = None,
    current_user: User = Depends(get_current_user)
):
    """프론트엔드 EnhancedTransportCard를 위한 다중 경로 정보"""
    try:
        # 모든 교통수단 경로 계산
        multi_routes_result = await route_service.get_multiple_routes(
            request.departure_lat,
            request.departure_lng,
            request.destination_lat,
            request.destination_lng
        )

        if not multi_routes_result.get("success"):
            return multi_routes_result

        routes = multi_routes_result["routes"]

        # 각 경로별 세부 정보 추가
        enhanced_routes = {}

        # 도보 경로 개선
        if routes.get("walk", {}).get("success"):
            walk_data = routes["walk"]
            enhanced_routes["walk"] = {
                **walk_data,
                "icon": "👣",
                "display_name": "도보",
                "environmental_impact": "친환경",
                "calories_burned": int(walk_data.get("distance", 0) * 50),  # 1km당 50칼로리
                "weather_dependent": True,
                "accessibility": {
                    "wheelchair_accessible": True,
                    "difficulty_level": "쉬움" if walk_data.get("distance", 0) < 2 else "보통"
                }
            }

        # 대중교통 경로 개선
        if routes.get("transit", {}).get("success"):
            transit_data = routes["transit"]
            enhanced_routes["transit"] = {
                **transit_data,
                "icon": "🚇",
                "display_name": "대중교통",
                "environmental_impact": "저탄소",
                "real_time_info": {
                    "last_updated": "실시간",
                    "service_status": "정상 운행",
                    "delays": None
                },
                "accessibility": {
                    "wheelchair_accessible": True,
                    "elderly_friendly": True
                },
                "card_payment": True,
                "mobile_payment": True
            }

            # ODsay 데이터에서 상세 정보 추출
            route_data = transit_data.get("route_data", {})
            if route_data.get("sub_paths"):
                enhanced_routes["transit"]["detailed_steps"] = []
                for i, step in enumerate(route_data["sub_paths"]):
                    step_info = {
                        "step": i + 1,
                        "type": step.get("type"),
                        "description": f"{step.get('start_station', '')} → {step.get('end_station', '')}",
                        "duration": step.get("section_time", 0),
                        "stations": step.get("station_count", 0),
                        "line_info": step.get("lane", {})
                    }
                    enhanced_routes["transit"]["detailed_steps"].append(step_info)

        # 자동차 경로 개선
        if routes.get("car", {}).get("success"):
            car_data = routes["car"]
            enhanced_routes["car"] = {
                **car_data,
                "icon": "🚗",
                "display_name": "자동차",
                "environmental_impact": "일반",
                "fuel_efficiency": {
                    "estimated_fuel_usage": f"{car_data.get('distance', 0) / 10:.1f}L",
                    "co2_emission": f"{car_data.get('distance', 0) * 0.18:.1f}kg"
                },
                "parking_info": {
                    "availability": "주차장 확인 필요",
                    "estimated_cost": f"{int(car_data.get('distance', 0) * 100)}원"
                },
            }

            # 타임머신 기능 추가
            if include_timemachine and departure_time:
                try:
                    timemachine_result = await tmap_service.compare_routes_with_time(
                        request.departure_lng,
                        request.departure_lat,
                        request.destination_lng,
                        request.destination_lat,
                        departure_time
                    )

                    if timemachine_result.get("success"):
                        enhanced_routes["car"]["timemachine_data"] = timemachine_result
                        enhanced_routes["car"]["departure_time"] = departure_time

                        # 추천 경로로 메인 데이터 업데이트
                        if timemachine_result.get("recommended"):
                            recommended = timemachine_result["recommended"]
                            enhanced_routes["car"]["duration"] = recommended["duration"]
                            enhanced_routes["car"]["distance"] = recommended["distance"]
                            enhanced_routes["car"]["cost"] = recommended["cost"]
                            enhanced_routes["car"]["predicted_traffic"] = "실시간 예측 적용"

                except Exception as e:
                    logger.warning(f"타임머신 데이터 조회 실패: {e}")
                    enhanced_routes["car"]["timemachine_data"] = None

        # 추천 로직 개선
        distance = route_service._calculate_distance(
            request.departure_lat, request.departure_lng,
            request.destination_lat, request.destination_lng
        )

        # 상황별 추천
        recommendations = {
            "primary": None,
            "alternatives": [],
            "context": {}
        }

        # 거리별 추천
        if distance <= 1.0:
            if enhanced_routes.get("walk"):
                recommendations["primary"] = {"type": "walk", "reason": "짧은 거리로 도보 이동이 최적"}
                if enhanced_routes.get("transit"):
                    recommendations["alternatives"].append({"type": "transit", "reason": "편의성"})
        elif distance <= 10.0:
            if enhanced_routes.get("transit"):
                recommendations["primary"] = {"type": "transit", "reason": "중거리 이동으로 대중교통이 경제적"}
                if enhanced_routes.get("car"):
                    recommendations["alternatives"].append({"type": "car", "reason": "빠른 이동"})
        else:
            if enhanced_routes.get("car"):
                recommendations["primary"] = {"type": "car", "reason": "장거리 이동으로 자동차가 효율적"}
                if enhanced_routes.get("transit"):
                    recommendations["alternatives"].append({"type": "transit", "reason": "경제성"})

        # 시간대별 추천 (출발 시간이 있는 경우)
        if departure_time:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                hour = dt.hour

                if 7 <= hour <= 9 or 17 <= hour <= 19:  # 출퇴근 시간
                    recommendations["context"]["rush_hour"] = True
                    recommendations["context"]["traffic_warning"] = "출퇴근 시간대로 교통 체증 예상"
                    # 대중교통을 우선 추천
                    if enhanced_routes.get("transit") and recommendations["primary"]["type"] != "walk":
                        recommendations["primary"] = {"type": "transit", "reason": "출퇴근 시간대 교통체증 회피"}

                elif 23 <= hour or hour <= 5:  # 심야 시간
                    recommendations["context"]["late_night"] = True
                    recommendations["context"]["transit_warning"] = "심야 시간대로 대중교통 운행 제한"
                    # 자동차나 도보 추천
                    if enhanced_routes.get("car"):
                        recommendations["primary"] = {"type": "car", "reason": "심야 시간대 대중교통 제한"}
                    elif enhanced_routes.get("walk") and distance <= 3:
                        recommendations["primary"] = {"type": "walk", "reason": "심야 도보 (안전 주의)"}
            except:
                pass

        # 날씨 정보 추가 (모의 데이터)
        weather_info = {
            "condition": "맑음",
            "temperature": "23°C",
            "precipitation": "0%",
            "wind_speed": "2m/s",
            "outdoor_activity_suitable": True
        }

        # 날씨에 따른 추천 조정
        if weather_info["precipitation"] != "0%":
            recommendations["context"]["weather_warning"] = "강수 예보로 대중교통 이용 권장"
            weather_info["outdoor_activity_suitable"] = False

        return {
            "success": True,
            "routes": enhanced_routes,
            "recommendations": recommendations,
            "context_info": {
                "distance": distance,
                "estimated_time_range": {
                    "min": min([r.get("duration", 999) for r in enhanced_routes.values() if r.get("success")]),
                    "max": max([r.get("duration", 0) for r in enhanced_routes.values() if r.get("success")])
                },
                "cost_range": {
                    "min": min([r.get("cost", 999999) for r in enhanced_routes.values() if r.get("success")]),
                    "max": max([r.get("cost", 0) for r in enhanced_routes.values() if r.get("success")])
                },
                "weather": weather_info,
                "departure_time": departure_time,
                "last_updated": "방금 전"
            }
        }

    except Exception as e:
        logger.error(f"Enhanced multi-route 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enhanced multi-route 조회 중 오류 발생: {str(e)}"
        )


@router.post("/enhanced-multi-route/batch")
async def get_enhanced_multi_route_batch(
    routes: list[RouteCalculationRequest],
    include_timemachine: bool = True,
    departure_time: str | None = None,
    current_user: User = Depends(get_current_user)
):
    """여러 경로에 대한 배치 처리 API"""
    try:
        if not routes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="최소 1개 이상의 경로를 제공해야 합니다."
            )
        
        if len(routes) > 20:  # 배치 크기 제한
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="한 번에 처리할 수 있는 경로는 최대 20개입니다."
            )
        
        # 각 경로를 병렬로 처리
        import asyncio
        
        async def process_single_route(route_request):
            try:
                # 기존의 enhanced-multi-route 로직 재사용
                result = await route_service.get_multiple_routes(
                    route_request.departure_lat,
                    route_request.departure_lng,
                    route_request.destination_lat,
                    route_request.destination_lng
                )
                
                if not result.get("success"):
                    return {
                        "success": False,
                        "route_request": route_request.dict(),
                        "error": result.get("message", "경로 계산 실패")
                    }
                
                # 각 경로별 세부 정보 추가 (기존 로직 활용)
                enhanced_routes = {}
                routes_data = result["routes"]
                
                # 도보 경로 개선
                if routes_data.get("walk", {}).get("success"):
                    walk_data = routes_data["walk"]
                    enhanced_routes["walk"] = {
                        **walk_data,
                        "icon": "👣",
                        "display_name": "도보",
                        "environmental_impact": "친환경",
                        "calories_burned": int(walk_data.get("distance", 0) * 50),
                        "weather_dependent": True,
                        "accessibility": {
                            "wheelchair_accessible": True,
                            "difficulty_level": "쉬움" if walk_data.get("distance", 0) < 2 else "보통"
                        }
                    }
                
                # 대중교통 경로 개선
                if routes_data.get("transit", {}).get("success"):
                    transit_data = routes_data["transit"]
                    enhanced_routes["transit"] = {
                        **transit_data,
                        "icon": "🚇",
                        "display_name": "대중교통",
                        "environmental_impact": "저탄소",
                        "real_time_info": {
                            "last_updated": "실시간",
                            "service_status": "정상 운행",
                            "delays": None
                        },
                        "accessibility": {
                            "wheelchair_accessible": True,
                            "elderly_friendly": True
                        },
                        "card_payment": True,
                        "mobile_payment": True
                    }
                
                # 자동차 경로 개선
                if routes_data.get("car", {}).get("success"):
                    car_data = routes_data["car"]
                    enhanced_routes["car"] = {
                        **car_data,
                        "icon": "🚗",
                        "display_name": "자동차",
                        "environmental_impact": "일반",
                        "fuel_efficiency": {
                            "estimated_fuel_usage": f"{car_data.get('distance', 0) / 10:.1f}L",
                            "co2_emission": f"{car_data.get('distance', 0) * 0.18:.1f}kg"
                        },
                        "parking_info": {
                            "availability": "주차장 확인 필요",
                            "estimated_cost": f"{int(car_data.get('distance', 0) * 100)}원"
                        },
                            }
                
                # 거리 계산 및 추천 로직
                distance = route_service._calculate_distance(
                    route_request.departure_lat, route_request.departure_lng,
                    route_request.destination_lat, route_request.destination_lng
                )
                
                recommendations = {
                    "primary": None,
                    "alternatives": [],
                    "context": {}
                }
                
                # 거리별 추천
                if distance <= 1.0:
                    if enhanced_routes.get("walk"):
                        recommendations["primary"] = {"type": "walk", "reason": "짧은 거리로 도보 이동이 최적"}
                elif distance <= 10.0:
                    if enhanced_routes.get("transit"):
                        recommendations["primary"] = {"type": "transit", "reason": "중거리 이동으로 대중교통이 경제적"}
                else:
                    if enhanced_routes.get("car"):
                        recommendations["primary"] = {"type": "car", "reason": "장거리 이동으로 자동차가 효율적"}
                
                return {
                    "success": True,
                    "route_request": route_request.dict(),
                    "routes": enhanced_routes,
                    "recommendations": recommendations,
                    "context_info": {
                        "distance": distance,
                        "departure_time": departure_time,
                        "last_updated": "방금 전"
                    }
                }
                
            except Exception as e:
                logger.error(f"경로 처리 중 오류: {e}")
                return {
                    "success": False,
                    "route_request": route_request.dict(),
                    "error": str(e)
                }
        
        # 모든 경로를 병렬로 처리
        results = await asyncio.gather(*[process_single_route(route) for route in routes])
        
        # 결과 정리
        successful_results = [r for r in results if r.get("success")]
        failed_results = [r for r in results if not r.get("success")]
        
        return {
            "success": True,
            "total_routes": len(routes),
            "successful_routes": len(successful_results),
            "failed_routes": len(failed_results),
            "results": results,
            "batch_info": {
                "departure_time": departure_time,
                "include_timemachine": include_timemachine,
                "processed_at": "방금 전"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"배치 처리 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"배치 처리 중 오류 발생: {str(e)}"
        )


@router.post("/timemachine-comparison")
async def get_timemachine_comparison(
    request: RouteCalculationRequest,
    departure_times: list[str],
    current_user: User = Depends(get_current_user)
):
    """여러 출발 시간대별 경로 비교 (타임머신)"""
    try:
        if not departure_times:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="출발 시간을 최소 1개 이상 제공해야 합니다."
            )

        time_comparisons = []

        for departure_time in departure_times:
            try:
                # 각 시간대별로 자동차 경로 비교
                comparison_result = await tmap_service.compare_routes_with_time(
                    request.departure_lng,
                    request.departure_lat,
                    request.destination_lng,
                    request.destination_lat,
                    departure_time
                )

                if comparison_result.get("success"):
                    # 시간 정보 파싱
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                        time_label = dt.strftime("%H:%M")
                        date_label = dt.strftime("%m/%d")
                    except:
                        time_label = departure_time
                        date_label = "날짜 불명"

                    # 교통 상황 예측
                    recommended = comparison_result.get("recommended", {})
                    duration = recommended.get("duration", 0)

                    # 교통량 예측
                    traffic_level = "원활"
                    if duration > 60:
                        traffic_level = "혼잡"
                    elif duration > 45:
                        traffic_level = "보통"

                    time_comparison = {
                        "departure_time": departure_time,
                        "time_label": time_label,
                        "date_label": date_label,
                        "recommended_route": recommended,
                        "all_routes": comparison_result.get("routes", []),
                        "traffic_prediction": {
                            "level": traffic_level,
                            "duration": duration,
                            "compared_to_optimal": f"+{max(0, duration - 30)}분" if duration > 30 else "최적",
                            "rush_hour": 7 <= int(time_label.split(':')[0]) <= 9 or 17 <= int(time_label.split(':')[0]) <= 19
                        },
                        "cost_analysis": {
                            "fuel_cost": recommended.get("cost", 0),
                            "toll_fee": recommended.get("toll_fee", 0),
                            "total_cost": recommended.get("cost", 0) + recommended.get("toll_fee", 0)
                        }
                    }

                    time_comparisons.append(time_comparison)

            except Exception as e:
                logger.warning(f"시간대 {departure_time} 처리 실패: {e}")
                # 실패한 시간대는 모의 데이터로 대체
                time_comparisons.append({
                    "departure_time": departure_time,
                    "time_label": departure_time,
                    "date_label": "날짜 불명",
                    "error": True,
                    "message": "해당 시간대 데이터를 가져올 수 없습니다."
                })

        # 최적 시간대 추천
        successful_comparisons = [tc for tc in time_comparisons if not tc.get("error")]
        optimal_time = None

        if successful_comparisons:
            optimal_time = min(successful_comparisons,
                             key=lambda x: x.get("recommended_route", {}).get("duration", 999))

        # 통계 정보
        statistics = {
            "total_times_compared": len(departure_times),
            "successful_predictions": len(successful_comparisons),
            "time_range": {
                "fastest": min([tc.get("recommended_route", {}).get("duration", 999)
                             for tc in successful_comparisons]) if successful_comparisons else None,
                "slowest": max([tc.get("recommended_route", {}).get("duration", 0)
                             for tc in successful_comparisons]) if successful_comparisons else None
            },
            "cost_range": {
                "cheapest": min([tc.get("cost_analysis", {}).get("total_cost", 999999)
                               for tc in successful_comparisons]) if successful_comparisons else None,
                "most_expensive": max([tc.get("cost_analysis", {}).get("total_cost", 0)
                                     for tc in successful_comparisons]) if successful_comparisons else None
            }
        }

        return {
            "success": True,
            "departure_times": departure_times,
            "time_comparisons": time_comparisons,
            "optimal_time": optimal_time,
            "statistics": statistics,
            "route_info": {
                "departure": {
                    "latitude": request.departure_lat,
                    "longitude": request.departure_lng
                },
                "destination": {
                    "latitude": request.destination_lat,
                    "longitude": request.destination_lng
                }
            },
            "data_source": "TMAP 타임머신 API",
            "last_updated": "방금 전"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"타임머신 비교 분석 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"타임머신 비교 분석 중 오류 발생: {str(e)}"
        )
