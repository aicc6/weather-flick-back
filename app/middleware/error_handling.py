"""
통합 에러 처리 미들웨어
API 전체에 걸친 일관된 에러 처리 및 로깅
"""
import traceback
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """통합 에러 처리 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 요청 ID 생성 (추적용)
        request_id = str(uuid.uuid4())[:8]
        
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as exc:
            # FastAPI HTTPException 처리
            return await self._handle_http_exception(request, exc, request_id)
            
        except RequestValidationError as exc:
            # 요청 검증 오류 처리
            return await self._handle_validation_error(request, exc, request_id)
            
        except SQLAlchemyError as exc:
            # 데이터베이스 오류 처리
            return await self._handle_database_error(request, exc, request_id)
            
        except Exception as exc:
            # 예상치 못한 오류 처리
            return await self._handle_unexpected_error(request, exc, request_id)
    
    async def _handle_http_exception(
        self, request: Request, exc: HTTPException, request_id: str
    ) -> JSONResponse:
        """HTTPException 처리"""
        logger.warning(
            f"HTTP Exception [{request_id}] {request.method} {request.url}: "
            f"{exc.status_code} - {exc.detail}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "http_error",
                    "code": exc.status_code,
                    "message": exc.detail,
                    "request_id": request_id,
                }
            },
            headers=exc.headers or {},
        )
    
    async def _handle_validation_error(
        self, request: Request, exc: RequestValidationError, request_id: str
    ) -> JSONResponse:
        """요청 검증 오류 처리"""
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            })
        
        logger.warning(
            f"Validation Error [{request_id}] {request.method} {request.url}: "
            f"{len(errors)} validation errors"
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "validation_error",
                    "code": 422,
                    "message": "요청 데이터 검증에 실패했습니다.",
                    "details": errors,
                    "request_id": request_id,
                }
            },
        )
    
    async def _handle_database_error(
        self, request: Request, exc: SQLAlchemyError, request_id: str
    ) -> JSONResponse:
        """데이터베이스 오류 처리"""
        logger.error(
            f"Database Error [{request_id}] {request.method} {request.url}: "
            f"{type(exc).__name__} - {str(exc)}"
        )
        
        # 프로덕션에서는 상세한 데이터베이스 오류를 숨김
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "database_error",
                    "code": 500,
                    "message": "데이터베이스 처리 중 오류가 발생했습니다.",
                    "request_id": request_id,
                }
            },
        )
    
    async def _handle_unexpected_error(
        self, request: Request, exc: Exception, request_id: str
    ) -> JSONResponse:
        """예상치 못한 오류 처리"""
        error_trace = traceback.format_exc()
        
        logger.error(
            f"Unexpected Error [{request_id}] {request.method} {request.url}: "
            f"{type(exc).__name__} - {str(exc)}\n{error_trace}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "internal_error", 
                    "code": 500,
                    "message": "서버 내부 오류가 발생했습니다.",
                    "request_id": request_id,
                }
            },
        )


class TimeoutMiddleware(BaseHTTPMiddleware):
    """요청 타임아웃 처리 미들웨어"""
    
    def __init__(self, app, timeout_seconds: int = 30):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import asyncio
        
        try:
            return await asyncio.wait_for(
                call_next(request), timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Request timeout: {request.method} {request.url} "
                f"(>{self.timeout_seconds}s)"
            )
            return JSONResponse(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                content={
                    "error": {
                        "type": "timeout_error",
                        "code": 408,
                        "message": "요청 처리 시간이 초과되었습니다.",
                        "timeout": self.timeout_seconds,
                    }
                },
            )


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """헬스체크 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 헬스체크 엔드포인트는 빠른 응답
        if request.url.path in ["/health", "/", "/api/health"]:
            try:
                # 간단한 데이터베이스 연결 확인
                from app.database import check_db_connection
                db_ok, db_msg = check_db_connection()
                
                if not db_ok:
                    logger.warning(f"Health check database failure: {db_msg}")
                    return JSONResponse(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content={
                            "status": "unhealthy", 
                            "database": db_msg,
                            "service": "weather-flick-backend"
                        }
                    )
                
                return JSONResponse(
                    content={
                        "status": "healthy",
                        "database": "connected",
                        "service": "weather-flick-backend"
                    }
                )
            except Exception as e:
                logger.error(f"Health check error: {e}")
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "unhealthy",
                        "error": str(e),
                        "service": "weather-flick-backend"
                    }
                )
        
        return await call_next(request)