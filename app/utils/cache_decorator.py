"""
Redis 캐싱 데코레이터
"""

import functools
import hashlib
import logging
from collections.abc import Callable

from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """캐시 키 생성"""
    # 인자들을 문자열로 변환하여 해시 생성
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    key_string = ":".join(key_parts)

    # 키가 너무 길어지는 것을 방지하기 위해 해시 사용
    if len(key_string) > 200:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    return f"{prefix}:{key_string}"


def cache_result(
    prefix: str,
    expire: int = 3600,
    key_generator: Callable | None = None,
    include_cache_info: bool = False
):
    """
    함수 결과를 캐싱하는 데코레이터
    
    Args:
        prefix: 캐시 키 접두사
        expire: 캐시 만료 시간 (초)
        key_generator: 커스텀 키 생성 함수
        include_cache_info: 캐시 정보를 응답에 포함할지 여부
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 캐시 키 생성
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                cache_key = generate_cache_key(prefix, *args, **kwargs)

            # Redis 클라이언트 가져오기
            redis_client = get_redis_client()

            # 캐시에서 조회
            cached_value = redis_client.get_cache(cache_key)
            if cached_value is not None:
                logger.debug(f"캐시 히트: {cache_key}")
                if include_cache_info:
                    # 캐시 정보 추가
                    import time
                    cached_value["cache_info"] = {
                        "is_cached": True,
                        "cache_key": cache_key,
                        "retrieved_at": time.time(),
                        "expires_in": expire
                    }
                return cached_value

            # 캐시 미스 - 함수 실행
            logger.debug(f"캐시 미스: {cache_key}")
            result = await func(*args, **kwargs)

            # 결과를 캐시에 저장
            if result is not None:
                redis_client.set_cache(cache_key, result, expire)
                if include_cache_info:
                    # 캐시 정보 추가
                    import time
                    result["cache_info"] = {
                        "is_cached": False,
                        "cache_key": cache_key,
                        "cached_at": time.time(),
                        "expires_in": expire
                    }

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 캐시 키 생성
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                cache_key = generate_cache_key(prefix, *args, **kwargs)

            # Redis 클라이언트 가져오기
            redis_client = get_redis_client()

            # 캐시에서 조회
            cached_value = redis_client.get_cache(cache_key)
            if cached_value is not None:
                logger.debug(f"캐시 히트: {cache_key}")
                if include_cache_info:
                    # 캐시 정보 추가
                    import time
                    cached_value["cache_info"] = {
                        "is_cached": True,
                        "cache_key": cache_key,
                        "retrieved_at": time.time(),
                        "expires_in": expire
                    }
                return cached_value

            # 캐시 미스 - 함수 실행
            logger.debug(f"캐시 미스: {cache_key}")
            result = func(*args, **kwargs)

            # 결과를 캐시에 저장
            if result is not None:
                redis_client.set_cache(cache_key, result, expire)
                if include_cache_info:
                    # 캐시 정보 추가
                    import time
                    result["cache_info"] = {
                        "is_cached": False,
                        "cache_key": cache_key,
                        "cached_at": time.time(),
                        "expires_in": expire
                    }

            return result

        # 비동기 함수인지 확인
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_cache(pattern: str):
    """캐시 무효화 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # 캐시 무효화
            redis_client = get_redis_client()
            deleted = redis_client.clear_pattern(pattern)
            if deleted > 0:
                logger.info(f"캐시 무효화: {pattern} ({deleted}개 삭제)")

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # 캐시 무효화
            redis_client = get_redis_client()
            deleted = redis_client.clear_pattern(pattern)
            if deleted > 0:
                logger.info(f"캐시 무효화: {pattern} ({deleted}개 삭제)")

            return result

        # 비동기 함수인지 확인
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
