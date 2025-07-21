"""
시스템 모니터링 미들웨어
성능 메트릭, 요청 추적, 리소스 사용량 모니터링
"""
import time
import psutil
import asyncio
from typing import Dict, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import logging

logger = logging.getLogger(__name__)


class SystemMetrics:
    """시스템 메트릭 수집 및 저장"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        # 요청 메트릭
        self.request_count = defaultdict(int)
        self.response_times = deque(maxlen=max_history)
        self.error_count = defaultdict(int)
        self.status_codes = defaultdict(int)
        
        # 시스템 메트릭
        self.cpu_usage = deque(maxlen=100)
        self.memory_usage = deque(maxlen=100)
        self.disk_usage = deque(maxlen=100)
        
        # 엔드포인트별 메트릭
        self.endpoint_metrics = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'errors': 0
        })
        
        # 시간대별 메트릭
        self.hourly_requests = defaultdict(int)
        
        # 시작 시간
        self.start_time = datetime.now()
    
    def record_request(self, method: str, path: str, status_code: int, 
                      response_time: float, error: bool = False):
        """요청 메트릭 기록"""
        # 전체 요청 수
        self.request_count[f"{method}"] += 1
        self.request_count["total"] += 1
        
        # 응답 시간
        self.response_times.append(response_time)
        
        # 상태 코드
        self.status_codes[status_code] += 1
        
        # 에러 카운트
        if error:
            self.error_count[f"{method}_{path}"] += 1
            self.error_count["total"] += 1
        
        # 엔드포인트별 메트릭
        endpoint_key = f"{method}_{path}"
        endpoint = self.endpoint_metrics[endpoint_key]
        endpoint['count'] += 1
        endpoint['total_time'] += response_time
        endpoint['avg_time'] = endpoint['total_time'] / endpoint['count']
        endpoint['min_time'] = min(endpoint['min_time'], response_time)
        endpoint['max_time'] = max(endpoint['max_time'], response_time)
        if error:
            endpoint['errors'] += 1
        
        # 시간대별 요청 수
        hour_key = datetime.now().strftime("%Y-%m-%d_%H")
        self.hourly_requests[hour_key] += 1
    
    def record_system_metrics(self):
        """시스템 리소스 메트릭 기록"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_usage.append(cpu_percent)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            self.memory_usage.append(memory.percent)
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.disk_usage.append(disk_percent)
            
        except Exception as e:
            logger.error(f"시스템 메트릭 수집 오류: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """메트릭 요약 정보 반환"""
        uptime = datetime.now() - self.start_time
        
        # 응답 시간 통계
        response_times_list = list(self.response_times)
        avg_response_time = sum(response_times_list) / len(response_times_list) if response_times_list else 0
        
        # 에러율 계산
        total_requests = self.request_count.get("total", 0)
        total_errors = self.error_count.get("total", 0)
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        # 최근 시스템 메트릭
        recent_cpu = list(self.cpu_usage)[-10:] if self.cpu_usage else []
        recent_memory = list(self.memory_usage)[-10:] if self.memory_usage else []
        recent_disk = list(self.disk_usage)[-10:] if self.disk_usage else []
        
        return {
            "uptime": str(uptime),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": round(error_rate, 2),
            "avg_response_time": round(avg_response_time, 3),
            "requests_by_method": dict(self.request_count),
            "status_codes": dict(self.status_codes),
            "system": {
                "cpu_usage": {
                    "current": recent_cpu[-1] if recent_cpu else 0,
                    "avg_last_10": round(sum(recent_cpu) / len(recent_cpu), 1) if recent_cpu else 0
                },
                "memory_usage": {
                    "current": recent_memory[-1] if recent_memory else 0,
                    "avg_last_10": round(sum(recent_memory) / len(recent_memory), 1) if recent_memory else 0
                },
                "disk_usage": {
                    "current": recent_disk[-1] if recent_disk else 0,
                    "avg_last_10": round(sum(recent_disk) / len(recent_disk), 1) if recent_disk else 0
                }
            },
            "top_endpoints": self._get_top_endpoints(),
            "recent_hourly_requests": dict(list(self.hourly_requests.items())[-24:])  # 최근 24시간
        }
    
    def _get_top_endpoints(self, limit: int = 10):
        """가장 많이 호출된 엔드포인트 반환"""
        sorted_endpoints = sorted(
            self.endpoint_metrics.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        top_endpoints = {}
        for endpoint, metrics in sorted_endpoints[:limit]:
            top_endpoints[endpoint] = {
                "count": metrics['count'],
                "avg_time": round(metrics['avg_time'], 3),
                "max_time": round(metrics['max_time'], 3),
                "errors": metrics['errors'],
                "error_rate": round((metrics['errors'] / metrics['count'] * 100), 2) if metrics['count'] > 0 else 0
            }
        
        return top_endpoints


# 전역 메트릭 인스턴스
system_metrics = SystemMetrics()


class MonitoringMiddleware(BaseHTTPMiddleware):
    """모니터링 미들웨어"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # 모니터링 엔드포인트는 메트릭에서 제외
        if request.url.path.startswith('/metrics'):
            return await call_next(request)
        
        start_time = time.time()
        method = request.method
        path = request.url.path
        
        try:
            response = await call_next(request)
            
            # 응답 시간 계산
            response_time = time.time() - start_time
            
            # 에러 여부 판단
            is_error = response.status_code >= 400
            
            # 메트릭 기록
            system_metrics.record_request(
                method=method,
                path=path,
                status_code=response.status_code,
                response_time=response_time,
                error=is_error
            )
            
            # 응답 헤더에 메트릭 정보 추가
            response.headers["X-Response-Time"] = f"{response_time:.3f}s"
            response.headers["X-Request-ID"] = str(hash(f"{method}_{path}_{start_time}"))
            
            return response
            
        except Exception as e:
            # 예외 발생 시에도 메트릭 기록
            response_time = time.time() - start_time
            system_metrics.record_request(
                method=method,
                path=path,
                status_code=500,
                response_time=response_time,
                error=True
            )
            raise


class MetricsEndpoint:
    """메트릭 조회 엔드포인트"""
    
    @staticmethod
    async def get_metrics():
        """현재 시스템 메트릭 반환"""
        # 최신 시스템 메트릭 수집
        system_metrics.record_system_metrics()
        
        # 메트릭 요약 반환
        return system_metrics.get_summary()
    
    @staticmethod
    async def get_health():
        """상세 헬스체크"""
        metrics = await MetricsEndpoint.get_metrics()
        
        # 헬스 상태 판단
        is_healthy = True
        issues = []
        
        # CPU 사용률 체크 (80% 이상이면 경고)
        cpu_usage = metrics["system"]["cpu_usage"]["current"]
        if cpu_usage > 80:
            is_healthy = False
            issues.append(f"High CPU usage: {cpu_usage}%")
        
        # 메모리 사용률 체크 (90% 이상이면 경고)
        memory_usage = metrics["system"]["memory_usage"]["current"]
        if memory_usage > 90:
            is_healthy = False
            issues.append(f"High memory usage: {memory_usage}%")
        
        # 에러율 체크 (5% 이상이면 경고)
        error_rate = metrics["error_rate"]
        if error_rate > 5:
            is_healthy = False
            issues.append(f"High error rate: {error_rate}%")
        
        # 평균 응답시간 체크 (1초 이상이면 경고)
        avg_response_time = metrics["avg_response_time"]
        if avg_response_time > 1.0:
            is_healthy = False
            issues.append(f"Slow response time: {avg_response_time}s")
        
        health_status = {
            "status": "healthy" if is_healthy else "unhealthy",
            "checks": {
                "cpu": cpu_usage,
                "memory": memory_usage,
                "error_rate": error_rate,
                "avg_response_time": avg_response_time
            },
            "issues": issues,
            "metrics": metrics
        }
        
        return health_status


# 백그라운드 작업으로 시스템 메트릭 주기적 수집
async def collect_system_metrics():
    """백그라운드에서 시스템 메트릭 수집"""
    while True:
        try:
            system_metrics.record_system_metrics()
            await asyncio.sleep(30)  # 30초마다 수집
        except Exception as e:
            logger.error(f"시스템 메트릭 수집 백그라운드 작업 오류: {e}")
            await asyncio.sleep(60)  # 오류 시 1분 대기