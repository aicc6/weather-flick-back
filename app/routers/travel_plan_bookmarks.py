"""
여행 계획 즐겨찾기 관련 API 엔드포인트
"""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import TravelPlan, TravelPlanBookmark, User
from app.utils import create_error_response, create_standard_response

router = APIRouter(
    prefix="/travel-plans",
    tags=["travel-plan-bookmarks"],
    responses={404: {"description": "Not found"}},
)


@router.post("/{plan_id}/bookmark", response_model=dict)
async def toggle_bookmark(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """여행 계획 즐겨찾기 토글 (추가/제거)"""
    try:
        # 여행 계획 확인
        plan = db.query(TravelPlan).filter(TravelPlan.plan_id == plan_id).first()
        
        if not plan:
            return create_error_response(
                code="NOT_FOUND",
                message="여행 계획을 찾을 수 없습니다.",
            )
        
        # 기존 즐겨찾기 확인
        existing_bookmark = (
            db.query(TravelPlanBookmark)
            .filter(
                and_(
                    TravelPlanBookmark.user_id == current_user.user_id,
                    TravelPlanBookmark.plan_id == plan_id,
                )
            )
            .first()
        )
        
        if existing_bookmark:
            # 즐겨찾기 제거
            db.delete(existing_bookmark)
            db.commit()
            
            return create_standard_response(
                success=True,
                data={"bookmarked": False, "message": "즐겨찾기가 해제되었습니다."},
            )
        else:
            # 즐겨찾기 추가
            new_bookmark = TravelPlanBookmark(
                user_id=current_user.user_id,
                plan_id=plan_id,
            )
            db.add(new_bookmark)
            db.commit()
            
            return create_standard_response(
                success=True,
                data={"bookmarked": True, "message": "즐겨찾기에 추가되었습니다."},
            )
            
    except Exception as e:
        db.rollback()
        return create_error_response(
            code="BOOKMARK_ERROR",
            message="즐겨찾기 처리 중 오류가 발생했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.get("/bookmarks", response_model=dict)
async def get_bookmarked_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """사용자의 즐겨찾기한 여행 계획 목록 조회"""
    try:
        # 즐겨찾기한 계획 ID 목록 조회
        bookmarked_plan_ids = (
            db.query(TravelPlanBookmark.plan_id)
            .filter(TravelPlanBookmark.user_id == current_user.user_id)
            .all()
        )
        
        plan_ids = [str(bookmark.plan_id) for bookmark in bookmarked_plan_ids]
        
        if not plan_ids:
            return create_standard_response(
                success=True,
                data={"plans": [], "total": 0},
            )
        
        # 여행 계획 조회
        plans = (
            db.query(TravelPlan)
            .filter(TravelPlan.plan_id.in_(plan_ids))
            .order_by(TravelPlan.created_at.desc())
            .all()
        )
        
        # 응답 데이터 구성
        plans_data = []
        for plan in plans:
            plan_dict = {
                "plan_id": str(plan.plan_id),
                "title": plan.title,
                "description": plan.description,
                "start_date": plan.start_date.isoformat() if plan.start_date else None,
                "end_date": plan.end_date.isoformat() if plan.end_date else None,
                "status": plan.status,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
                "is_bookmarked": True,  # 즐겨찾기 목록이므로 항상 true
            }
            plans_data.append(plan_dict)
        
        return create_standard_response(
            success=True,
            data={"plans": plans_data, "total": len(plans_data)},
        )
        
    except Exception as e:
        return create_error_response(
            code="QUERY_ERROR",
            message="즐겨찾기 목록 조회 중 오류가 발생했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.get("/{plan_id}/bookmark/status", response_model=dict)
async def get_bookmark_status(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """특정 여행 계획의 즐겨찾기 상태 확인"""
    try:
        # 즐겨찾기 여부 확인
        bookmark = (
            db.query(TravelPlanBookmark)
            .filter(
                and_(
                    TravelPlanBookmark.user_id == current_user.user_id,
                    TravelPlanBookmark.plan_id == plan_id,
                )
            )
            .first()
        )
        
        return create_standard_response(
            success=True,
            data={"bookmarked": bookmark is not None},
        )
        
    except Exception as e:
        return create_error_response(
            code="QUERY_ERROR",
            message="즐겨찾기 상태 확인 중 오류가 발생했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )