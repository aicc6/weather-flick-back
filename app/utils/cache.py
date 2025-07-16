"""
캐시 유틸리티
Redis 기반 캐싱 시스템
"""

import json
import hashlib
from functools import wraps
from typing import Any, Callable, Optional
from app.utils.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)


def cache_result(ttl: int = 3600, key_prefix: str = "cache"):
    """
    결과를 캐시하는 데코레이터
    
    Args:
        ttl: 캐시 유효시간 (초)
        key_prefix: 캐시 키 접두사
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 캐시 키 생성
            cache_key = _generate_cache_key(func, args, kwargs, key_prefix)
            
            try:
                # 캐시에서 조회
                cached_result = redis_client.get_cache(cache_key)
                if cached_result:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return cached_result
                
                # 캐시 미스 - 함수 실행
                result = func(*args, **kwargs)
                
                # 결과 캐시 저장
                redis_client.set_cache(cache_key, result, ttl)
                logger.debug(f"Cache set for key: {cache_key}")
                
                return result
                
            except Exception as e:
                logger.warning(f"Cache error for key {cache_key}: {e}")
                # 캐시 오류 시 원본 함수 실행
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def _generate_cache_key(func: Callable, args: tuple, kwargs: dict, prefix: str) -> str:
    """캐시 키 생성"""
    # 함수명과 인자들을 조합하여 고유 키 생성
    key_data = {
        'function': f"{func.__module__}.{func.__name__}",
        'args': args,
        'kwargs': kwargs
    }
    
    # 직렬화 가능한 형태로 변환
    serialized = json.dumps(key_data, sort_keys=True, default=str)
    
    # 해시 생성
    hash_object = hashlib.md5(serialized.encode())
    hash_hex = hash_object.hexdigest()
    
    return f"{prefix}:{hash_hex}"


def invalidate_cache_pattern(pattern: str) -> int:
    """패턴에 맞는 캐시 키들을 삭제"""
    try:
        client = redis_client.get_client()
        if not client:
            logger.warning("Redis client not available, skipping cache invalidation")
            return 0
            
        keys = client.keys(pattern)
        if keys:
            deleted_count = client.delete(*keys)
            logger.info(f"Invalidated {deleted_count} cache keys matching pattern: {pattern}")
            return deleted_count
        return 0
    except Exception as e:
        logger.error(f"Error invalidating cache pattern {pattern}: {e}")
        return 0


def clear_category_cache():
    """카테고리 관련 캐시 전체 삭제"""
    return invalidate_cache_pattern("cache:*category*")


def get_cache_info(key: str) -> Optional[dict]:
    """캐시 정보 조회"""
    try:
        client = redis_client.get_client()
        if not client:
            return None
            
        ttl = client.ttl(key)
        if ttl > 0:
            return {
                'key': key,
                'ttl': ttl,
                'exists': True
            }
        return None
    except Exception as e:
        logger.error(f"Error getting cache info for key {key}: {e}")
        return None