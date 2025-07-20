"""
여행 코스 저장 관련 API 엔드포인트
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_active_user
from app.database import get_db, engine
from app.models import (
    TravelCourse,
    TravelCourseSave,
    TravelCourseSaveCreate,
    TravelCourseSaveResponse,
    User,
    Base,
)

router = APIRouter(
    prefix="/travel-course-saves",
    tags=["travel-course-saves"],
    responses={404: {"description": "Not found"}},
)


@router.post("/init-table")
async def init_table():
    """테이블 초기화 (개발용)"""
    try:
        Base.metadata.create_all(bind=engine)
        return {"message": "Table created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Table creation failed: {str(e)}")


def get_travel_course_with_stats(
    db: Session, content_id: str, current_user_id: Optional[UUID] = None
) -> Optional[dict]:
    """여행 코스 정보와 저장 통계를 함께 가져오는 헬퍼 함수"""
    travel_course = db.query(TravelCourse).filter(
        TravelCourse.content_id == content_id
    ).first()
    
    if not travel_course:
        return None
    
    # 저장 수 계산
    saves_count = db.query(func.count(TravelCourseSave.id)).filter(
        TravelCourseSave.content_id == content_id
    ).scalar()
    
    result = {
        "content_id": travel_course.content_id,
        "course_name": travel_course.course_name,
        "course_theme": travel_course.course_theme,
        "region_code": travel_course.region_code,
        "required_time": travel_course.required_time,
        "difficulty_level": travel_course.difficulty_level,
        "schedule": travel_course.schedule,
        "course_distance": travel_course.course_distance,
        "address": travel_course.address,
        "overview": travel_course.overview,
        "first_image": travel_course.first_image,
        "latitude": float(travel_course.latitude) if travel_course.latitude else None,
        "longitude": float(travel_course.longitude) if travel_course.longitude else None,
        "saves_count": saves_count,
        "is_saved": False,
    }
    
    # 현재 사용자의 저장 여부 확인
    if current_user_id:
        is_saved = db.query(TravelCourseSave).filter(
            and_(
                TravelCourseSave.user_id == current_user_id,
                TravelCourseSave.content_id == content_id
            )
        ).first() is not None
        
        result["is_saved"] = is_saved
    
    return result


@router.post("/", response_model=TravelCourseSaveResponse)
async def create_travel_course_save(
    save_data: TravelCourseSaveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """여행 코스 저장"""
    # 여행 코스 존재 확인
    travel_course = db.query(TravelCourse).filter(
        TravelCourse.content_id == save_data.content_id
    ).first()
    
    if not travel_course:
        raise HTTPException(status_code=404, detail="Travel course not found")
    
    # 이미 저장했는지 확인
    existing_save = db.query(TravelCourseSave).filter(
        and_(
            TravelCourseSave.user_id == current_user.user_id,
            TravelCourseSave.content_id == save_data.content_id
        )
    ).first()
    
    if existing_save:
        raise HTTPException(status_code=400, detail="Already saved this travel course")
    
    # 저장 생성
    new_save = TravelCourseSave(
        user_id=current_user.user_id,
        content_id=save_data.content_id,
        note=save_data.note
    )
    
    try:
        db.add(new_save)
        db.commit()
        db.refresh(new_save)
        
        # 응답에 여행 코스 정보 포함
        travel_course_data = get_travel_course_with_stats(
            db, new_save.content_id, current_user.user_id
        )
        
        response = TravelCourseSaveResponse(
            id=new_save.id,
            user_id=new_save.user_id,
            content_id=new_save.content_id,
            note=new_save.note,
            created_at=new_save.created_at,
            updated_at=new_save.updated_at,
            travel_course=travel_course_data
        )
        
        return response
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to save travel course")


@router.delete("/{content_id}")
async def delete_travel_course_save(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """여행 코스 저장 취소"""
    save = db.query(TravelCourseSave).filter(
        and_(
            TravelCourseSave.user_id == current_user.user_id,
            TravelCourseSave.content_id == content_id
        )
    ).first()
    
    if not save:
        raise HTTPException(status_code=404, detail="Save not found")
    
    db.delete(save)
    db.commit()
    
    return {"message": "Save removed successfully"}


@router.get("/", response_model=List[TravelCourseSaveResponse])
async def get_my_travel_course_saves(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """내가 저장한 여행 코스 목록 조회"""
    saves = db.query(TravelCourseSave).filter(
        TravelCourseSave.user_id == current_user.user_id
    ).order_by(
        TravelCourseSave.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    result = []
    for save in saves:
        travel_course_data = get_travel_course_with_stats(
            db, save.content_id, current_user.user_id
        )
        result.append(
            TravelCourseSaveResponse(
                id=save.id,
                user_id=save.user_id,
                content_id=save.content_id,
                note=save.note,
                created_at=save.created_at,
                updated_at=save.updated_at,
                travel_course=travel_course_data
            )
        )
    
    return result


@router.put("/{content_id}", response_model=TravelCourseSaveResponse)
async def update_travel_course_save_note(
    content_id: str,
    note: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """저장한 여행 코스의 메모 수정"""
    save = db.query(TravelCourseSave).filter(
        and_(
            TravelCourseSave.user_id == current_user.user_id,
            TravelCourseSave.content_id == content_id
        )
    ).first()
    
    if not save:
        raise HTTPException(status_code=404, detail="Save not found")
    
    save.note = note
    db.commit()
    db.refresh(save)
    
    # 응답에 여행 코스 정보 포함
    travel_course_data = get_travel_course_with_stats(
        db, save.content_id, current_user.user_id
    )
    
    response = TravelCourseSaveResponse(
        id=save.id,
        user_id=save.user_id,
        content_id=save.content_id,
        note=save.note,
        created_at=save.created_at,
        updated_at=save.updated_at,
        travel_course=travel_course_data
    )
    
    return response