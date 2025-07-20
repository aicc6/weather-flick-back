from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import google
from app.exception_handlers import register_exception_handlers
from app.logging_config import setup_logging
from app.middleware.activity_tracking import ActivityTrackingMiddleware
from app.routers import (
    advanced_travel,
    attractions,
    auth,
    categories,
    chatbot,
    config,
    contact,
    custom_travel,
    custom_travel_converter,
    destinations,
    destination_likes_saves,
    events,
    leisure_sports,
    likes_recommend,
    local_info,
    location,
    notifications,  # 2025-07-20: 알림 시스템 재활성화 - 문의 답변 알림 기능 추가
    personalized_recommendations,
    plan,
    realtime_travel,
    recommend_reviews,
    regions,
    review_likes,
    # recommendations,
    route_optimization,
    routes,
    system,
    travel_course,
    travel_course_like,
    travel_plans,
    travel_plan_share,
    weather,
)
from app.utils.redis_client import test_redis_connection

# 로깅 설정 초기화
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # Startup
    logger.info("Starting Weather Flick API...")
    
    # Redis 연결 테스트
    redis_connected = test_redis_connection()
    if redis_connected:
        logger.info("Redis 캐시 서버 연결 성공")
    else:
        logger.warning("Redis 캐시 서버 연결 실패 - 캐시 없이 실행됩니다")
    
    # OpenAI 초기화 상태 확인
    try:
        from app.services.openai_service import openai_service
        if openai_service.client:
            logger.info("OpenAI 서비스 초기화 성공")
        else:
            logger.warning("OpenAI 서비스 초기화 실패 - API 키를 확인하세요")
    except Exception as e:
        logger.error(f"OpenAI 서비스 확인 중 오류: {e}")
    
    yield
    
    # Shutdown (필요시 정리 작업 추가)
    logger.info("Shutting down Weather Flick API...")

app = FastAPI(
    title="Weather Flick API",
    description="Weather Flick Backend API with Authentication, Admin Management, and Local Information",
    version="1.0.0",
    lifespan=lifespan,
)

# 글로벌 예외 핸들러 등록
register_exception_handlers(app)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 사용자 활동 추적 미들웨어 추가
app.add_middleware(ActivityTrackingMiddleware)

# 라우터 포함 - 모든 라우터에 /api prefix 추가
app.include_router(contact.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(local_info.router, prefix="/api")
app.include_router(travel_plans.router, prefix="/api")
# app.include_router(recommendations.router, prefix="/api")
app.include_router(personalized_recommendations.router, prefix="/api")
app.include_router(recommend_reviews.router, prefix="/api")
app.include_router(destinations.router, prefix="/api")
app.include_router(destination_likes_saves.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(location.router, prefix="/api")
app.include_router(plan.router, prefix="/api")
app.include_router(chatbot.router, prefix="/api")
app.include_router(travel_course.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
app.include_router(likes_recommend.router, prefix="/api")
app.include_router(review_likes.router, prefix="/api")
app.include_router(travel_course_like.router, prefix="/api")
app.include_router(custom_travel.router, prefix="/api")
app.include_router(advanced_travel.router, prefix="/api")  # 고급 AI 여행 추천 API
app.include_router(custom_travel_converter.router, prefix="/api")
app.include_router(attractions.router, prefix="/api")
app.include_router(leisure_sports.router, prefix="/api")  # 레저 스포츠 API 라우터 추가
app.include_router(categories.router, prefix="/api")  # 카테고리 API 라우터 추가
app.include_router(regions.router)  # 지역 API 라우터 (prefix는 라우터에서 정의됨)
app.include_router(system.router, prefix="/api")
app.include_router(route_optimization.router, prefix="/api")  # 경로 최적화 API 라우터 추가
app.include_router(notifications.router, prefix="/api")  # 2025-07-20: 알림 시스템 재활성화
app.include_router(google.router, prefix="/api")
app.include_router(realtime_travel.router, prefix="/api")  # 실시간 여행 정보 API 라우터 추가
app.include_router(travel_plan_share.router, prefix="/api")  # 여행 계획 공유 API 라우터
app.include_router(travel_plan_share.shared_router, prefix="/api")  # 공유된 계획 조회 라우터

@app.get("/")
async def root():
    return {"message": "Weather Flick API is running!"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000, log_config=None)
