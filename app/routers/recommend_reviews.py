from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.auth import get_current_user
from app.models import RecommendReview, RecommendReviewCreate, RecommendReviewResponse, User
from fastapi import Query
import uuid

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
        parent_id=review.parent_id,  # 답글용
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

@router.get("/course/{course_id}", response_model=List[RecommendReviewResponse])
async def get_recommend_reviews_by_course(
    course_id: int,
    parent_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(RecommendReview).filter(RecommendReview.course_id == course_id)
    if parent_id is None:
        query = query.filter(RecommendReview.parent_id.is_(None))
    else:
        query = query.filter(RecommendReview.parent_id == parent_id)
    reviews = query.order_by(RecommendReview.created_at.asc()).all()
    return reviews

@router.get("/course/{course_id}/tree", response_model=List[RecommendReviewResponse])
async def get_recommend_reviews_tree(
    course_id: int,
    db: Session = Depends(get_db),
):
    all_reviews = db.query(RecommendReview).filter(RecommendReview.course_id == course_id).all()
    review_dict = {str(r.id): r for r in all_reviews}
    # children 필드 초기화
    for r in all_reviews:
        r.children = []
    tree = []
    for review in all_reviews:
        if review.parent_id is None:
            tree.append(review)
        else:
            parent = review_dict.get(str(review.parent_id))
            if parent:
                parent.children.append(review)
    return tree
