"""
타임존 처리 유틸리티 모듈
모든 시간 관련 처리를 일관되게 관리하기 위한 유틸리티
"""

from datetime import datetime, timezone, timedelta
import pytz
from typing import Optional, Union

# 한국 표준시 타임존
KST = pytz.timezone('Asia/Seoul')
UTC = pytz.UTC


class TimezoneUtils:
    """타임존 처리를 위한 유틸리티 클래스"""
    
    @classmethod
    def now_utc(cls) -> datetime:
        """UTC 현재 시간 반환"""
        return datetime.now(timezone.utc)
    
    @classmethod
    def now_kst(cls) -> datetime:
        """KST 현재 시간 반환"""
        return datetime.now(KST)
    
    @classmethod
    def to_utc(cls, dt: Union[datetime, str, None]) -> Optional[datetime]:
        """datetime을 UTC로 변환"""
        if dt is None:
            return None
            
        if isinstance(dt, str):
            dt = cls._parse_datetime_string(dt)
            if dt is None:
                return None
        
        if dt.tzinfo is None:
            # naive datetime을 KST로 가정하고 UTC로 변환
            dt = KST.localize(dt)
        
        return dt.astimezone(timezone.utc)
    
    @classmethod
    def to_kst(cls, dt: Union[datetime, str, None]) -> Optional[datetime]:
        """datetime을 KST로 변환"""
        if dt is None:
            return None
            
        if isinstance(dt, str):
            dt = cls._parse_datetime_string(dt)
            if dt is None:
                return None
        
        if dt.tzinfo is None:
            # naive datetime을 UTC로 가정
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt.astimezone(KST)
    
    @classmethod
    def localize_kst(cls, naive_dt: datetime) -> datetime:
        """naive datetime을 KST로 localize"""
        if naive_dt.tzinfo is not None:
            return naive_dt
        return KST.localize(naive_dt)
    
    @classmethod
    def format_iso_with_timezone(cls, dt: datetime) -> str:
        """datetime을 타임존 정보가 포함된 ISO 8601 형식으로 포맷"""
        if dt is None:
            return None
        
        if dt.tzinfo is None:
            # naive datetime을 UTC로 가정
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt.isoformat()
    
    @classmethod
    def format_for_api(cls, dt: datetime) -> str:
        """API 응답용 날짜시간 포맷 (ISO 8601 with timezone)"""
        if dt is None:
            return None
            
        # UTC로 변환 후 ISO 형식으로 출력
        utc_dt = cls.to_utc(dt)
        return utc_dt.isoformat() if utc_dt else None
    
    @classmethod
    def parse_api_datetime(cls, dt_string: str) -> Optional[datetime]:
        """API에서 받은 날짜시간 문자열을 파싱"""
        return cls._parse_datetime_string(dt_string)
    
    @classmethod
    def get_kst_date_string(cls, dt: Optional[datetime] = None) -> str:
        """KST 기준 날짜를 YYYY-MM-DD 형식으로 반환"""
        if dt is None:
            dt = cls.now_kst()
        else:
            dt = cls.to_kst(dt)
        
        return dt.strftime('%Y-%m-%d') if dt else None
    
    @classmethod
    def get_date_range_kst(cls, start_date: str, end_date: str) -> tuple:
        """날짜 범위를 KST 기준으로 파싱하여 UTC datetime 튜플 반환"""
        try:
            # 날짜 문자열을 KST 기준으로 파싱
            start_kst = KST.localize(datetime.strptime(start_date, '%Y-%m-%d'))
            # 종료일은 해당 날의 23:59:59까지 포함
            end_kst = KST.localize(
                datetime.strptime(end_date, '%Y-%m-%d').replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
            )
            
            # UTC로 변환하여 반환
            return start_kst.astimezone(timezone.utc), end_kst.astimezone(timezone.utc)
        except (ValueError, TypeError) as e:
            print(f"날짜 범위 파싱 오류: {e}")
            return None, None
    
    @classmethod
    def _parse_datetime_string(cls, dt_string: str) -> Optional[datetime]:
        """다양한 형식의 날짜시간 문자열을 파싱"""
        if not dt_string:
            return None
        
        # 지원하는 날짜시간 형식들
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',     # ISO with microseconds and Z
            '%Y-%m-%dT%H:%M:%SZ',        # ISO with Z
            '%Y-%m-%dT%H:%M:%S.%f%z',    # ISO with microseconds and timezone
            '%Y-%m-%dT%H:%M:%S%z',       # ISO with timezone
            '%Y-%m-%dT%H:%M:%S.%f',      # ISO with microseconds (naive)
            '%Y-%m-%dT%H:%M:%S',         # ISO format (naive)
            '%Y-%m-%d %H:%M:%S.%f',      # SQL datetime with microseconds
            '%Y-%m-%d %H:%M:%S',         # SQL datetime
            '%Y-%m-%d',                  # Date only
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(dt_string, fmt)
                
                # Z가 있으면 UTC로 처리
                if dt_string.endswith('Z'):
                    dt = dt.replace(tzinfo=timezone.utc)
                
                return dt
            except ValueError:
                continue
        
        # 모든 형식이 실패하면 None 반환
        print(f"지원하지 않는 날짜시간 형식: {dt_string}")
        return None


def utcnow() -> datetime:
    """UTC 현재 시간 반환 (func.utcnow() 대체용)"""
    return TimezoneUtils.now_utc()


def kst_now() -> datetime:
    """KST 현재 시간 반환"""
    return TimezoneUtils.now_kst()


def format_datetime_for_api(dt: datetime) -> str:
    """API 응답용 datetime 포맷"""
    return TimezoneUtils.format_for_api(dt)


def safe_parse_datetime(dt_string: str) -> Optional[datetime]:
    """안전한 datetime 파싱"""
    return TimezoneUtils.parse_api_datetime(dt_string)


# 하위 호환성을 위한 별칭들
now_utc = TimezoneUtils.now_utc
now_kst = TimezoneUtils.now_kst
to_utc = TimezoneUtils.to_utc
to_kst = TimezoneUtils.to_kst