# Weather Flick Backend API

FastAPI를 사용한 날씨 정보 API 서버입니다. JWT 기반 인증 시스템과 WeatherAPI, 기상청 API 연동을 포함합니다.

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

# 기상청 API 설정
KMA_API_KEY=your_kma_api_key_here
```

### 3. API 키 발급

#### WeatherAPI 키 발급

1. [WeatherAPI](https://www.weatherapi.com/)에 가입
2. 무료 API 키 발급 (월 1,000,000 요청)
3. `.env` 파일의 `WEATHER_API_KEY`에 발급받은 키 입력

#### 기상청 API 키 발급

1. [공공데이터포털](https://www.data.go.kr/)에 가입
2. 기상청 API 신청:
   - 단기예보 조회서비스
   - 중기예보 조회서비스
   - 현재날씨 조회서비스
   - 특보 조회서비스
3. `.env` 파일의 `KMA_API_KEY`에 발급받은 키 입력

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

### WeatherAPI 날씨 API

- `GET /weather/` - 날씨 API 정보
- `POST /weather/current` - 현재 날씨 조회 (POST 요청)
- `GET /weather/current/{city}` - 현재 날씨 조회 (GET 요청)
- `GET /weather/forecast/{city}` - 날씨 예보 조회 (1-14일)
- `GET /weather/cities` - 지원되는 도시 목록
- `GET /weather/favorites` - 사용자 즐겨찾기 조회 (인증 필요)
- `POST /weather/favorites/{city}` - 즐겨찾기 도시 추가 (인증 필요)
- `DELETE /weather/favorites/{city}` - 즐겨찾기 도시 제거 (인증 필요)
- `GET /weather/favorites/weather` - 즐겨찾기 도시들의 날씨 조회 (인증 필요)

### 기상청 API

- `GET /kma/cities` - 기상청 API 지원 도시 목록
- `GET /kma/current/{city}` - 기상청 현재 날씨 조회 (인증 필요)
- `GET /kma/forecast/short/{city}` - 기상청 단기예보 조회 (3일) (인증 필요)
- `GET /kma/forecast/mid/{city}` - 기상청 중기예보 조회 (3~10일) (인증 필요)
- `GET /kma/warning/{area}` - 기상특보 조회 (인증 필요)
- `GET /kma/compare/{city}` - WeatherAPI와 기상청 API 비교 (인증 필요)
- `GET /kma/coordinates/{city}` - 도시의 격자 좌표 조회

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

### 3. WeatherAPI 현재 날씨 조회

```bash
# POST 방식
curl -X POST "http://localhost:8000/weather/current" \
     -H "Content-Type: application/json" \
     -d '{"city": "Seoul", "country": "KR"}'

# GET 방식
curl -X GET "http://localhost:8000/weather/current/Seoul?country=KR"
```

### 4. 기상청 현재 날씨 조회

```bash
curl -X GET "http://localhost:8000/kma/current/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 5. 기상청 단기예보 조회

```bash
curl -X GET "http://localhost:8000/kma/forecast/short/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 6. 기상청 중기예보 조회

```bash
curl -X GET "http://localhost:8000/kma/forecast/mid/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 7. 기상특보 조회

```bash
curl -X GET "http://localhost:8000/kma/warning/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 8. API 비교

```bash
curl -X GET "http://localhost:8000/kma/compare/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 기상청 API 응답 예시

### 현재 날씨

```json
{
  "city": "서울",
  "source": "기상청",
  "coordinates": { "nx": 60, "ny": 127 },
  "weather": {
    "nx": 60,
    "ny": 127,
    "temperature": 22.5,
    "humidity": 65,
    "rainfall": 0,
    "wind_speed": 12.5,
    "wind_direction": "남동",
    "pressure": 1013.0,
    "visibility": 10.0,
    "cloud_cover": 0,
    "precipitation_type": "없음"
  }
}
```

### 단기예보

```json
{
  "city": "서울",
  "source": "기상청",
  "forecast_type": "단기예보 (3일)",
  "coordinates": { "nx": 60, "ny": 127 },
  "forecast": {
    "nx": 60,
    "ny": 127,
    "forecast": [
      {
        "date": "20240101",
        "max_temp": 25.0,
        "min_temp": 18.0,
        "avg_temp": 21.5,
        "rainfall_probability": 20,
        "weather_description": "맑음",
        "wind_speed": 15.0
      }
    ]
  }
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
│   │   ├── weather_service.py      # WeatherAPI 서비스
│   │   └── kma_weather_service.py  # 기상청 API 서비스
│   └── routers/
│       ├── __init__.py
│       ├── auth.py      # 인증 라우터
│       ├── weather.py   # WeatherAPI 라우터
│       └── kma_weather.py # 기상청 API 라우터
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

### 기상청 API 서비스 사용

```python
from app.services.kma_weather_service import kma_weather_service

# 현재 날씨 조회 (서울: nx=60, ny=127)
weather = await kma_weather_service.get_current_weather(60, 127)

# 단기예보 조회
forecast = await kma_weather_service.get_short_forecast(60, 127)

# 중기예보 조회 (서울: regId=11B10101)
mid_forecast = await kma_weather_service.get_mid_forecast("11B10101")
```

### 설정 추가

1. `app/config.py`의 `Settings` 클래스에 새 설정 추가
2. `.env` 파일에 해당 환경 변수 추가

## 보안 고려사항

- 프로덕션 환경에서는 `SECRET_KEY`를 강력한 랜덤 문자열로 변경하세요
- CORS 설정을 실제 프론트엔드 도메인으로 제한하세요
- 비밀번호 정책을 강화하세요 (최소 길이, 특수문자 등)
- 이메일 인증 기능을 추가하세요
- WeatherAPI 키와 기상청 API 키를 환경 변수로 안전하게 관리하세요

## API 제한사항

### WeatherAPI

- 무료 플랜: 월 1,000,000 요청
- 예보: 최대 14일
- 대기질 정보: 별도 요청 필요
- 지역화: 한국어 지원

### 기상청 API

- 무료 플랜: 일 1,000 요청
- 단기예보: 3일
- 중기예보: 3~10일
- 현재날씨: 실시간
- 특보: 기상특보 발표 시
- 격자 좌표 기반 (nx, ny)
- 지역 코드 기반 (regId)

## 기상청 API 격자 좌표

기상청 API는 격자 좌표(nx, ny)를 사용합니다. 주요 도시의 좌표:

- 서울: nx=60, ny=127
- 부산: nx=97, ny=74
- 대구: nx=89, ny=90
- 인천: nx=55, ny=124
- 광주: nx=58, ny=74
- 대전: nx=67, ny=100
- 울산: nx=102, ny=84
- 세종: nx=66, ny=103
- 수원: nx=60, ny=120
- 고양: nx=57, ny=128
- 용인: nx=64, ny=119
- 창원: nx=89, ny=76
- 포항: nx=102, ny=94
- 제주: nx=53, ny=38
