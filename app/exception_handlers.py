"""
글로벌 예외 핸들러
"""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions import BaseAPIException
from app.utils.common import create_error_response


# 로거 설정
logger = logging.getLogger(__name__)


async def base_api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """사용자 정의 API 예외 핸들러"""
    logger.error(
        f"API Exception: {exc.code}",
        extra={
            "error_code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            code=exc.code,
            message=exc.message,
            details=exc.details
        )
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTPException 핸들러"""
    logger.warning(
        f"HTTP Exception: {exc.status_code}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # 상태 코드별 에러 코드 매핑
    error_code_mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_SERVER_ERROR"
    }
    
    error_code = error_code_mapping.get(exc.status_code, "HTTP_ERROR")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            code=error_code,
            message=str(exc.detail)
        )
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """요청 검증 예외 핸들러"""
    logger.warning(
        "Validation Error",
        extra={
            "errors": exc.errors(),
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # 검증 에러를 사용자 친화적 형태로 변환
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])  # 'body' 제외
        details.append({
            "field": field,
            "message": error["msg"]
        })
    
    return JSONResponse(
        status_code=422,
        content=create_error_response(
            code="VALIDATION_ERROR",
            message="입력 데이터 검증에 실패했습니다.",
            details=details
        )
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """SQLAlchemy 예외 핸들러"""
    logger.error(
        "Database Error",
        extra={
            "error": str(exc),
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            code="DATABASE_ERROR",
            message="데이터베이스 작업 중 오류가 발생했습니다."
        )
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """일반 예외 핸들러 (catch-all)"""
    logger.error(
        "Unexpected Error",
        extra={
            "error": str(exc),
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="예상치 못한 오류가 발생했습니다."
        )
    )


def register_exception_handlers(app):
    """FastAPI 앱에 예외 핸들러 등록"""
    app.add_exception_handler(BaseAPIException, base_api_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)