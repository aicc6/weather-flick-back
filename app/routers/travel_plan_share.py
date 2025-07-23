import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_current_user_optional
from app.database import get_db
from app.models import (
    TravelPlan,
    TravelPlanShare,
    TravelPlanShareCreate,
    TravelPlanShareResponse,
    User,
)
from app.utils import (
    convert_uuids_to_strings,
    create_error_response,
    create_standard_response,
)

router = APIRouter(
    prefix="/travel-plans",
    tags=["travel-plan-shares"],
    responses={404: {"description": "Not found"}},
)


def generate_share_token() -> str:
    """고유한 공유 토큰 생성"""
    return secrets.token_urlsafe(32)


@router.post("/{plan_id}/share", response_model=dict)
async def create_share_link(
    plan_id: str,
    share_data: TravelPlanShareCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """여행 계획 공유 링크 생성"""
    try:
        # 여행 계획 확인
        plan = (
            db.query(TravelPlan)
            .filter(TravelPlan.plan_id == plan_id, TravelPlan.user_id == current_user.id)
            .first()
        )
        
        if not plan:
            return create_error_response(
                code="NOT_FOUND", 
                message="여행 계획을 찾을 수 없거나 권한이 없습니다."
            )
        
        # 기존 활성 공유 링크 확인
        existing_share = (
            db.query(TravelPlanShare)
            .filter(
                TravelPlanShare.plan_id == plan_id,
                TravelPlanShare.is_active == True,
                TravelPlanShare.created_by == current_user.id,
            )
            .first()
        )
        
        if existing_share:
            # 기존 공유 링크 비활성화
            existing_share.is_active = False
            db.commit()
        
        # 새 공유 링크 생성
        share_token = generate_share_token()
        
        db_share = TravelPlanShare(
            plan_id=plan_id,
            share_token=share_token,
            permission=share_data.permission,
            expires_at=share_data.expires_at,
            max_uses=share_data.max_uses,
            created_by=current_user.id,
        )
        
        db.add(db_share)
        db.commit()
        db.refresh(db_share)
        
        # 응답 데이터 구성
        response_data = {
            "share_id": db_share.share_id,
            "plan_id": db_share.plan_id,
            "share_token": db_share.share_token,
            "share_link": f"/shared/{share_token}",  # 프론트엔드에서 전체 URL 구성
            "permission": db_share.permission,
            "expires_at": db_share.expires_at,
            "max_uses": db_share.max_uses,
            "use_count": db_share.use_count,
            "is_active": db_share.is_active,
            "created_at": db_share.created_at,
            "created_by": db_share.created_by,
        }
        
        return create_standard_response(
            success=True, 
            data=convert_uuids_to_strings(response_data)
        )
        
    except Exception as e:
        db.rollback()
        return create_error_response(
            code="SHARE_ERROR",
            message="공유 링크 생성에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.get("/{plan_id}/shares", response_model=dict)
async def get_share_links(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """여행 계획의 공유 링크 목록 조회"""
    try:
        # 여행 계획 확인
        plan = (
            db.query(TravelPlan)
            .filter(TravelPlan.plan_id == plan_id, TravelPlan.user_id == current_user.id)
            .first()
        )
        
        if not plan:
            return create_error_response(
                code="NOT_FOUND", 
                message="여행 계획을 찾을 수 없거나 권한이 없습니다."
            )
        
        # 공유 링크 목록 조회
        shares = (
            db.query(TravelPlanShare)
            .filter(TravelPlanShare.plan_id == plan_id)
            .order_by(TravelPlanShare.created_at.desc())
            .all()
        )
        
        response_data = []
        for share in shares:
            share_dict = {
                "share_id": share.share_id,
                "plan_id": share.plan_id,
                "share_token": share.share_token,
                "share_link": f"/shared/{share.share_token}",
                "permission": share.permission,
                "expires_at": share.expires_at,
                "max_uses": share.max_uses,
                "use_count": share.use_count,
                "is_active": share.is_active,
                "created_at": share.created_at,
                "created_by": share.created_by,
            }
            response_data.append(convert_uuids_to_strings(share_dict))
        
        return create_standard_response(success=True, data=response_data)
        
    except Exception as e:
        return create_error_response(
            code="QUERY_ERROR",
            message="공유 링크 목록 조회에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.put("/{plan_id}/shares/{share_id}", response_model=dict)
async def update_share_link(
    plan_id: str,
    share_id: str,
    is_active: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """공유 링크 활성화/비활성화"""
    try:
        # 공유 링크 확인
        share = (
            db.query(TravelPlanShare)
            .filter(
                TravelPlanShare.share_id == share_id,
                TravelPlanShare.plan_id == plan_id,
                TravelPlanShare.created_by == current_user.id,
            )
            .first()
        )
        
        if not share:
            return create_error_response(
                code="NOT_FOUND", 
                message="공유 링크를 찾을 수 없거나 권한이 없습니다."
            )
        
        # 상태 업데이트
        share.is_active = is_active
        db.commit()
        db.refresh(share)
        
        share_dict = {
            "share_id": share.share_id,
            "plan_id": share.plan_id,
            "share_token": share.share_token,
            "share_link": f"/shared/{share.share_token}",
            "permission": share.permission,
            "expires_at": share.expires_at,
            "max_uses": share.max_uses,
            "use_count": share.use_count,
            "is_active": share.is_active,
            "created_at": share.created_at,
            "created_by": share.created_by,
        }
        
        return create_standard_response(
            success=True, 
            data=convert_uuids_to_strings(share_dict)
        )
        
    except Exception as e:
        db.rollback()
        return create_error_response(
            code="UPDATE_ERROR",
            message="공유 링크 업데이트에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.delete("/{plan_id}/shares/{share_id}", response_model=dict)
async def delete_share_link(
    plan_id: str,
    share_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """공유 링크 삭제"""
    try:
        # 공유 링크 확인
        share = (
            db.query(TravelPlanShare)
            .filter(
                TravelPlanShare.share_id == share_id,
                TravelPlanShare.plan_id == plan_id,
                TravelPlanShare.created_by == current_user.id,
            )
            .first()
        )
        
        if not share:
            return create_error_response(
                code="NOT_FOUND", 
                message="공유 링크를 찾을 수 없거나 권한이 없습니다."
            )
        
        # 삭제
        db.delete(share)
        db.commit()
        
        return create_standard_response(
            success=True, 
            data={"message": "공유 링크가 삭제되었습니다."}
        )
        
    except Exception as e:
        db.rollback()
        return create_error_response(
            code="DELETE_ERROR",
            message="공유 링크 삭제에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


# 공유된 여행 계획 조회를 위한 별도 라우터
shared_router = APIRouter(
    prefix="/shared",
    tags=["shared-plans"],
    responses={404: {"description": "Not found"}},
)


@shared_router.get("/{share_token}", response_model=dict)
async def get_shared_plan(
    share_token: str,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """공유된 여행 계획 조회"""
    try:
        # 공유 링크 확인
        share = (
            db.query(TravelPlanShare)
            .filter(
                TravelPlanShare.share_token == share_token,
                TravelPlanShare.is_active == True,
            )
            .first()
        )
        
        if not share:
            return create_error_response(
                code="NOT_FOUND", 
                message="유효하지 않은 공유 링크입니다."
            )
        
        # 만료 시간 확인
        if share.expires_at and share.expires_at < datetime.now(timezone.utc):
            share.is_active = False
            db.commit()
            return create_error_response(
                code="EXPIRED", 
                message="만료된 공유 링크입니다."
            )
        
        # 사용 횟수 확인
        if share.max_uses and share.use_count >= share.max_uses:
            share.is_active = False
            db.commit()
            return create_error_response(
                code="MAX_USES_REACHED", 
                message="최대 사용 횟수를 초과한 공유 링크입니다."
            )
        
        # 사용 횟수 증가
        share.use_count += 1
        db.commit()
        
        # 여행 계획 조회
        plan = db.query(TravelPlan).filter(TravelPlan.plan_id == share.plan_id).first()
        
        if not plan:
            return create_error_response(
                code="NOT_FOUND", 
                message="여행 계획을 찾을 수 없습니다."
            )
        
        # 권한 확인
        can_edit = False
        if current_user:
            # 소유자이거나 편집 권한이 있는 공유 링크인 경우
            if plan.user_id == current_user.id or share.permission == "edit":
                can_edit = True
        
        # 응답 데이터 구성
        from app.models import TravelPlanResponse
        plan_response = TravelPlanResponse.from_orm(plan)
        response_data = convert_uuids_to_strings(plan_response)
        response_data["can_edit"] = can_edit
        response_data["share_permission"] = share.permission
        
        return create_standard_response(success=True, data=response_data)
        
    except Exception as e:
        return create_error_response(
            code="QUERY_ERROR",
            message="공유된 여행 계획 조회에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )