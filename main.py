from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import weather, auth, kma_weather, local_info, naver_map, travel_plans, recommendations, destinations, events
from app.exception_handlers import register_exception_handlers
from app.logging_config import setup_logging

# 로깅 설정 초기화
logger = setup_logging()

app = FastAPI(
    title="Weather Flick API",
    description="Weather Flick Backend API with Authentication, Admin Management, Local Information, and Naver Maps",
    version="1.0.0"
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

# 라우터 포함
app.include_router(auth.router)
app.include_router(weather.router)
app.include_router(kma_weather.router)
app.include_router(local_info.router)
app.include_router(naver_map.router)
app.include_router(travel_plans.router)
app.include_router(recommendations.router)
app.include_router(destinations.router)
app.include_router(events.router)

@app.get("/")
async def root():
    return {"message": "Weather Flick API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
