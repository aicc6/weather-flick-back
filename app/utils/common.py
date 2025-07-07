"""
공통 유틸리티 함수들
"""

import uuid
import json
from datetime import datetime
from typing import Any


def create_standard_response(
    success: bool,
    data: Any | None = None,
    error: dict[str, Any] | None = None,
    pagination: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    표준 API 응답 형식을 생성합니다.

    Args:
        success: 성공 여부
        data: 응답 데이터
        error: 에러 정보
        pagination: 페이지네이션 정보

    Returns:
        표준 응답 형식의 딕셔너리
    """
    return {
        "success": success,
        "data": data,
        "error": error,
        "pagination": pagination,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def convert_uuids_to_strings(obj: dict | list | Any) -> dict | list | Any:
    """
    UUID 객체를 문자열로 변환하는 헬퍼 함수

    Args:
        obj: 변환할 객체 (dict, list, 또는 Pydantic 객체)

    Returns:
        UUID가 문자열로 변환된 객체
    """
    # Pydantic 객체인 경우 dict로 변환
    if hasattr(obj, "dict"):
        data = obj.dict()
    elif hasattr(obj, "model_dump"):  # Pydantic v2
        data = obj.model_dump()
    else:
        data = obj

    # 딕셔너리 처리
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, uuid.UUID):  # UUID 객체인 경우
                data[key] = str(value)
            elif hasattr(value, "hex"):  # UUID 객체인 경우 (구 버전 호환)
                data[key] = str(value)
            elif key in ['itinerary', 'weather_info'] and isinstance(value, str):
                # JSON 문자열인 경우 파싱
                try:
                    parsed_value = json.loads(value)
                    data[key] = parsed_value
                except (json.JSONDecodeError, TypeError) as e:
                    # 파싱 실패시 None으로 설정하여 Pydantic 검증 오류 방지
                    print(f"JSON parsing failed for {key}: {e}")
                    data[key] = None
            elif isinstance(value, dict | list):  # 중첩된 객체 처리
                data[key] = convert_uuids_to_strings(value)

    # 리스트 처리
    elif isinstance(data, list):
        for i, item in enumerate(data):
            data[i] = convert_uuids_to_strings(item)

    return data


def create_error_response(
    code: str, message: str, details: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    """
    표준 에러 응답을 생성합니다.

    Args:
        code: 에러 코드
        message: 에러 메시지
        details: 상세 에러 정보

    Returns:
        표준 에러 응답 형식
    """
    error_data = {"code": code, "message": message}

    if details:
        error_data["details"] = details

    return create_standard_response(success=False, error=error_data)


def create_pagination_info(page: int, limit: int, total: int) -> dict[str, int]:
    """
    페이지네이션 정보를 생성합니다.

    Args:
        page: 현재 페이지
        limit: 페이지당 항목 수
        total: 총 항목 수

    Returns:
        페이지네이션 정보 딕셔너리
    """
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
    }


def validate_uuid(uuid_string: str) -> bool:
    """
    UUID 문자열이 유효한지 검증합니다.

    Args:
        uuid_string: 검증할 UUID 문자열

    Returns:
        유효하면 True, 그렇지 않으면 False
    """
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, TypeError):
        return False
