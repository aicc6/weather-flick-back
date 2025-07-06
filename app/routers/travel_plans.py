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


@router.post("/", response_model=dict)
async def create_travel_plan(
    plan_data: TravelPlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """여행 계획 생성"""
    try:
        # 새 여행 계획 생성 (UUID는 자동 생성)
        db_plan = TravelPlan(
            user_id=current_user.id,
            title=plan_data.title,
            description=plan_data.description,
            start_date=plan_data.start_date,
            end_date=plan_data.end_date,
            budget=plan_data.budget,
            participants=plan_data.participants,
            transportation=plan_data.transportation,
            start_location=plan_data.start_location,
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
        response_data = [
            convert_uuids_to_strings(TravelPlanResponse.from_orm(plan))
            for plan in plans
        ]

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
