from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TravelCourseLike
from app.schemas import TravelCourseLikeCreate, TravelCourseLikeResponse

router = APIRouter(prefix="/travel-course-likes", tags=["travel_course_likes"])

@router.post("/", response_model=TravelCourseLikeResponse)
async def create_travel_course_like(course: TravelCourseLikeCreate, db: Session = Depends(get_db)):
    db_course = TravelCourseLike(**course.model_dump())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course
