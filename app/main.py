from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import travel_course, travel_course_like
from app.database import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Weather Flick API",
    description="Backend API for Weather Flick travel recommendation service",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(travel_course.router)
app.include_router(travel_course_like.router)

@app.get("/")
async def root():
    return {"message": "Weather Flick API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}