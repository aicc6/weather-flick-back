"""맞춤 여행 추천을 여행 계획으로 변환하는 라우터"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    CustomTravelRecommendationRequest,
    CustomTravelRecommendationResponse,
    TravelPlan,
    TravelPlanStatus,
    User,
)
from app.services.region_service import RegionService
from app.utils import (
    create_error_response,
    create_standard_response,
)

router = APIRouter(
    prefix="/custom-travel",
    tags=["custom-travel"],
)


class ConvertToTravelPlanRequest(BaseModel):
    """맞춤 여행 추천을 여행 계획으로 변환하는 요청"""
    custom_recommendation: CustomTravelRecommendationResponse
    title: str
    description: str | None = None
    start_date: datetime
    budget: int | None = None
    participants: int | None = 1
    transportation: str | None = "자가용"
    start_location: str | None = None


@router.post("/convert-to-travel-plan", response_model=dict)
async def convert_to_travel_plan(
    request: ConvertToTravelPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """맞춤 여행 추천을 여행 계획 형식으로 변환하여 저장"""
    try:
        # 종료일 계산 (일수 - 1일)
        end_date = request.start_date + timedelta(days=len(request.custom_recommendation.days) - 1)

        # itinerary 형식으로 변환
        # 맞춤일정의 days 배열을 그대로 사용
        itinerary = {
            "days": [day.dict() for day in request.custom_recommendation.days],
            "weather_summary": request.custom_recommendation.weather_summary,
            "total_places": request.custom_recommendation.total_places,
            "recommendation_type": request.custom_recommendation.recommendation_type,
            "generated_at": datetime.now().isoformat()
        }

        # 새 여행 계획 생성
        db_plan = TravelPlan(
            user_id=current_user.id,
            title=request.title,
            description=request.description or f"{len(request.custom_recommendation.days)}일간의 맞춤 여행 일정",
            start_date=request.start_date,
            end_date=end_date,
            budget=request.budget,
            itinerary=itinerary,  # JSONB 필드에 저장
            participants=request.participants,
            transportation=request.transportation,
            start_location=request.start_location,
            weather_info=request.custom_recommendation.weather_summary,  # 날씨 요약 정보 저장
            status=TravelPlanStatus.PLANNING,  # 초기 상태는 계획 중
        )

        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)

        # 응답 데이터 구성
        response_data = {
            "plan_id": str(db_plan.plan_id),
            "title": db_plan.title,
            "description": db_plan.description,
            "start_date": db_plan.start_date.isoformat(),
            "end_date": db_plan.end_date.isoformat(),
            "status": db_plan.status.value,
            "created_at": db_plan.created_at.isoformat(),
        }

        return create_standard_response(
            success=True,
            data={
                "plan": response_data,
                "message": "맞춤 여행 추천이 여행 계획으로 성공적으로 변환되었습니다."
            }
        )

    except Exception as e:
        db.rollback()
        return create_error_response(
            code="CONVERSION_ERROR",
            message="여행 계획 변환에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )


@router.post("/recommendations-with-plan-format", response_model=dict)
async def get_recommendations_with_plan_format(
    request: CustomTravelRecommendationRequest,
    db: Session = Depends(get_db),
):
    """맞춤 여행 추천을 받으면서 동시에 여행 계획 형식으로도 변환하여 반환"""
    from app.routers.custom_travel import get_custom_travel_recommendations

    try:
        # 기존 맞춤 여행 추천 API 호출
        recommendation_response = await get_custom_travel_recommendations(request, db)

        # 여행 계획 형식으로 변환 준비
        start_date = datetime.now().date() + timedelta(days=7)  # 기본값: 일주일 후
        end_date = start_date + timedelta(days=request.days - 1)

        # 데이터베이스에서 지역 이름 조회 (프론트엔드 코드 매핑 사용)
        region_name = RegionService.get_region_name_by_frontend_code(db, request.region_code)

        # 여행 계획 형식
        travel_plan_format = {
            "title": f"{region_name} {request.days}일 맞춤 여행",
            "description": f"{request.who} 여행, {', '.join(request.styles)} 스타일",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "budget": None,  # 사용자가 나중에 설정
            "itinerary": {
                "days": [day.dict() for day in recommendation_response.days],
                "weather_summary": recommendation_response.weather_summary,
                "total_places": recommendation_response.total_places,
                "recommendation_type": recommendation_response.recommendation_type,
                "generated_at": datetime.now().isoformat()
            },
            "participants": 1 if request.who == "solo" else 2 if request.who == "couple" else 4,
            "transportation": "자가용",  # 기본값
            "start_location": region_name,
            "weather_info": recommendation_response.weather_summary,
            "status": "PLANNING"
        }

        return create_standard_response(
            success=True,
            data={
                "recommendation": recommendation_response.dict(),
                "travel_plan_format": travel_plan_format,
                "can_save_as_plan": True,
                "message": "맞춤 여행 추천과 여행 계획 형식을 함께 반환합니다."
            }
        )

    except Exception as e:
        return create_error_response(
            code="RECOMMENDATION_ERROR",
            message="맞춤 여행 추천 생성에 실패했습니다.",
            details=[{"field": "general", "message": str(e)}],
        )
