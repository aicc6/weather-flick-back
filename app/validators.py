"""
공통 Validation 규칙 정의
모든 Pydantic 스키마에서 일관되게 사용할 validator 함수들
"""

import re
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal
from pydantic import field_validator, ValidationInfo
from pydantic_core import PydanticCustomError


class CommonValidators:
    """공통 validation 규칙들"""

    @staticmethod
    def validate_email(email: str) -> str:
        """이메일 유효성 검증"""
        if not email or '@' not in email:
            raise ValueError('유효하지 않은 이메일 형식입니다')
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError('올바른 이메일 형식이 아닙니다')
        
        return email.lower().strip()

    @staticmethod
    def validate_password(password: str) -> str:
        """비밀번호 유효성 검증"""
        if not password:
            raise ValueError('비밀번호는 필수입니다')
        
        if len(password) < 8:
            raise ValueError('비밀번호는 최소 8자 이상이어야 합니다')
        
        if len(password) > 100:
            raise ValueError('비밀번호는 100자를 초과할 수 없습니다')
        
        # 영문, 숫자, 특수문자 중 2가지 이상 포함
        patterns = [
            r'[a-zA-Z]',  # 영문
            r'[0-9]',     # 숫자
            r'[!@#$%^&*(),.?":{}|<>]'  # 특수문자
        ]
        
        match_count = sum(1 for pattern in patterns if re.search(pattern, password))
        if match_count < 2:
            raise ValueError('비밀번호는 영문, 숫자, 특수문자 중 2가지 이상을 포함해야 합니다')
        
        return password

    @staticmethod
    def validate_nickname(nickname: str) -> str:
        """닉네임 유효성 검증"""
        if not nickname or not nickname.strip():
            raise ValueError('닉네임은 필수입니다')
        
        nickname = nickname.strip()
        
        if len(nickname) < 2:
            raise ValueError('닉네임은 최소 2자 이상이어야 합니다')
        
        if len(nickname) > 20:
            raise ValueError('닉네임은 20자를 초과할 수 없습니다')
        
        # 허용되지 않는 문자 검사
        if re.search(r'[^\w\sㄱ-ㅎㅏ-ㅣ가-힣]', nickname):
            raise ValueError('닉네임에는 한글, 영문, 숫자, 공백만 사용할 수 있습니다')
        
        return nickname

    @staticmethod
    def validate_phone(phone: Optional[str]) -> Optional[str]:
        """전화번호 유효성 검증"""
        if not phone:
            return None
        
        # 숫자와 하이픈만 허용
        phone = re.sub(r'[^\d-]', '', phone)
        
        # 한국 전화번호 패턴 (010-1234-5678, 02-1234-5678 등)
        phone_patterns = [
            r'^01[0-9]-\d{3,4}-\d{4}$',  # 휴대폰
            r'^0[2-6][0-9]?-\d{3,4}-\d{4}$',  # 지역번호
            r'^070-\d{3,4}-\d{4}$',  # 인터넷 전화
        ]
        
        if not any(re.match(pattern, phone) for pattern in phone_patterns):
            raise ValueError('올바른 전화번호 형식이 아닙니다 (예: 010-1234-5678)')
        
        return phone

    @staticmethod
    def validate_preferences(preferences: Any) -> Dict[str, Any]:
        """사용자 설정 유효성 검증"""
        if preferences is None or preferences == []:
            return {}
        
        if isinstance(preferences, list):
            return {}
        
        if not isinstance(preferences, dict):
            raise ValueError('사용자 설정은 딕셔너리 형태여야 합니다')
        
        return preferences

    @staticmethod
    def validate_date_range(start_date: Optional[date], end_date: Optional[date]) -> tuple:
        """날짜 범위 유효성 검증"""
        if start_date and end_date:
            if start_date > end_date:
                raise ValueError('시작일은 종료일보다 늦을 수 없습니다')
            
            # 최대 365일까지만 허용
            if (end_date - start_date).days > 365:
                raise ValueError('여행 기간은 최대 365일까지만 설정할 수 있습니다')
        
        return start_date, end_date

    @staticmethod
    def validate_budget(budget: Optional[Decimal]) -> Optional[Decimal]:
        """예산 유효성 검증"""
        if budget is None:
            return None
        
        if budget < 0:
            raise ValueError('예산은 0 이상이어야 합니다')
        
        if budget > Decimal('999999999'):
            raise ValueError('예산은 999,999,999원을 초과할 수 없습니다')
        
        return budget

    @staticmethod
    def validate_participants(participants: Optional[int]) -> Optional[int]:
        """참가자 수 유효성 검증"""
        if participants is None:
            return None
        
        if participants < 1:
            raise ValueError('참가자 수는 1명 이상이어야 합니다')
        
        if participants > 100:
            raise ValueError('참가자 수는 100명을 초과할 수 없습니다')
        
        return participants

    @staticmethod
    def validate_coordinates(latitude: Optional[float], longitude: Optional[float]) -> tuple:
        """좌표 유효성 검증"""
        if latitude is not None:
            if not (-90 <= latitude <= 90):
                raise ValueError('위도는 -90도에서 90도 사이여야 합니다')
        
        if longitude is not None:
            if not (-180 <= longitude <= 180):
                raise ValueError('경도는 -180도에서 180도 사이여야 합니다')
        
        return latitude, longitude

    @staticmethod
    def validate_json_field(data: Any, field_name: str) -> Optional[Dict[str, Any]]:
        """JSON 필드 유효성 검증"""
        if data is None:
            return None
        
        if isinstance(data, str):
            try:
                import json
                data = json.loads(data)
            except json.JSONDecodeError:
                raise ValueError(f'{field_name}은(는) 유효한 JSON 형태여야 합니다')
        
        if not isinstance(data, dict):
            raise ValueError(f'{field_name}은(는) 딕셔너리 형태여야 합니다')
        
        return data

    @staticmethod
    def validate_content_id(content_id: str) -> str:
        """관광지 컨텐츠 ID 유효성 검증"""
        if not content_id or not content_id.strip():
            raise ValueError('컨텐츠 ID는 필수입니다')
        
        content_id = content_id.strip()
        
        # 숫자만 허용 (한국관광공사 API 규격)
        if not content_id.isdigit():
            raise ValueError('컨텐츠 ID는 숫자여야 합니다')
        
        if len(content_id) > 20:
            raise ValueError('컨텐츠 ID는 20자를 초과할 수 없습니다')
        
        return content_id

    @staticmethod
    def validate_region_code(region_code: str) -> str:
        """지역 코드 유효성 검증"""
        if not region_code or not region_code.strip():
            raise ValueError('지역 코드는 필수입니다')
        
        region_code = region_code.strip()
        
        # 지역 코드 형식: 숫자 또는 숫자+문자 조합
        if not re.match(r'^[0-9A-Za-z]+$', region_code):
            raise ValueError('지역 코드는 영숫자만 사용할 수 있습니다')
        
        if len(region_code) > 10:
            raise ValueError('지역 코드는 10자를 초과할 수 없습니다')
        
        return region_code

    @staticmethod  
    def validate_url(url: Optional[str]) -> Optional[str]:
        """URL 유효성 검증"""
        if not url:
            return None
        
        url = url.strip()
        
        # 기본적인 URL 패턴 검증
        url_pattern = r'^https?:\/\/[\w\-._~:/?#[\]@!$&\'()*+,;=%]+$'
        if not re.match(url_pattern, url):
            raise ValueError('올바른 URL 형식이 아닙니다')
        
        if len(url) > 2000:
            raise ValueError('URL은 2000자를 초과할 수 없습니다')
        
        return url


def create_field_validator(validator_func, field_name: str = None):
    """필드 validator 생성 헬퍼 함수"""
    def validator(cls, v, info: ValidationInfo = None):
        if field_name and info:
            # ValidationInfo에서 필드명 가져오기
            current_field = info.field_name if info.field_name else field_name
            return validator_func(v, current_field)
        return validator_func(v)
    
    return field_validator(field_name if field_name else 'value', mode='before')(validator)