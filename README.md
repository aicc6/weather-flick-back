# Weather Flick Backend API

FastAPI를 사용한 날씨 정보 API 서버입니다.

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
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# 외부 API 설정 (향후 사용)
WEATHER_API_KEY=your_api_key_here
WEATHER_API_URL=https://api.weatherapi.com/v1
```

### 3. 서버 실행

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

### 날씨 API

- `GET /weather/` - 날씨 API 정보
- `POST /weather/current` - 현재 날씨 조회
- `GET /weather/cities` - 지원되는 도시 목록

## 프로젝트 구조

```
weather-flick-back/
├── main.py              # 메인 애플리케이션
├── requirements.txt     # 의존성 목록
├── app/
│   ├── __init__.py
│   ├── config.py        # 설정 관리
│   └── routers/
│       ├── __init__.py
│       └── weather.py   # 날씨 관련 라우터
└── README.md
```

## 개발 가이드

### 새로운 라우터 추가

1. `app/routers/` 디렉토리에 새 라우터 파일 생성
2. `main.py`에서 라우터 import 및 include
3. API 문서는 자동으로 생성됩니다

### 설정 추가

1. `app/config.py`의 `Settings` 클래스에 새 설정 추가
2. `.env` 파일에 해당 환경 변수 추가
