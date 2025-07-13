import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    TravelPlan,
    TravelPlanCreate,
    TravelPlanResponse,
    TravelPlanUpdate,
    User,
    CategoryCode,
)
from app.utils import (
    convert_uuids_to_strings,
    create_error_response,
    create_pagination_info,
    create_standard_response,
)

router = APIRouter(
    prefix="/travel-plans",
    tags=["travel-plans"],
    responses={404: {"description": "Not found"}},
)


def convert_category_codes_in_itinerary(itinerary: dict, db: Session) -> dict:
    """여행 일정 내의 카테고리 코드를 한글로 변환"""
    if not itinerary or not isinstance(itinerary, dict):
        return itinerary
    
    # 카테고리 코드 캐시
    category_cache = {}
    
    for day_key, day_places in itinerary.items():
        if isinstance(day_places, list):
            for place in day_places:
                if isinstance(place, dict) and 'tags' in place and isinstance(place['tags'], list):
                    # 태그 중 카테고리 코드 형식(예: A02, A04)인 것을 변환
                    converted_tags = []
                    for tag in place['tags']:
                        if isinstance(tag, str) and tag.startswith('A') and len(tag) == 3:
                            # 캐시 확인
                            if tag in category_cache:
                                converted_tags.append(category_cache[tag])
                            else:
                                # DB에서 조회
                                category = db.query(CategoryCode).filter(CategoryCode.category_code == tag).first()
                                if category:
                                    category_cache[tag] = category.category_name
                                    converted_tags.append(category.category_name)
                                else:
                                    converted_tags.append(tag)
                        else:
                            converted_tags.append(tag)
                    place['tags'] = converted_tags
    
    return itinerary


@router.post("/", response_model=dict)
async def create_travel_plan(
    plan_data: TravelPlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """여행 계획 생성"""
    print(f"=== Travel Plan Creation Request ===")
    print(f"User: {current_user.email if current_user else 'No user'}")
    print(f"Plan data: {plan_data.dict()}")
    print(f"=================================")
    
    try:
        # 새 여행 계획 생성 (UUID는 자동 생성)
        from app.models import TravelPlanStatus
        
        # status 처리
        status = TravelPlanStatus.PLANNING  # 기본값
        if plan_data.status:
            try:
                status = TravelPlanStatus(plan_data.status)
            except ValueError:
                status = TravelPlanStatus.PLANNING
        
        db_plan = TravelPlan(
            user_id=current_user.id,
            title=plan_data.title,
            description=plan_data.description,
            start_date=plan_data.start_date,
            end_date=plan_data.end_date,
            budget=plan_data.budget,
            itinerary=plan_data.itinerary,
            participants=plan_data.participants,
            transportation=plan_data.transportation,
            start_location=plan_data.start_location,
            weather_info=plan_data.weather_info,
            status=status,
            plan_type=plan_data.plan_type or "manual",  # 기본값은 'manual'
        )

        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)

        # 응답 데이터 구성
        response_data = TravelPlanResponse.from_orm(db_plan)
        response_dict = convert_uuids_to_strings(response_data)

        return create_standard_response(success=True, data=response_dict)

    except Exception as e:
        db.rollback()
        import traceback
        print(f"Travel plan creation error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        print(f"Plan data: {plan_data}")
        return create_error_response(
            code="CREATION_ERROR",
            message="여행 계획 생성에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.get("/", response_model=dict)
async def get_travel_plans(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """사용자 여행 계획 목록 조회"""
    try:
        # 기본 쿼리
        query = db.query(TravelPlan).filter(TravelPlan.user_id == current_user.id)

        # 상태 필터
        if status:
            query = query.filter(TravelPlan.status == status)

        # 총 개수 조회
        total = query.count()

        # 페이지네이션 적용
        offset = (page - 1) * limit
        plans = query.offset(offset).limit(limit).all()

        # 응답 데이터 구성
        response_data = []
        
        for plan in plans:
            # weather_info가 JSON 문자열인 경우 파싱
            if hasattr(plan, 'weather_info') and plan.weather_info and isinstance(plan.weather_info, str):
                try:
                    plan.weather_info = json.loads(plan.weather_info)
                except (json.JSONDecodeError, TypeError):
                    plan.weather_info = None
            
            # itinerary가 JSON 문자열인 경우 파싱
            if hasattr(plan, 'itinerary') and plan.itinerary and isinstance(plan.itinerary, str):
                try:
                    plan.itinerary = json.loads(plan.itinerary)
                except (json.JSONDecodeError, TypeError):
                    plan.itinerary = None
            
            # 카테고리 코드를 한글로 변환
            plan.itinerary = convert_category_codes_in_itinerary(plan.itinerary, db)
            
            response_data.append(convert_uuids_to_strings(TravelPlanResponse.from_orm(plan)))

        # 페이지네이션 정보
        pagination = create_pagination_info(page, limit, total)

        return create_standard_response(
            success=True, data=response_data, pagination=pagination
        )

    except Exception as e:
        return create_error_response(
            code="QUERY_ERROR",
            message="여행 계획 조회에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.get("/{plan_id}", response_model=dict)
async def get_travel_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """특정 여행 계획 조회"""
    try:
        plan = (
            db.query(TravelPlan)
            .filter(TravelPlan.plan_id == plan_id, TravelPlan.user_id == current_user.id)
            .first()
        )

        if not plan:
            return create_error_response(
                code="NOT_FOUND", message="여행 계획을 찾을 수 없습니다."
            )

        # weather_info가 JSON 문자열인 경우 파싱
        if hasattr(plan, 'weather_info') and plan.weather_info and isinstance(plan.weather_info, str):
            try:
                plan.weather_info = json.loads(plan.weather_info)
            except (json.JSONDecodeError, TypeError):
                plan.weather_info = None
        
        # itinerary가 JSON 문자열인 경우 파싱
        if hasattr(plan, 'itinerary') and plan.itinerary and isinstance(plan.itinerary, str):
            try:
                plan.itinerary = json.loads(plan.itinerary)
            except (json.JSONDecodeError, TypeError):
                plan.itinerary = None
        
        # 카테고리 코드를 한글로 변환
        plan.itinerary = convert_category_codes_in_itinerary(plan.itinerary, db)
        
        response_data = convert_uuids_to_strings(TravelPlanResponse.from_orm(plan))

        return create_standard_response(success=True, data=response_data)

    except Exception as e:
        return create_error_response(
            code="QUERY_ERROR",
            message="여행 계획 조회에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.put("/{plan_id}", response_model=dict)
async def update_travel_plan(
    plan_id: str,
    plan_data: TravelPlanUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """여행 계획 수정"""
    try:
        plan = (
            db.query(TravelPlan)
            .filter(TravelPlan.plan_id == plan_id, TravelPlan.user_id == current_user.id)
            .first()
        )

        if not plan:
            return create_error_response(
                code="NOT_FOUND", message="여행 계획을 찾을 수 없습니다."
            )

        # 업데이트할 필드들
        update_data = plan_data.dict(exclude_unset=True)

        # itinerary가 dict인 경우 JSON 문자열로 변환
        if "itinerary" in update_data and update_data["itinerary"]:
            update_data["itinerary"] = json.dumps(
                update_data["itinerary"], ensure_ascii=False
            )
        
        # weather_info가 dict인 경우 JSON 문자열로 변환
        if "weather_info" in update_data and update_data["weather_info"]:
            update_data["weather_info"] = json.dumps(
                update_data["weather_info"], ensure_ascii=False
            )

        for field, value in update_data.items():
            setattr(plan, field, value)

        db.commit()
        db.refresh(plan)

        response_data = convert_uuids_to_strings(TravelPlanResponse.from_orm(plan))

        return create_standard_response(success=True, data=response_data)

    except Exception as e:
        db.rollback()
        return create_error_response(
            code="UPDATE_ERROR",
            message="여행 계획 수정에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.delete("/{plan_id}", response_model=dict)
async def delete_travel_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """여행 계획 삭제"""
    try:
        plan = (
            db.query(TravelPlan)
            .filter(TravelPlan.plan_id == plan_id, TravelPlan.user_id == current_user.id)
            .first()
        )

        if not plan:
            return create_error_response(
                code="NOT_FOUND", message="여행 계획을 찾을 수 없습니다."
            )

        # 관련 경로 데이터 먼저 삭제
        from app.models import TravelRoute
        db.query(TravelRoute).filter(TravelRoute.plan_id == plan_id).delete()
        
        # 여행 계획 삭제
        db.delete(plan)
        db.commit()

        return create_standard_response(
            success=True, data={"message": "여행 계획이 삭제되었습니다."}
        )

    except Exception as e:
        db.rollback()
        return create_error_response(
            code="DELETE_ERROR",
            message="여행 계획 삭제에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )
