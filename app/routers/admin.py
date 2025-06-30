from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.database import get_db
from app.models import (
    User, UserActivity, UserRole, TravelPlan, Destination, Review,
    DashboardStats, UserAnalytics, SystemMetrics, ContentStats,
    StandardResponse
)
from app.auth import get_current_super_admin_user
from app.services.weather_service import weather_service
from app.services.kma_weather_service import kma_weather_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

def create_standard_response(success: bool, data=None, error=None, pagination=None):
    """표준 응답 형식 생성"""
    return {
        "success": success,
        "data": data,
        "error": error,
        "pagination": pagination,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.get("/dashboard/stats", response_model=dict)
async def get_dashboard_stats(
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """관리자 대시보드 통계 정보"""
    try:
        now = datetime.utcnow()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # 실시간 메트릭
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        
        # 여행 계획 통계 (테이블이 존재하는 경우)
        try:
            total_travel_plans = db.query(TravelPlan).count()
            active_travel_plans = db.query(TravelPlan).filter(
                TravelPlan.status.in_(["draft", "confirmed"])
            ).count()
        except:
            total_travel_plans = 0
            active_travel_plans = 0

        # 여행지 통계 (테이블이 존재하는 경우)
        try:
            total_destinations = db.query(Destination).count()
            active_destinations = db.query(Destination).filter(
                Destination.status == "active"
            ).count()
        except:
            total_destinations = 0
            active_destinations = 0

        realtime_metrics = {
            "active_users": active_users,
            "server_load": 67.5,  # 추후 실제 시스템 메트릭 연동
            "api_response_time": 120,
            "error_rate": 0.02
        }

        # 일일 통계
        new_users_today = db.query(User).filter(
            func.date(User.created_at) == today
        ).count()
        
        daily_stats = {
            "new_users": new_users_today,
            "total_recommendations": total_travel_plans,
            "weather_queries": 0,  # 추후 날씨 쿼리 로그 테이블 추가 시 연동
            "avg_session_time": 342
        }

        # 알림 (예시)
        alerts = []
        if active_users > 1000:
            alerts.append({
                "type": "info",
                "severity": "info",
                "message": f"현재 활성 사용자 수: {active_users}명"
            })

        dashboard_data = {
            "realtime_metrics": realtime_metrics,
            "daily_stats": daily_stats,
            "alerts": alerts
        }

        return create_standard_response(
            success=True,
            data=dashboard_data
        )
        
    except Exception as e:
        return create_standard_response(
            success=False,
            error={
                "code": "DASHBOARD_ERROR",
                "message": "대시보드 통계 조회에 실패했습니다.",
                "details": [{"field": "general", "message": str(e)}]
            }
        )

@router.get("/analytics/users", response_model=dict)
async def get_user_analytics(
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """사용자 분석 데이터"""
    try:
        now = datetime.utcnow()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # 기본 사용자 통계
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        
        new_users_today = db.query(User).filter(
            func.date(User.created_at) == today
        ).count()
        
        new_users_week = db.query(User).filter(
            User.created_at >= week_ago
        ).count()
        
        new_users_month = db.query(User).filter(
            User.created_at >= month_ago
        ).count()

        # 성장률 계산 (간단한 예시)
        previous_month_users = db.query(User).filter(
            User.created_at >= month_ago - timedelta(days=30),
            User.created_at < month_ago
        ).count()
        
        growth_rate = ((new_users_month - previous_month_users) / max(previous_month_users, 1)) * 100

        user_analytics_data = {
            "total_users": total_users,
            "active_users": active_users,
            "new_users_today": new_users_today,
            "new_users_this_week": new_users_week,
            "new_users_this_month": new_users_month,
            "user_growth_rate": round(growth_rate, 2),
            "retention_rate": 85.5  # 추후 실제 리텐션 계산 로직 추가
        }

        return create_standard_response(
            success=True,
            data=user_analytics_data
        )
        
    except Exception as e:
        return create_standard_response(
            success=False,
            error={
                "code": "ANALYTICS_ERROR",
                "message": "사용자 분석 데이터 조회에 실패했습니다.",
                "details": [{"field": "general", "message": str(e)}]
            }
        )

@router.get("/dashboard")
async def get_admin_dashboard(
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """관리자 대시보드 메인 정보 (기존 호환성 유지)"""
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
