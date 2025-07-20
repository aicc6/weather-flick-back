# app/routers/travel_courses.py
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from app.database import get_db
from app.models import TravelCourse, TravelCourseLike, User
from app.schema_models.travel_course import TravelCourseListResponse, TravelCourseDetailResponse
from app.schema_models.travel_course import TravelCourseResponse
from app.schemas.travel_course_like import TravelCourseLikeCreate, TravelCourseLikeResponse
from app.auth import get_current_user_optional, get_current_user

router = APIRouter(prefix="/travel-courses", tags=["travel-courses"])

@router.get("/", response_model=TravelCourseListResponse)
async def get_travel_courses(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    limit: int = Query(10, ge=1, le=50, description="페이지당 항목 수 (최대 50)"),
    region_code: Optional[int] = Query(None, description="지역 코드 (숫자 ID, 예: 1=서울, 6=부산)"),
    liked_only: Optional[bool] = Query(False, description="좋아요한 코스만 조회 (로그인 필요)")
) -> TravelCourseListResponse:
    offset = (page - 1) * limit
    query = db.query(TravelCourse)
    
    # 좋아요 필터링 (로그인된 사용자만)
    if liked_only:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="좋아요 필터를 사용하려면 로그인이 필요합니다."
            )
        # JOIN을 사용하여 좋아요한 코스만 조회
        query = query.join(TravelCourseLike).filter(
            TravelCourseLike.user_id == current_user.user_id
        )
    
    # 지역 필터링 (숫자 ID 기반)
    if region_code:
        query = query.filter(TravelCourse.region_code == str(region_code))
    
    total_count = query.count()  # 전체 개수
    courses = query.offset(offset).limit(limit).all()
    
    # 로그인된 사용자가 있는 경우 좋아요 정보 조회
    user_likes = set()
    if current_user:
        liked_course_ids = db.query(TravelCourseLike.content_id).filter(
            TravelCourseLike.user_id == current_user.user_id
        ).all()
        user_likes = {like.content_id for like in liked_course_ids}
    
    # ORM 객체를 Pydantic 모델로 변환 (좋아요 정보 포함)
    course_models = []
    for course in courses:
        try:
            course_dict = TravelCourseResponse.model_validate(course, from_attributes=True).model_dump()
            
            # 좋아요 정보 추가 (로그인된 사용자만)
            if current_user:
                course_dict['is_liked'] = course.content_id in user_likes
                # 해당 코스의 총 좋아요 수도 추가
                total_likes = db.query(TravelCourseLike).filter(
                    TravelCourseLike.content_id == course.content_id
                ).count()
                course_dict['total_likes'] = total_likes
            else:
                course_dict['is_liked'] = None  # 비로그인 사용자
                course_dict['total_likes'] = None
                
            course_models.append(course_dict)
        except Exception as e:
            # 로그는 운영 환경에서는 적절한 로깅 시스템으로 대체 필요
            raise HTTPException(status_code=500, detail="데이터 변환 중 오류가 발생했습니다")
    
    return TravelCourseListResponse(courses=course_models, totalCount=total_count)

@router.get("/{course_id}", response_model=TravelCourseDetailResponse)
async def get_travel_course_detail(
    course_id: str,
    db: Session = Depends(get_db)
) -> TravelCourseDetailResponse:
    """여행 코스 상세 정보 조회"""
    # 복합 기본키 대응: content_id로만 조회하되 첫 번째 결과 사용
    course = db.query(TravelCourse).filter(TravelCourse.content_id == course_id).first()

    if not course:
        raise HTTPException(status_code=404, detail="여행 코스를 찾을 수 없습니다")

    # ORM 객체를 Pydantic 모델로 변환
    return TravelCourseDetailResponse.model_validate(course, from_attributes=True)

@router.get("/{course_id}/google-review")
async def get_google_review_for_course(course_id: str, db: Session = Depends(get_db)):
    course = db.query(TravelCourse).filter(TravelCourse.content_id == course_id).first()
    if not course or not course.place_id:
        raise HTTPException(status_code=404, detail="place_id가 없습니다")
    from app.services.google_places_service import GooglePlacesService
    service = GooglePlacesService()
    return await service.get_place_reviews_and_rating(course.place_id)

@router.put("/{course_id}/likes", response_model=dict)
async def toggle_travel_course_like(
    course_id: str,
    course_data: TravelCourseLikeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """여행 코스 좋아요 토글 (추가/삭제)"""
    
    # 기존 좋아요 확인
    existing_like = db.query(TravelCourseLike).filter(
        TravelCourseLike.user_id == current_user.user_id,
        TravelCourseLike.content_id == course_id
    ).first()
    
    if existing_like:
        # 좋아요 취소
        db.delete(existing_like)
        db.commit()
        
        # 총 좋아요 수 계산
        total_likes = db.query(TravelCourseLike).filter(
            TravelCourseLike.content_id == course_id
        ).count()
        
        return {
            "message": "좋아요가 취소되었습니다.",
            "liked": False,
            "total_likes": total_likes
        }
    else:
        # 좋아요 추가
        try:
            course_like_data = course_data.model_dump()
            course_like_data['user_id'] = current_user.user_id
            course_like_data['content_id'] = course_id  # URL 파라미터 사용
            
            db_like = TravelCourseLike(**course_like_data)
            db.add(db_like)
            db.commit()
            db.refresh(db_like)
            
            # 총 좋아요 수 계산
            total_likes = db.query(TravelCourseLike).filter(
                TravelCourseLike.content_id == course_id
            ).count()
            
            return {
                "message": "좋아요가 추가되었습니다.",
                "liked": True,
                "total_likes": total_likes
            }
            
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
