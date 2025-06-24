# 관리자 기능 사용 가이드

## 개요

Weather Flick API는 강력한 관리자 기능을 제공하여 사용자 관리, 시스템 모니터링, 활동 로깅 등을 수행할 수 있습니다.

## 사용자 역할 (User Roles)

### 1. USER (일반 사용자)

- 기본 사용자 역할
- 날씨 정보 조회 가능
- 프로필 관리 가능

### 2. MODERATOR (중간 관리자)

- 사용자 관리 (조회, 수정)
- 활동 로그 조회
- 통계 조회

### 3. ADMIN (슈퍼 관리자)

- 모든 관리자 기능 사용 가능
- 사용자 삭제
- 시스템 관리
- 역할 관리

## 관리자 계정 생성

### 스크립트를 사용한 생성

```bash
python create_admin.py
```

### 수동 생성 (데이터베이스 직접 접근)

```sql
INSERT INTO users (email, username, hashed_password, role, is_active, is_verified)
VALUES ('admin@example.com', 'admin', 'hashed_password', 'admin', true, true);
```

## API 엔드포인트

### 인증 관련 API

#### 1. 로그인

```bash
curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin@example.com&password=your_password"
```

#### 2. 로그아웃

```bash
curl -X POST "http://localhost:8000/auth/logout" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 3. 비밀번호 변경

```bash
curl -X POST "http://localhost:8000/auth/change-password" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "current_password": "old_password",
       "new_password": "new_strong_password"
     }'
```

### 사용자 관리 API (관리자 전용)

#### 1. 모든 사용자 목록 조회

```bash
curl -X GET "http://localhost:8000/auth/admin/users?skip=0&limit=100" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 2. 특정 사용자 정보 조회

```bash
curl -X GET "http://localhost:8000/auth/admin/users/1" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 3. 사용자 정보 수정 (슈퍼 관리자 전용)

```bash
curl -X PUT "http://localhost:8000/auth/admin/users/1" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "new_username",
       "is_active": true,
       "role": "moderator"
     }'
```

#### 4. 사용자 삭제 (슈퍼 관리자 전용)

```bash
curl -X DELETE "http://localhost:8000/auth/admin/users/1" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 5. 관리자 통계 조회

```bash
curl -X GET "http://localhost:8000/auth/admin/stats" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 6. 사용자 활동 로그 조회

```bash
curl -X GET "http://localhost:8000/auth/admin/activities?skip=0&limit=100" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 관리자 대시보드 API (슈퍼 관리자 전용)

#### 1. 대시보드 메인 정보

```bash
curl -X GET "http://localhost:8000/admin/dashboard" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 2. 사용자 분석 데이터

```bash
curl -X GET "http://localhost:8000/admin/users/analytics?period=week" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 3. 시스템 상태 확인

```bash
curl -X GET "http://localhost:8000/admin/system/health" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 4. 사용자 검색

```bash
curl -X GET "http://localhost:8000/admin/users/search?q=search_term" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 5. 특정 사용자 활동 로그

```bash
curl -X GET "http://localhost:8000/admin/users/1/activities" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 6. 사용자 인증 (관리자 수동)

```bash
curl -X POST "http://localhost:8000/admin/users/1/verify" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 7. 사용자 계정 활성화/비활성화

```bash
# 활성화
curl -X POST "http://localhost:8000/admin/users/1/activate" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 비활성화
curl -X POST "http://localhost:8000/admin/users/1/deactivate" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 8. 사용자 역할 승격

```bash
curl -X POST "http://localhost:8000/admin/users/1/promote?role=moderator" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 9. 시스템 정보 조회

```bash
curl -X GET "http://localhost:8000/admin/system/info" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 응답 예시

### 관리자 통계

```json
{
  "total_users": 150,
  "active_users": 120,
  "verified_users": 100,
  "admin_users": 3,
  "moderator_users": 5,
  "today_logins": 45,
  "this_week_logins": 280,
  "this_month_logins": 1200
}
```

### 대시보드 정보

```json
{
  "user_stats": {
    "total_users": 150,
    "active_users": 120,
    "new_users_today": 5,
    "new_users_week": 25,
    "role_distribution": {
      "user": 142,
      "moderator": 5,
      "admin": 3
    }
  },
  "login_stats": {
    "today_logins": 45,
    "this_week_logins": 280,
    "this_month_logins": 1200
  },
  "activity_stats": {
    "activity_distribution": {
      "login": 1200,
      "logout": 1150,
      "api_call": 5000
    }
  },
  "recent_activities": [
    {
      "id": 1,
      "user_id": 1,
      "activity_type": "login",
      "description": "User logged in from 192.168.1.100",
      "ip_address": "192.168.1.100",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

## 보안 고려사항

### 1. 비밀번호 정책

- 최소 8자 이상
- 대문자, 소문자, 숫자, 특수문자 포함
- 강도 검사 자동 수행

### 2. 권한 관리

- 역할 기반 접근 제어 (RBAC)
- 최소 권한 원칙 적용
- 관리자 권한 분리

### 3. 활동 로깅

- 모든 관리자 활동 로깅
- IP 주소 및 사용자 에이전트 기록
- 감사 추적 가능

### 4. 토큰 관리

- JWT 토큰 사용
- 토큰 만료 시간 설정
- 역할 정보 포함

## 모니터링 및 알림

### 1. 시스템 상태 모니터링

- 데이터베이스 연결 상태
- 외부 API 상태 (WeatherAPI, 기상청 API)
- 시스템 리소스 사용량

### 2. 사용자 활동 모니터링

- 로그인 패턴 분석
- 비정상적인 활동 감지
- API 사용량 추적

### 3. 성능 모니터링

- 응답 시간 측정
- 에러율 추적
- 리소스 사용량 모니터링

## 문제 해결

### 1. 권한 오류

```
403 Forbidden: Not enough permissions
```

- 사용자 역할 확인
- 필요한 권한 확인

### 2. 토큰 만료

```
401 Unauthorized: Could not validate credentials
```

- 토큰 재발급 필요
- 로그인 다시 수행

### 3. 데이터베이스 오류

```
500 Internal Server Error
```

- 데이터베이스 연결 확인
- 로그 확인

## 개발 팁

### 1. 관리자 계정 생성

```python
from app.models import User, UserRole
from app.auth import get_password_hash

admin_user = User(
    email="admin@example.com",
    username="admin",
    hashed_password=get_password_hash("strong_password"),
    role=UserRole.ADMIN,
    is_active=True,
    is_verified=True
)
```

### 2. 권한 검증

```python
from app.auth import get_current_admin_user, get_current_super_admin_user

# 중간 관리자 권한
@router.get("/moderator-only")
async def moderator_endpoint(current_user: User = Depends(get_current_admin_user)):
    return {"message": "Moderator access"}

# 슈퍼 관리자 권한
@router.get("/admin-only")
async def admin_endpoint(current_user: User = Depends(get_current_super_admin_user)):
    return {"message": "Admin access"}
```

### 3. 활동 로깅

```python
from app.auth import log_user_activity

log_user_activity(
    db=db,
    user_id=current_user.id,
    activity_type="admin_action",
    description="User management action",
    ip_address=request.client.host,
    user_agent=request.headers.get("User-Agent")
)
```

## 추가 기능

### 1. 이메일 알림

- 사용자 가입 알림
- 관리자 활동 알림
- 시스템 오류 알림

### 2. 백업 및 복구

- 사용자 데이터 백업
- 설정 백업
- 복구 기능

### 3. API 문서

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

이 가이드를 통해 Weather Flick API의 관리자 기능을 효과적으로 활용할 수 있습니다.
