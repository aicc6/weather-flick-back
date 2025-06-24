from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import weather, auth, kma_weather
from app.database import engine
from app.models import Base

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Weather Flick API",
    description="Weather Flick Backend API with Authentication",
    version="1.0.0"
)

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

@app.get("/")
async def root():
    return {"message": "Weather Flick API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
