# Weather Flick Backend API

FastAPI를 사용한 날씨 정보 API 서버입니다. JWT 기반 인증 시스템과 WeatherAPI 연동을 포함합니다.

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# 애플리케이션 설정
APP_NAME=Weather Flick API
APP_VERSION=1.0.0
DEBUG=false

# 서버 설정
HOST=0.0.0.0
PORT=8000

# CORS 설정
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# JWT 설정
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# WeatherAPI 설정
WEATHER_API_KEY=your_weather_api_key_here
WEATHER_API_URL=http://api.weatherapi.com/v1
```

### 3. WeatherAPI 키 발급

1. [WeatherAPI](https://www.weatherapi.com/)에 가입
2. 무료 API 키 발급 (월 1,000,000 요청)
3. `.env` 파일의 `WEATHER_API_KEY`에 발급받은 키 입력

### 4. 서버 실행

```bash
# 개발 모드
uvicorn main:app --reload

# 또는
python main.py
```

## API 엔드포인트

### 기본 엔드포인트

- `GET /` - API 상태 확인
- `GET /health` - 헬스 체크
- `GET /docs` - Swagger UI 문서
- `GET /redoc` - ReDoc 문서

### 인증 API

- `POST /auth/register` - 회원가입
- `POST /auth/login` - 로그인
- `GET /auth/me` - 현재 사용자 정보 조회 (인증 필요)
- `GET /auth/profile` - 사용자 프로필 조회 (인증 필요)

### 날씨 API

- `GET /weather/` - 날씨 API 정보
- `POST /weather/current` - 현재 날씨 조회 (POST 요청)
- `GET /weather/current/{city}` - 현재 날씨 조회 (GET 요청)
- `GET /weather/forecast/{city}` - 날씨 예보 조회 (1-14일)
- `GET /weather/cities` - 지원되는 도시 목록
- `GET /weather/favorites` - 사용자 즐겨찾기 조회 (인증 필요)
- `POST /weather/favorites/{city}` - 즐겨찾기 도시 추가 (인증 필요)
- `DELETE /weather/favorites/{city}` - 즐겨찾기 도시 제거 (인증 필요)
- `GET /weather/favorites/weather` - 즐겨찾기 도시들의 날씨 조회 (인증 필요)

## 사용법

### 1. 회원가입

```bash
curl -X POST "http://localhost:8000/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "username": "testuser",
       "password": "password123"
     }'
```

### 2. 로그인

```bash
curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=user@example.com&password=password123"
```

### 3. 현재 날씨 조회

```bash
# POST 방식
curl -X POST "http://localhost:8000/weather/current" \
     -H "Content-Type: application/json" \
     -d '{"city": "Seoul", "country": "KR"}'

# GET 방식
curl -X GET "http://localhost:8000/weather/current/Seoul?country=KR"
```

### 4. 날씨 예보 조회

```bash
curl -X GET "http://localhost:8000/weather/forecast/Seoul?days=7&country=KR"
```

### 5. 인증이 필요한 API 호출

```bash
curl -X GET "http://localhost:8000/auth/me" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## WeatherAPI 응답 예시

### 현재 날씨

```json
{
  "city": "Seoul",
  "country": "South Korea",
  "region": "Seoul",
  "temperature": 22.5,
  "feels_like": 24.2,
  "description": "Partly cloudy",
  "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png",
  "humidity": 65,
  "wind_speed": 12.5,
  "wind_direction": "SE",
  "pressure": 1013.0,
  "visibility": 10.0,
  "uv_index": 5.0,
  "last_updated": "2024-01-01 12:00"
}
```

### 날씨 예보

```json
{
  "city": "Seoul",
  "country": "South Korea",
  "region": "Seoul",
  "forecast": [
    {
      "date": "2024-01-01",
      "max_temp": 25.0,
      "min_temp": 18.0,
      "avg_temp": 21.5,
      "description": "Partly cloudy",
      "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png",
      "humidity": 65,
      "chance_of_rain": 20,
      "chance_of_snow": 0,
      "uv_index": 5.0
    }
  ]
}
```

## 프로젝트 구조

```
weather-flick-back/
├── main.py              # 메인 애플리케이션
├── requirements.txt     # 의존성 목록
├── app/
│   ├── __init__.py
│   ├── config.py        # 설정 관리
│   ├── database.py      # 데이터베이스 설정
│   ├── models.py        # 데이터 모델
│   ├── auth.py          # 인증 유틸리티
│   ├── services/
│   │   ├── __init__.py
│   │   └── weather_service.py  # WeatherAPI 서비스
│   └── routers/
│       ├── __init__.py
│       ├── auth.py      # 인증 라우터
│       └── weather.py   # 날씨 관련 라우터
└── README.md
```

## 개발 가이드

### 새로운 라우터 추가

1. `app/routers/` 디렉토리에 새 라우터 파일 생성
2. `main.py`에서 라우터 import 및 include
3. API 문서는 자동으로 생성됩니다

### 인증이 필요한 엔드포인트 추가

```python
from app.auth import get_current_active_user
from app.models import User

@router.get("/protected")
async def protected_endpoint(current_user: User = Depends(get_current_active_user)):
    return {"message": "This is protected", "user": current_user.email}
```

### WeatherAPI 서비스 사용

```python
from app.services.weather_service import weather_service

# 현재 날씨 조회
weather = await weather_service.get_current_weather("Seoul", "KR")

# 예보 조회
forecast = await weather_service.get_forecast("Seoul", days=7, country="KR")
```

### 설정 추가

1. `app/config.py`의 `Settings` 클래스에 새 설정 추가
2. `.env` 파일에 해당 환경 변수 추가

## 보안 고려사항

- 프로덕션 환경에서는 `SECRET_KEY`를 강력한 랜덤 문자열로 변경하세요
- CORS 설정을 실제 프론트엔드 도메인으로 제한하세요
- 비밀번호 정책을 강화하세요 (최소 길이, 특수문자 등)
- 이메일 인증 기능을 추가하세요
- WeatherAPI 키를 환경 변수로 안전하게 관리하세요

## WeatherAPI 제한사항

- 무료 플랜: 월 1,000,000 요청
- 예보: 최대 14일
- 대기질 정보: 별도 요청 필요
- 지역화: 한국어 지원
