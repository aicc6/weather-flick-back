"""
타임존 처리 미들웨어
클라이언트 타임존 정보를 처리하고 적절한 응답 헤더를 추가
"""

import logging
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.timezone_utils import TimezoneUtils

logger = logging.getLogger(__name__)


class TimezoneMiddleware(BaseHTTPMiddleware):
    """
    타임존 처리를 위한 미들웨어
    
    기능:
    1. 클라이언트 타임존 헤더 확인 및 처리
    2. 서버 타임존 정보를 응답 헤더에 추가
    3. 요청별 타임존 컨텍스트 설정
    """
    
    def __init__(self, app, default_timezone: str = "Asia/Seoul"):
        super().__init__(app)
        self.default_timezone = default_timezone
    
    async def dispatch(self, request: Request, call_next):
        # 클라이언트 타임존 정보 수집
        client_timezone = self._extract_client_timezone(request)
        
        # 요청 상태에 타임존 정보 저장
        request.state.client_timezone = client_timezone
        request.state.server_timezone = "UTC"
        request.state.recommended_timezone = self.default_timezone
        
        # 다음 미들웨어/라우터 실행
        response = await call_next(request)
        
        # 응답 헤더에 타임존 정보 추가
        self._add_timezone_headers(response, client_timezone)
        
        # 타임존 관련 로깅
        self._log_timezone_info(request, client_timezone)
        
        return response
    
    def _extract_client_timezone(self, request: Request) -> str:
        """
        클라이언트의 타임존 정보를 추출
        
        우선순위:
        1. X-Client-Timezone 헤더
        2. X-Timezone 헤더
        3. Accept-Language에서 추론
        4. 기본값 (Asia/Seoul)
        """
        
        # 1. 직접 타임존 헤더 확인
        client_timezone = request.headers.get("X-Client-Timezone")
        if client_timezone:
            if self._is_valid_timezone(client_timezone):
                return client_timezone
            else:
                logger.warning(f"유효하지 않은 클라이언트 타임존: {client_timezone}")
        
        # 2. 다른 타임존 헤더 확인
        timezone_header = request.headers.get("X-Timezone")
        if timezone_header:
            if self._is_valid_timezone(timezone_header):
                return timezone_header
        
        # 3. Accept-Language에서 추론
        accept_language = request.headers.get("Accept-Language", "")
        inferred_timezone = self._infer_timezone_from_language(accept_language)
        if inferred_timezone:
            return inferred_timezone
        
        # 4. 기본값 반환
        return self.default_timezone
    
    def _is_valid_timezone(self, timezone_str: str) -> bool:
        """타임존 문자열이 유효한지 확인"""
        try:
            import pytz
            pytz.timezone(timezone_str)
            return True
        except pytz.UnknownTimeZoneError:
            return False
    
    def _infer_timezone_from_language(self, accept_language: str) -> Optional[str]:
        """Accept-Language 헤더에서 타임존 추론"""
        
        # 한국어 관련 로케일
        korean_locales = ["ko", "ko-KR", "ko-kr"]
        
        # 일본어 관련 로케일
        japanese_locales = ["ja", "ja-JP", "ja-jp"]
        
        # 중국어 관련 로케일
        chinese_locales = ["zh", "zh-CN", "zh-cn", "zh-TW", "zh-tw"]
        
        accept_language_lower = accept_language.lower()
        
        for locale in korean_locales:
            if locale in accept_language_lower:
                return "Asia/Seoul"
        
        for locale in japanese_locales:
            if locale in accept_language_lower:
                return "Asia/Tokyo"
        
        for locale in chinese_locales:
            if "tw" in locale or "hk" in accept_language_lower:
                return "Asia/Taipei"
            else:
                return "Asia/Shanghai"
        
        # 영어권의 경우 User-Agent에서 추가 추론 가능하지만 여기서는 기본값 사용
        return None
    
    def _add_timezone_headers(self, response: Response, client_timezone: str):
        """응답에 타임존 관련 헤더 추가"""
        
        # 테스트 헤더 추가
        response.headers["X-Timezone-Middleware-Active"] = "true"
        
        # 서버 타임존 정보
        response.headers["X-Server-Timezone"] = "UTC"
        response.headers["X-Server-Time"] = TimezoneUtils.now_utc().isoformat()
        
        # 클라이언트 권장 타임존
        response.headers["X-Recommended-Timezone"] = self.default_timezone
        response.headers["X-Detected-Client-Timezone"] = client_timezone
        
        # 시간 형식 정보
        response.headers["X-Datetime-Format"] = "ISO8601"
        response.headers["X-Timezone-Note"] = "All server times are in UTC. Convert to local timezone for display."
        
        # CORS를 위한 헤더 노출
        existing_expose = response.headers.get("Access-Control-Expose-Headers", "")
        additional_headers = [
            "X-Timezone-Middleware-Active",
            "X-Server-Timezone",
            "X-Server-Time", 
            "X-Recommended-Timezone",
            "X-Detected-Client-Timezone",
            "X-Datetime-Format",
            "X-Timezone-Note"
        ]
        
        if existing_expose:
            exposed_headers = f"{existing_expose}, {', '.join(additional_headers)}"
        else:
            exposed_headers = ", ".join(additional_headers)
        
        response.headers["Access-Control-Expose-Headers"] = exposed_headers
    
    def _log_timezone_info(self, request: Request, client_timezone: str):
        """타임존 관련 정보 로깅 (디버그 레벨)"""
        
        # 개발 환경에서만 상세 로깅
        logger.debug(
            f"Timezone Info - Path: {request.url.path}, "
            f"Client: {client_timezone}, "
            f"Server: UTC, "
            f"Method: {request.method}"
        )


class AdminTimezoneMiddleware(BaseHTTPMiddleware):
    """
    관리자 백엔드용 타임존 처리 미들웨어
    배치 작업, 로그, 사용자 관리 등에 특화된 타임존 처리
    """
    
    def __init__(self, app, default_timezone: str = "Asia/Seoul"):
        super().__init__(app)
        self.default_timezone = default_timezone
    
    async def dispatch(self, request: Request, call_next):
        # 관리자 전용 타임존 정보 설정
        request.state.admin_timezone = self.default_timezone
        request.state.server_timezone = "UTC"
        request.state.log_timezone = "UTC"  # 로그는 항상 UTC
        
        # 다음 미들웨어/라우터 실행
        response = await call_next(request)
        
        # 관리자 전용 응답 헤더 추가
        self._add_admin_timezone_headers(response)
        
        # 관리자 액션 로깅
        self._log_admin_action(request)
        
        return response
    
    def _add_admin_timezone_headers(self, response: Response):
        """관리자 응답에 타임존 관련 헤더 추가"""
        
        current_utc = TimezoneUtils.now_utc()
        current_kst = TimezoneUtils.to_kst(current_utc)
        
        # 관리자 전용 헤더
        response.headers["X-Admin-Server-Timezone"] = "UTC"
        response.headers["X-Admin-Server-Time-UTC"] = current_utc.isoformat()
        response.headers["X-Admin-Server-Time-KST"] = current_kst.isoformat() if current_kst else ""
        response.headers["X-Admin-Display-Timezone"] = self.default_timezone
        
        # 배치 작업 관련 정보
        response.headers["X-Admin-Batch-Timezone"] = "UTC"
        response.headers["X-Admin-Log-Timezone"] = "UTC"
        
        # 관리자 안내 메시지
        response.headers["X-Admin-Timezone-Guide"] = (
            "Server times in UTC, display times in KST. "
            "Batch jobs and logs use UTC timestamps."
        )
        
        # CORS를 위한 헤더 노출
        admin_headers = [
            "X-Admin-Server-Timezone",
            "X-Admin-Server-Time-UTC",
            "X-Admin-Server-Time-KST",
            "X-Admin-Display-Timezone",
            "X-Admin-Batch-Timezone",
            "X-Admin-Log-Timezone",
            "X-Admin-Timezone-Guide"
        ]
        
        response.headers["Access-Control-Expose-Headers"] = ", ".join(admin_headers)
    
    def _log_admin_action(self, request: Request):
        """관리자 작업 로깅"""
        
        # 민감한 작업만 로깅 (GET 요청 제외)
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            logger.info(
                f"Admin Action - Method: {request.method}, "
                f"Path: {request.url.path}, "
                f"Time: {TimezoneUtils.now_utc().isoformat()}, "
                f"IP: {request.client.host if request.client else 'unknown'}"
            )


# 미들웨어 설정 헬퍼 함수
def setup_timezone_middleware(app, is_admin: bool = False):
    """
    앱에 타임존 미들웨어 추가
    
    Args:
        app: FastAPI 앱 인스턴스
        is_admin: 관리자 백엔드 여부
    """
    
    if is_admin:
        app.add_middleware(AdminTimezoneMiddleware, default_timezone="Asia/Seoul")
        logger.info("관리자용 타임존 미들웨어가 추가되었습니다.")
    else:
        app.add_middleware(TimezoneMiddleware, default_timezone="Asia/Seoul")
        logger.info("사용자용 타임존 미들웨어가 추가되었습니다.")


# 타임존 관련 유틸리티 함수들
def get_request_timezone(request: Request) -> str:
    """요청에서 클라이언트 타임존 반환"""
    return getattr(request.state, 'client_timezone', 'Asia/Seoul')


def get_server_timezone(request: Request) -> str:
    """요청에서 서버 타임존 반환"""
    return getattr(request.state, 'server_timezone', 'UTC')


def format_datetime_for_client(dt, request: Request) -> str:
    """클라이언트 타임존에 맞게 datetime 포맷팅"""
    client_tz = get_request_timezone(request)
    
    if client_tz == "Asia/Seoul":
        kst_dt = TimezoneUtils.to_kst(dt)
        return TimezoneUtils.format_for_api(kst_dt) if kst_dt else ""
    else:
        # 다른 타임존도 필요시 추가
        return TimezoneUtils.format_for_api(dt)