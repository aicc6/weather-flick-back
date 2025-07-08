from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.exception_handlers import register_exception_handlers
from app.logging_config import setup_logging
from app.routers import (
    auth,
    chatbot,
    config,
    destinations,
    events,
    kma_weather,
    local_info,
    location,
    naver_map,
    plan,
    recommendations,
    travel_plans,
    weather,
)

# 로깅 설정 초기화
logger = setup_logging()

app = FastAPI(
    title="Weather Flick API",
    description="Weather Flick Backend API with Authentication, Admin Management, Local Information, and Naver Maps",
    version="1.0.0",
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

# 라우터 포함 - 모든 라우터에 /api prefix 추가
app.include_router(auth.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(kma_weather.router, prefix="/api")
app.include_router(local_info.router, prefix="/api")
app.include_router(naver_map.router, prefix="/api")
app.include_router(travel_plans.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(destinations.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(location.router, prefix="/api")
app.include_router(plan.router, prefix="/api")
app.include_router(chatbot.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Weather Flick API is running!"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000, log_config=None)
