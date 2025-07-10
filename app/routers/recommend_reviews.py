from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth import get_current_user
from app.models import RecommendReview, RecommendReviewCreate, RecommendReviewResponse, User

router = APIRouter(
    prefix="/recommend-reviews",
    tags=["recommend-reviews"]
)

@router.post("/", response_model=RecommendReviewResponse)
async def create_recommend_review(
    review: RecommendReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_review = RecommendReview(
        course_id=review.course_id,
        user_id=current_user.id,
        nickname=current_user.nickname,
        rating=review.rating,
        content=review.content,
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

@router.get("/course/{course_id}", response_model=List[RecommendReviewResponse])
async def get_recommend_reviews_by_course(
    course_id: int,
    db: Session = Depends(get_db),
):
    reviews = db.query(RecommendReview).filter(RecommendReview.course_id == course_id).order_by(RecommendReview.created_at.desc()).all()
    return reviews
