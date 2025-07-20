
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import TravelCourseLike, User
from app.schemas import TravelCourseLikeCreate, TravelCourseLikeResponse
from app.auth import get_current_user

router = APIRouter(prefix="/travel-course-likes", tags=["travel_course_likes"])

@router.post("/", response_model=TravelCourseLikeResponse)
async def create_travel_course_like(
    course: TravelCourseLikeCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # 현재 사용자의 user_id를 사용하여 데이터 생성
        course_data = course.model_dump()
        course_data['user_id'] = current_user.user_id
        
        db_course = TravelCourseLike(**course_data)
        db.add(db_course)
        db.commit()
        db.refresh(db_course)
        return db_course
    except IntegrityError as e:
        db.rollback()
        if "uq_user_content_like" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 해당 코스에 좋아요를 눌렀습니다."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="데이터베이스 제약조건 오류가 발생했습니다."
        )

@router.get("/", response_model=list[TravelCourseLikeResponse])
async def get_travel_course_likes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 현재 사용자의 좋아요 목록만 조회
    return db.query(TravelCourseLike).filter(
        TravelCourseLike.user_id == current_user.user_id
    ).all()

@router.delete("/{content_id}")
async def delete_travel_course_like(
    content_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 현재 사용자의 좋아요 삭제
    db_like = db.query(TravelCourseLike).filter(
        TravelCourseLike.user_id == current_user.user_id,
        TravelCourseLike.content_id == content_id
    ).first()
    
    if not db_like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 코스에 좋아요를 누르지 않았습니다."
        )
    
    db.delete(db_like)
    db.commit()
    return {"message": "좋아요가 취소되었습니다."}

@router.get("/check/{content_id}")
async def check_travel_course_like(
    content_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 현재 사용자의 특정 코스 좋아요 상태 확인
    like_exists = db.query(TravelCourseLike).filter(
        TravelCourseLike.user_id == current_user.user_id,
        TravelCourseLike.content_id == content_id
    ).first() is not None
    
    # 해당 코스의 총 좋아요 수
    total_likes = db.query(TravelCourseLike).filter(
        TravelCourseLike.content_id == content_id
    ).count()
    
    return {
        "liked": like_exists,
        "total": total_likes
    }
