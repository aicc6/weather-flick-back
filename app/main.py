from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import travel_course, notifications, auth
from app.middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware, CORS보안미들웨어

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Weather Flick API",
    description="Backend API for Weather Flick travel recommendation service",
    version="1.0.0",
)

# Add security middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
app.add_middleware(CORS보안미들웨어, production=False)

# Include routers
app.include_router(auth.router)
app.include_router(travel_course.router)
app.include_router(notifications.router)

@app.get("/")
async def root():
    return {"message": "Weather Flick API is running"}

@app.get("/health")
async def health_check():
    from app.database import get_db
    from sqlalchemy import text
    
    try:
        # 데이터베이스 연결 확인
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"Database connection failed: {str(e)}"
        return {
            "status": "unhealthy",
            "database": db_status,
            "service": "weather-flick-backend"
        }
    
    return {
        "status": "healthy",
        "database": db_status,
        "service": "weather-flick-backend"
    }
