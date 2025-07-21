"""
Security middleware module
Middleware for protecting against XSS, clickjacking, CSRF and other security threats
"""

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers"""

    def __init__(self, app, csp_policy: str = None):
        super().__init__(app)
        self.csp_policy = csp_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://unpkg.com https://cdn.jsdelivr.net https://apis.google.com "
            "https://maps.googleapis.com https://www.gstatic.com; "
            "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://api.openweathermap.org "
            "https://apis.data.go.kr https://dapi.kakao.com "
            "https://api.openai.com https://fcm.googleapis.com "
            "https://firebase.googleapis.com https://firebaseinstallations.googleapis.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Clickjacking Protection
        response.headers["X-Frame-Options"] = "DENY"

        # MIME Type Sniffing Protection
        response.headers["X-Content-Type-Options"] = "nosniff"

        # CSP (Content Security Policy)
        response.headers["Content-Security-Policy"] = self.csp_policy

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS (HTTPS Strict Transport Security) - Only active in HTTPS environments
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(self), " "microphone=(), " "camera=(), " "payment=()"
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate Limiting middleware (simple memory-based implementation)"""

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {client_ip: [(timestamp, count), ...]}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import time

        from starlette.responses import JSONResponse

        client_ip = request.client.host
        current_time = time.time()

        # Cleanup: Remove old request records
        if client_ip in self.requests:
            self.requests[client_ip] = [
                (timestamp, count)
                for timestamp, count in self.requests[client_ip]
                if current_time - timestamp < self.window_seconds
            ]

        # Calculate current client's request count
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        current_requests = sum(count for _, count in self.requests[client_ip])

        # Rate limit check
        if current_requests >= self.max_requests:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_seconds} seconds.",
                    "retry_after": self.window_seconds,
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + self.window_seconds)),
                },
            )
            return response

        # Add request record
        self.requests[client_ip].append((current_time, 1))

        response = await call_next(request)

        # Add rate limit headers
        remaining = max(0, self.max_requests - current_requests - 1)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(current_time + self.window_seconds)
        )

        return response


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced CORS security middleware"""

    def __init__(self, app, allowed_origins: list = None, production: bool = False):
        super().__init__(app)
        self.production = production

        if production:
            # 프로덕션 환경에서는 특정 도메인만 허용
            self.allowed_origins = allowed_origins or [
                "https://wf-dev.seongjunlee.dev",
                "https://wf-admin-dev.seongjunlee.dev",
                "https://wf-admin-api-dev.seongjunlee.dev",
            ]
        else:
            # 개발 환경에서는 로컬호스트 허용
            self.allowed_origins = allowed_origins or [
                "http://localhost:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
                "http://127.0.0.1:9000",
            ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("origin")

        response = await call_next(request)

        # Origin validation
        if origin and (origin in self.allowed_origins or not self.production):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif not self.production:
            response.headers["Access-Control-Allow-Origin"] = "*"

        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        )
        response.headers["Access-Control-Allow-Headers"] = (
            "Origin, X-Requested-With, Content-Type, Accept, Authorization, "
            "Cache-Control, Pragma, API-Version, Accept-Version"
        )
        response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours

        return response
