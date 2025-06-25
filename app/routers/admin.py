from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.database import get_db
from app.models import User, UserActivity, UserRole
from app.auth import get_current_super_admin_user
from app.services.weather_service import weather_service
from app.services.kma_weather_service import kma_weather_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

@router.get("/dashboard")
async def get_admin_dashboard(
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """관리자 대시보드 메인 정보"""
    now = datetime.utcnow()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # 사용자 통계
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    new_users_today = db.query(User).filter(
        func.date(User.created_at) == today
    ).count()
    new_users_week = db.query(User).filter(
        User.created_at >= week_ago
    ).count()

    # 역할별 사용자 수
    role_stats = db.query(
        User.role,
        func.count(User.id).label('count')
    ).group_by(User.role).all()

    role_distribution = {role.value: count for role, count in role_stats}

    # 최근 활동
    recent_activities = db.query(UserActivity).order_by(
        desc(UserActivity.created_at)
    ).limit(10).all()

    # 로그인 통계
    today_logins = db.query(User).filter(
        User.last_login >= today
    ).count()

    this_week_logins = db.query(User).filter(
        User.last_login >= week_ago
    ).count()

    this_month_logins = db.query(User).filter(
        User.last_login >= month_ago
    ).count()

    # 활동 타입별 통계
    activity_stats = db.query(
        UserActivity.activity_type,
        func.count(UserActivity.id).label('count')
    ).group_by(UserActivity.activity_type).all()

    activity_distribution = {activity_type: count for activity_type, count in activity_stats}

    return {
        "user_stats": {
            "total_users": total_users,
            "active_users": active_users,
            "new_users_today": new_users_today,
            "new_users_week": new_users_week,
            "role_distribution": role_distribution
        },
        "login_stats": {
            "today_logins": today_logins,
            "this_week_logins": this_week_logins,
            "this_month_logins": this_month_logins
        },
        "activity_stats": {
            "activity_distribution": activity_distribution
        },
        "recent_activities": [
            {
                "id": activity.id,
                "user_id": activity.user_id,
                "activity_type": activity.activity_type,
                "description": activity.description,
                "ip_address": activity.ip_address,
                "created_at": activity.created_at
            }
            for activity in recent_activities
        ]
    }

@router.get("/users/analytics")
async def get_user_analytics(
    period: str = Query("week", description="Period: day, week, month"),
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """사용자 분석 데이터"""
    now = datetime.utcnow()

    if period == "day":
        start_date = now - timedelta(days=1)
        group_by = func.date(User.created_at)
    elif period == "week":
        start_date = now - timedelta(days=7)
        group_by = func.date(User.created_at)
    elif period == "month":
        start_date = now - timedelta(days=30)
        group_by = func.date(User.created_at)
    else:
        raise HTTPException(status_code=400, detail="Invalid period")

    # 일별 가입자 수
    daily_registrations = db.query(
        group_by.label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(group_by).order_by(group_by).all()

    # 역할별 가입자 수
    role_registrations = db.query(
        User.role,
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(User.role).all()

    return {
        "period": period,
        "daily_registrations": [
            {"date": str(date), "count": count}
            for date, count in daily_registrations
        ],
        "role_registrations": [
            {"role": role.value, "count": count}
            for role, count in role_registrations
        ]
    }

@router.get("/system/health")
async def get_system_health(
    current_admin: User = Depends(get_current_super_admin_user)
):
    """시스템 상태 확인"""
    health_status = {
        "database": "healthy",
        "weather_api": "unknown",
        "kma_api": "unknown",
        "overall": "healthy"
    }

    # WeatherAPI 상태 확인
    try:
        await weather_service.get_current_weather("Seoul", "KR")
        health_status["weather_api"] = "healthy"
    except Exception as e:
        health_status["weather_api"] = f"error: {str(e)}"
        health_status["overall"] = "degraded"

    # 기상청 API 상태 확인
    try:
        await kma_weather_service.get_current_weather(60, 127)  # 서울
        health_status["kma_api"] = "healthy"
    except Exception as e:
        health_status["kma_api"] = f"error: {str(e)}"
        health_status["overall"] = "degraded"

    return health_status

@router.get("/users/search")
async def search_users(
    q: str = Query(..., description="Search query"),
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """사용자 검색"""
    users = db.query(User).filter(
        (User.email.contains(q)) |
        (User.username.contains(q)) |
        (User.bio.contains(q))
    ).limit(20).all()

    return [
        {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role.value,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "last_login": user.last_login,
            "created_at": user.created_at
        }
        for user in users
    ]

@router.get("/users/{user_id}/activities")
async def get_user_activities(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """특정 사용자의 활동 로그"""
    # 사용자 존재 확인
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    activities = db.query(UserActivity).filter(
        UserActivity.user_id == user_id
    ).order_by(
        desc(UserActivity.created_at)
    ).offset(skip).limit(limit).all()

    return [
        {
            "id": activity.id,
            "activity_type": activity.activity_type,
            "description": activity.description,
            "ip_address": activity.ip_address,
            "user_agent": activity.user_agent,
            "created_at": activity.created_at
        }
        for activity in activities
    ]

@router.post("/users/{user_id}/verify")
async def verify_user(
    user_id: int,
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """사용자 이메일 인증 (관리자 수동)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    db.commit()

    return {"message": "User verified successfully"}

@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """사용자 계정 활성화"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    db.commit()

    return {"message": "User activated successfully"}

@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """사용자 계정 비활성화"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 자기 자신은 비활성화할 수 없음
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user.is_active = False
    db.commit()

    return {"message": "User deactivated successfully"}

@router.post("/users/{user_id}/promote")
async def promote_user(
    user_id: int,
    role: UserRole = Body(..., embed=True),
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """사용자 역할 승격"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role
    db.commit()

    return {"message": f"User promoted to {role.value}"}

@router.get("/logs/errors")
async def get_error_logs(
    skip: int = 0,
    limit: int = 100,
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """에러 로그 조회 (시스템 로그)"""
    # 실제 구현에서는 로그 파일이나 로그 데이터베이스를 사용
    # 여기서는 예시로 빈 배열 반환
    return {
        "message": "Error logs feature not implemented yet",
        "logs": []
    }

@router.get("/system/info")
async def get_system_info(
    current_admin: User = Depends(get_current_super_admin_user)
):
    """시스템 정보"""
    import platform

    try:
        import psutil
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage('/').percent
        }
    except ImportError:
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": "N/A",
            "memory_total": "N/A",
            "memory_available": "N/A",
            "disk_usage": "N/A",
            "note": "psutil not available"
        }
