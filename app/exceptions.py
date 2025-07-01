"""
사용자 정의 예외 클래스들
"""
from typing import Optional, Dict, Any, List


class BaseAPIException(Exception):
    """기본 API 예외 클래스"""
    
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 500,
        details: Optional[List[Dict[str, str]]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []
        super().__init__(self.message)


class AuthenticationError(BaseAPIException):
    """인증 관련 예외"""
    
    def __init__(
        self,
        message: str = "인증에 실패했습니다.",
        code: str = "AUTHENTICATION_ERROR",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, 401, details)


class AuthorizationError(BaseAPIException):
    """권한 관련 예외"""
    
    def __init__(
        self,
        message: str = "권한이 없습니다.",
        code: str = "AUTHORIZATION_ERROR",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, 403, details)


class ValidationError(BaseAPIException):
    """데이터 검증 예외"""
    
    def __init__(
        self,
        message: str = "입력 데이터가 올바르지 않습니다.",
        code: str = "VALIDATION_ERROR",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, 400, details)


class NotFoundError(BaseAPIException):
    """리소스 없음 예외"""
    
    def __init__(
        self,
        message: str = "요청한 리소스를 찾을 수 없습니다.",
        code: str = "NOT_FOUND",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, 404, details)


class ExternalAPIError(BaseAPIException):
    """외부 API 호출 예외"""
    
    def __init__(
        self,
        message: str = "외부 서비스에 일시적인 문제가 발생했습니다.",
        code: str = "EXTERNAL_API_ERROR",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, 503, details)


class WeatherServiceError(ExternalAPIError):
    """날씨 서비스 예외"""
    
    def __init__(
        self,
        message: str = "날씨 정보를 가져올 수 없습니다.",
        code: str = "WEATHER_SERVICE_ERROR",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, details)


class KMAServiceError(ExternalAPIError):
    """기상청 API 서비스 예외"""
    
    def __init__(
        self,
        message: str = "기상청 날씨 정보를 가져올 수 없습니다.",
        code: str = "KMA_SERVICE_ERROR",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, details)


class EmailServiceError(BaseAPIException):
    """이메일 서비스 예외"""
    
    def __init__(
        self,
        message: str = "이메일 전송에 실패했습니다.",
        code: str = "EMAIL_SERVICE_ERROR",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, 503, details)


class DatabaseError(BaseAPIException):
    """데이터베이스 예외"""
    
    def __init__(
        self,
        message: str = "데이터베이스 작업 중 오류가 발생했습니다.",
        code: str = "DATABASE_ERROR",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, 500, details)


class TravelPlanError(BaseAPIException):
    """여행 계획 관련 예외"""
    
    def __init__(
        self,
        message: str = "여행 계획 처리 중 오류가 발생했습니다.",
        code: str = "TRAVEL_PLAN_ERROR",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, 400, details)


class RecommendationError(BaseAPIException):
    """추천 서비스 예외"""
    
    def __init__(
        self,
        message: str = "추천 서비스에서 오류가 발생했습니다.",
        code: str = "RECOMMENDATION_ERROR",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, 500, details)


class LocalInfoServiceError(ExternalAPIError):
    """지역 정보 서비스 예외"""
    
    def __init__(
        self,
        message: str = "지역 정보를 가져올 수 없습니다.",
        code: str = "LOCAL_INFO_SERVICE_ERROR",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, details)


class NaverMapServiceError(ExternalAPIError):
    """네이버 지도 서비스 예외"""
    
    def __init__(
        self,
        message: str = "지도 정보를 가져올 수 없습니다.",
        code: str = "NAVER_MAP_SERVICE_ERROR",
        details: Optional[List[Dict[str, str]]] = None
    ):
        super().__init__(message, code, details)