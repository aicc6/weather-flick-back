"""사용자 활동 추적 미들웨어"""

import json
import time
import uuid
from uuid import UUID
from typing import Optional
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.database import SessionLocal
from app.services.user_behavior_service import get_user_behavior_service
from app.auth import verify_token
from jose import JWTError
from app.config import settings


class ActivityTrackingMiddleware(BaseHTTPMiddleware):
    """사용자 활동을 자동으로 추적하는 미들웨어"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # 추적할 엔드포인트 패턴 정의
        self.tracked_patterns = {
            # 여행지 조회
            r"/destinations/(\w+)": "destination_view",
            r"/attractions/(\w+)": "destination_view",
            r"/restaurants/(\w+)": "destination_view",
            r"/accommodations/(\w+)": "destination_view",
            r"/cultural-facilities/(\w+)": "destination_view",
            r"/shopping/(\w+)": "destination_view",
            
            # 여행 계획
            r"/travel-plans": "plan_created",
            r"/travel-plans/(\w+)": "plan_view",
            
            # 리뷰 및 평가
            r"/reviews": "review_created",
            r"/likes": "like_added",
            r"/bookmarks": "bookmark_added",
            
            # 검색
            r"/search": "search_performed",
            
            # 추천
            r"/recommendations": "recommendation_viewed",
            r"/custom-travel/recommendations": "custom_recommendation_viewed",
        }
        
        # 페이지 타입 매핑
        self.page_types = {
            "/": "home",
            "/destinations": "destination_list",
            "/travel-plans": "travel_plan_list",
            "/profile": "profile",
            "/search": "search",
        }
    
    async def dispatch(self, request: Request, call_next):
        """미들웨어 처리"""
        
        # 시작 시간 기록
        start_time = time.time()
        
        # 사용자 정보 추출
        user_id = await self._get_user_id(request)
        
        # 세션 ID 생성/추출
        session_id = request.cookies.get("session_id") or str(uuid.uuid4())
        
        # 요청 처리
        response = await call_next(request)
        
        # 처리 시간 계산
        duration = time.time() - start_time
        
        # 활동 추적 (비동기 처리)
        if user_id and response.status_code < 400:
            await self._track_activity(
                request, response, user_id, session_id, duration
            )
        
        # 세션 쿠키 설정
        if "session_id" not in request.cookies:
            response.set_cookie(
                key="session_id",
                value=session_id,
                max_age=30 * 24 * 60 * 60,  # 30일
                httponly=True,
                samesite="lax"
            )
        
        return response
    
    async def _get_user_id(self, request: Request) -> Optional[UUID]:
        """요청에서 사용자 ID 추출"""
        
        # Authorization 헤더에서 토큰 추출
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        
        try:
            # 토큰 검증 및 디코드
            credentials_exception = Exception("Could not validate credentials")
            payload = verify_token(token, credentials_exception)
            user_id_str = payload.get("user_id") or payload.get("sub")
            if user_id_str:
                return UUID(user_id_str)
        except Exception:
            pass
        
        return None
    
    async def _track_activity(
        self,
        request: Request,
        response: Response,
        user_id: UUID,
        session_id: str,
        duration: float
    ):
        """활동 추적"""
        
        try:
            # 데이터베이스 세션 생성
            db = SessionLocal()
            behavior_service = get_user_behavior_service(db)
            
            # URL 경로
            path = request.url.path
            method = request.method
            
            # 활동 타입 결정
            activity_type = self._determine_activity_type(path, method)
            
            if activity_type:
                # 활동 데이터 수집
                activity_data = {
                    "path": path,
                    "method": method,
                    "session_id": session_id,
                    "duration": duration,
                    "timestamp": datetime.now().isoformat()
                }
                
                # 추가 데이터 수집
                if activity_type == "destination_view":
                    # URL에서 destination_id 추출
                    parts = path.split("/")
                    if len(parts) >= 3:
                        activity_data["destination_id"] = parts[-1]
                
                elif activity_type == "search_performed":
                    # 검색어 추출
                    query_params = dict(request.query_params)
                    activity_data["query"] = query_params.get("q", "")
                    activity_data["filters"] = query_params
                
                elif activity_type == "plan_created" and method == "POST":
                    # 요청 본문에서 지역 정보 추출 (가능한 경우)
                    try:
                        body = await request.body()
                        if body:
                            data = json.loads(body)
                            activity_data["region"] = data.get("region")
                            activity_data["days"] = data.get("days")
                    except:
                        pass
                
                # 페이지 뷰 추적
                if method == "GET" and duration > 1.0:  # 1초 이상 체류
                    page_type = self._get_page_type(path)
                    if page_type:
                        await behavior_service.track_user_activity(
                            user_id=user_id,
                            activity_type="page_view",
                            activity_data={
                                **activity_data,
                                "page_type": page_type,
                                "duration": duration
                            },
                            request=request
                        )
                
                # 주요 활동 추적
                await behavior_service.track_user_activity(
                    user_id=user_id,
                    activity_type=activity_type,
                    activity_data=activity_data,
                    request=request
                )
            
            # 데이터베이스 세션 닫기
            db.close()
            
        except Exception as e:
            # 에러가 발생해도 메인 요청 처리에는 영향 없음
            print(f"Activity tracking error: {str(e)}")
    
    def _determine_activity_type(self, path: str, method: str) -> Optional[str]:
        """URL 패턴과 메서드를 기반으로 활동 타입 결정"""
        
        import re
        
        for pattern, activity_type in self.tracked_patterns.items():
            if re.match(pattern, path):
                # POST 메서드인 경우 타입 조정
                if method == "POST" and activity_type.endswith("_view"):
                    return activity_type.replace("_view", "_created")
                return activity_type
        
        return None
    
    def _get_page_type(self, path: str) -> Optional[str]:
        """페이지 타입 결정"""
        
        # 정확한 매칭
        if path in self.page_types:
            return self.page_types[path]
        
        # 패턴 매칭
        if path.startswith("/destinations"):
            return "destination_detail" if len(path.split("/")) > 2 else "destination_list"
        elif path.startswith("/travel-plans"):
            return "travel_plan_detail" if len(path.split("/")) > 2 else "travel_plan_list"
        elif path.startswith("/search"):
            return "search"
        
        return None