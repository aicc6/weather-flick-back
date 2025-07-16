"""사용자 활동 로깅 미들웨어"""

import json
import logging
from datetime import datetime

from fastapi import Request
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.database import SessionLocal
from app.models import UserActivityLog

logger = logging.getLogger(__name__)


class ActivityLoggerMiddleware(BaseHTTPMiddleware):
    """사용자 활동을 자동으로 로깅하는 미들웨어"""
    
    # 로깅할 엔드포인트 패턴
    TRACKED_ENDPOINTS = {
        "/api/travel-courses": "BROWSE_COURSES",
        "/api/travel-plans": "VIEW_PLANS",
        "/api/weather": "CHECK_WEATHER",
        "/api/destinations/search": "SEARCH",
        "/api/local": "BROWSE_LOCAL",
        "/api/recommend": "VIEW_RECOMMENDATIONS",
    }
    
    # 상세 로깅이 필요한 엔드포인트
    DETAILED_ENDPOINTS = {
        "/api/destinations/search",
        "/api/travel-courses/search",
        "/api/local/search",
    }

    async def dispatch(self, request: Request, call_next):
        # 응답 처리
        response = await call_next(request)
        
        # 로깅 대상 확인
        if not self._should_log(request):
            return response
        
        # 비동기로 활동 로깅
        try:
            await self._log_activity(request, response)
        except Exception as e:
            logger.error(f"활동 로깅 실패: {e}")
        
        return response
    
    def _should_log(self, request: Request) -> bool:
        """로깅 대상 여부 확인"""
        # API 호출만 로깅
        if not request.url.path.startswith("/api/"):
            return False
        
        # 인증된 사용자만 로깅
        if not hasattr(request.state, "user") or not request.state.user:
            return False
        
        # GET/POST 메서드만 로깅
        if request.method not in ["GET", "POST"]:
            return False
        
        return True
    
    async def _log_activity(self, request: Request, response: Response):
        """사용자 활동 로깅"""
        db: Session = SessionLocal()
        try:
            user = request.state.user
            path = request.url.path
            
            # 활동 타입 결정
            activity_type = self._get_activity_type(path)
            
            # 상세 정보 수집
            details = await self._collect_details(request, path)
            
            # 로그 생성
            log = UserActivityLog(
                user_id=user.id,
                activity_type=activity_type,
                resource_type=self._get_resource_type(path),
                details=details,
                created_at=datetime.utcnow()
            )
            
            db.add(log)
            db.commit()
            
        except Exception as e:
            logger.error(f"활동 로그 저장 실패: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _get_activity_type(self, path: str) -> str:
        """경로에서 활동 타입 추출"""
        # 정확한 매칭
        for endpoint, activity in self.TRACKED_ENDPOINTS.items():
            if path.startswith(endpoint):
                return activity
        
        # 기본 활동 타입
        if "search" in path:
            return "SEARCH"
        elif "view" in path or path.count("/") >= 4:  # 상세 조회
            return "VIEW_DETAIL"
        else:
            return "BROWSE"
    
    def _get_resource_type(self, path: str) -> str:
        """리소스 타입 추출"""
        parts = path.split("/")
        if len(parts) >= 3:
            return parts[2].upper()  # /api/[resource]/...
        return "UNKNOWN"
    
    async def _collect_details(self, request: Request, path: str) -> dict:
        """요청 상세 정보 수집"""
        details = {
            "path": path,
            "method": request.method,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 검색 쿼리 추출
        if path in self.DETAILED_ENDPOINTS:
            # Query parameters
            if request.query_params:
                query_params = dict(request.query_params)
                if "q" in query_params:
                    details["keyword"] = query_params["q"]
                if "region" in query_params:
                    details["region"] = query_params["region"]
                if "theme" in query_params:
                    details["theme"] = query_params["theme"]
            
            # Request body (POST 검색)
            if request.method == "POST":
                try:
                    body = await request.body()
                    if body:
                        data = json.loads(body)
                        if "keyword" in data:
                            details["keyword"] = data["keyword"]
                        if "filters" in data:
                            details["filters"] = data["filters"]
                except:
                    pass
        
        return details