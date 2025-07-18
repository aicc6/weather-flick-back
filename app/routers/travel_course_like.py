
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TravelCourseLike
from app.schemas import TravelCourseLikeCreate, TravelCourseLikeResponse

router = APIRouter(prefix="/travel-course-likes", tags=["travel_course_likes"])

@router.post("/", response_model=TravelCourseLikeResponse)
async def create_travel_course_like(
    course: TravelCourseLikeCreate, db: Session = Depends(get_db)
):
    db_course = TravelCourseLike(**course.model_dump())  # 또는 .dict() for Pydantic v1
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

@router.get("/", response_model=list[TravelCourseLikeResponse])
async def get_travel_course_likes(
    user_id: int | None = None, db: Session = Depends(get_db)
):
    query = db.query(TravelCourseLike)
    if user_id is not None:
        query = query.filter(TravelCourseLike.user_id == user_id)
    return query.all()
