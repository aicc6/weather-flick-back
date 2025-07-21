from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import google
from app.exception_handlers import register_exception_handlers
from app.logging_config import setup_logging
from app.middleware.activity_tracking import ActivityTrackingMiddleware
from app.middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware
from app.middleware.error_handling import ErrorHandlingMiddleware, TimeoutMiddleware, HealthCheckMiddleware
from app.middleware.monitoring import MonitoringMiddleware, MetricsEndpoint, collect_system_metrics
from app.middleware.json_encoder import setup_json_encoding
from app.middleware.timezone_middleware import setup_timezone_middleware
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
    # notifications,  # 2025-07-20: Notification system reactivation - Added inquiry response notification feature (temporarily disabled)
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
    travel_course_saves,
    travel_plans,
    travel_plan_share,
    weather,
)
from app.utils.redis_client import test_redis_connection

# Initialize logging configuration
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    logger.info("Starting Weather Flick API...")
    
    # Redis connection test
    redis_connected = test_redis_connection()
    if redis_connected:
        logger.info("Redis cache server connection successful")
    else:
        logger.warning("Redis cache server connection failed - running without cache")
    
    # OpenAI initialization status check
    try:
        from app.services.openai_service import openai_service
        if openai_service.client:
            logger.info("OpenAI service initialization successful")
        else:
            logger.warning("OpenAI service initialization failed - check API key")
    except Exception as e:
        logger.error(f"Error checking OpenAI service: {e}")
    
    # Start monitoring background task
    import asyncio
    monitoring_task = asyncio.create_task(collect_system_metrics())
    logger.info("System monitoring background task started")
    
    yield
    
    # Shutdown (cleanup)
    monitoring_task.cancel()
    logger.info("Shutting down Weather Flick API...")

app = FastAPI(
    title="Weather Flick API",
    description="Weather Flick Backend API with Authentication, Admin Management, and Local Information",
    version="1.0.0",
    lifespan=lifespan,
)

# Register global exception handlers
register_exception_handlers(app)

# Add middleware (order matters: external → internal)
app.add_middleware(ErrorHandlingMiddleware)  # Top-level error handling
app.add_middleware(TimeoutMiddleware, timeout_seconds=30)  # Timeout handling
app.add_middleware(HealthCheckMiddleware)  # Health check handling
app.add_middleware(SecurityHeadersMiddleware)  # Security headers
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)  # Rate limiting

# CORS middleware configuration (modified for development environment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174", 
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Add complete timezone middleware
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware

class TimezoneMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, default_timezone: str = "Asia/Seoul"):
        super().__init__(app)
        self.default_timezone = default_timezone
    
    async def dispatch(self, request, call_next):
        # Collect client timezone information
        client_timezone = self._extract_client_timezone(request)
        
        # Store timezone information in request state
        request.state.client_timezone = client_timezone
        request.state.server_timezone = "UTC"
        request.state.recommended_timezone = self.default_timezone
        
        # Execute next middleware/router
        response = await call_next(request)
        
        # Add timezone information to response headers
        self._add_timezone_headers(response, client_timezone)
        
        return response
    
    def _extract_client_timezone(self, request):
        # Check X-Client-Timezone header
        client_timezone = request.headers.get("X-Client-Timezone")
        if client_timezone:
            return client_timezone
        
        # Infer from Accept-Language
        accept_language = request.headers.get("Accept-Language", "")
        if "ko" in accept_language.lower():
            return "Asia/Seoul"
        
        return self.default_timezone
    
    def _add_timezone_headers(self, response, client_timezone):
        # Server timezone information
        response.headers["X-Server-Timezone"] = "UTC"
        response.headers["X-Server-Time"] = datetime.now(timezone.utc).isoformat()
        
        # Client recommended timezone
        response.headers["X-Recommended-Timezone"] = self.default_timezone
        response.headers["X-Detected-Client-Timezone"] = client_timezone
        
        # Time format information
        response.headers["X-Datetime-Format"] = "ISO8601"
        response.headers["X-Timezone-Note"] = "All server times are in UTC. Convert to local timezone for display."

app.add_middleware(TimezoneMiddleware, default_timezone="Asia/Seoul")
logger.info("Complete timezone middleware has been added.")

# JSON 직렬화 설정 적용
setup_json_encoding(app)

# 모니터링 및 사용자 활동 추적 미들웨어 추가
app.add_middleware(MonitoringMiddleware)  # 모니터링 (성능 메트릭)
app.add_middleware(ActivityTrackingMiddleware)  # 사용자 활동 추적

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
app.include_router(travel_course_saves.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
app.include_router(likes_recommend.router, prefix="/api")
app.include_router(review_likes.router, prefix="/api")
app.include_router(custom_travel.router, prefix="/api")
app.include_router(advanced_travel.router, prefix="/api")  # 고급 AI 여행 추천 API
app.include_router(custom_travel_converter.router, prefix="/api")
app.include_router(attractions.router, prefix="/api")
app.include_router(leisure_sports.router, prefix="/api")  # 레저 스포츠 API 라우터 추가
app.include_router(categories.router, prefix="/api")  # 카테고리 API 라우터 추가
app.include_router(regions.router)  # 지역 API 라우터 (prefix는 라우터에서 정의됨)
app.include_router(system.router, prefix="/api")
app.include_router(route_optimization.router, prefix="/api")  # 경로 최적화 API 라우터 추가
# app.include_router(notifications.router, prefix="/api")  # 2025-07-20: 알림 시스템 재활성화 (임시 비활성화)
app.include_router(auth.router, prefix="/api")  # 인증 API 라우터
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
