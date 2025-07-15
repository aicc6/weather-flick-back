import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ReviewLike, ReviewLikeCreate, ReviewLikeResponse, User

router = APIRouter(prefix="/review-likes", tags=["review-likes"])

@router.post("/", response_model=ReviewLikeResponse)
async def like_review(
    like: ReviewLikeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 중복 체크
    exists = db.query(ReviewLike).filter_by(
        review_id=like.review_id, user_id=current_user.id, is_like=like.is_like
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="이미 처리된 상태입니다.")
    db_like = ReviewLike(
        review_id=like.review_id,
        user_id=current_user.id,
        is_like=like.is_like,
    )
    db.add(db_like)
    db.commit()
    db.refresh(db_like)
    return db_like

@router.delete("/{review_id}")
async def unlike_review(
    review_id: uuid.UUID,
    is_like: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    like = db.query(ReviewLike).filter_by(
        review_id=review_id, user_id=current_user.id, is_like=is_like
    ).first()
    if not like:
        raise HTTPException(status_code=404, detail="좋아요/싫어요 내역이 없습니다.")
    db.delete(like)
    db.commit()
    return {"success": True}

@router.get("/{review_id}")
async def get_review_likes(
    review_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_like = db.query(ReviewLike).filter_by(review_id=review_id, is_like=True).count()
    total_dislike = db.query(ReviewLike).filter_by(review_id=review_id, is_like=False).count()
    my_like = db.query(ReviewLike).filter_by(review_id=review_id, user_id=current_user.id, is_like=True).first() is not None
    my_dislike = db.query(ReviewLike).filter_by(review_id=review_id, user_id=current_user.id, is_like=False).first() is not None
    return {
        "total_like": total_like,
        "total_dislike": total_dislike,
        "my_like": my_like,
        "my_dislike": my_dislike,
    }
