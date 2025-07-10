from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth import get_current_user
from app.models import RecommendLike, RecommendLikeCreate, RecommendLikeResponse, User

router = APIRouter(
    prefix="/likes-recommend",
    tags=["likes-recommend"]
)

@router.post("/", response_model=RecommendLikeResponse)
async def like_course(
    like: RecommendLikeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 중복 체크
    exists = db.query(RecommendLike).filter_by(course_id=like.course_id, user_id=current_user.id).first()
    if exists:
        raise HTTPException(status_code=400, detail="이미 좋아요를 눌렀습니다.")
    db_like = RecommendLike(course_id=like.course_id, user_id=current_user.id)
    db.add(db_like)
    db.commit()
    db.refresh(db_like)
    return db_like

@router.delete("/{course_id}", status_code=204)
async def unlike_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    like = db.query(RecommendLike).filter_by(course_id=course_id, user_id=current_user.id).first()
    if not like:
        raise HTTPException(status_code=404, detail="좋아요를 누르지 않았습니다.")
    db.delete(like)
    db.commit()
    return

@router.get("/course/{course_id}")
async def get_course_likes(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = db.query(RecommendLike).filter_by(course_id=course_id).count()
    liked = db.query(RecommendLike).filter_by(course_id=course_id, user_id=current_user.id).first() is not None
    return {"total": total, "liked": liked}

@router.get("/my", response_model=List[RecommendLikeResponse])
async def get_my_likes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(RecommendLike).filter_by(user_id=current_user.id).all()
