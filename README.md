# Weather Flick Backend API

FastAPI를 사용한 날씨 정보 API 서버입니다. JWT 기반 인증 시스템, WeatherAPI, 기상청 API 연동, 지역 정보 서비스, 네이버 지도 API, 대기질 정보 API, 그리고 강력한 관리자 기능을 포함합니다.

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

# 카카오 API 설정 (맛집, 장소 검색)
KAKAO_API_KEY=your_kakao_api_key_here
KAKAO_API_URL=https://dapi.kakao.com/v2/local

# 네이버 API 설정 (지도, 블로그, 뉴스 검색)
NAVER_CLIENT_ID=your_naver_client_id_here
NAVER_CLIENT_SECRET=your_naver_client_secret_here
NAVER_API_URL=https://openapi.naver.com/v1

# 구글 Places API 설정 (장소 검색)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_PLACES_URL=https://maps.googleapis.com/maps/api/place

# 공공데이터포털 API 설정 (관광정보)
PUBLIC_DATA_API_KEY=your_public_data_api_key_here
PUBLIC_DATA_API_URL=http://api.visitkorea.or.kr/openapi/service/rest/KorService

# 한국관광공사 API 설정
KOREA_TOURISM_API_KEY=your_korea_tourism_api_key_here
KOREA_TOURISM_API_URL=http://api.visitkorea.or.kr/openapi/service/rest/KorService

# 미세미세 API 설정 (대기질 정보)
MISEMISE_API_KEY=your_misemise_api_key_here
MISEMISE_API_URL=https://www.misemise.co.kr/api
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

#### 카카오 API 키 발급

1. [카카오 개발자 센터](https://developers.kakao.com/)에 가입
2. 애플리케이션 등록
3. REST API 키 발급
4. `.env` 파일의 `KAKAO_API_KEY`에 발급받은 키 입력

#### 네이버 API 키 발급

1. [네이버 개발자 센터](https://developers.naver.com/)에 가입
2. 애플리케이션 등록
3. 다음 API 서비스 신청:
   - 검색 API (지역 검색)
   - 지도 API (웹 서비스용)
4. `.env` 파일의 `NAVER_CLIENT_ID`와 `NAVER_CLIENT_SECRET`에 발급받은 키 입력

#### 한국관광공사 API 키 발급

1. [공공데이터포털](https://www.data.go.kr/)에 가입
2. 한국관광공사 API 신청:
   - 지역기반 관광정보 조회서비스
   - 키워드 검색 조회서비스
3. `.env` 파일의 `KOREA_TOURISM_API_KEY`에 발급받은 키 입력

#### 미세미세 API 키 발급

1. [미세미세](https://www.misemise.co.kr/)에 가입
2. API 서비스 신청
3. API 키 발급
4. `.env` 파일의 `MISEMISE_API_KEY`에 발급받은 키 입력

### 4. 데이터베이스 설정

PostgreSQL 데이터베이스를 설정하고 `.env` 파일에 연결 정보를 추가하세요:

```env
DATABASE_HOST=your_db_host
DATABASE_PORT=5432
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_db_password
DATABASE_NAME=weather_flick
```

### 5. 관리자 계정 생성

```bash
python create_admin.py
```

### 6. 서버 실행

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
- `POST /auth/logout` - 로그아웃
- `GET /auth/me` - 현재 사용자 정보 조회 (인증 필요)
- `PUT /auth/me` - 사용자 프로필 업데이트 (인증 필요)
- `POST /auth/change-password` - 비밀번호 변경 (인증 필요)

### 관리자 API

#### 사용자 관리 (관리자 전용)

- `GET /auth/admin/users` - 모든 사용자 목록 조회
- `GET /auth/admin/users/{user_id}` - 특정 사용자 정보 조회
- `PUT /auth/admin/users/{user_id}` - 사용자 정보 수정 (슈퍼 관리자 전용)
- `DELETE /auth/admin/users/{user_id}` - 사용자 삭제 (슈퍼 관리자 전용)
- `GET /auth/admin/stats` - 관리자 통계 조회
- `GET /auth/admin/activities` - 사용자 활동 로그 조회

#### 관리자 대시보드 (슈퍼 관리자 전용)

- `GET /admin/dashboard` - 대시보드 메인 정보
- `GET /admin/users/analytics` - 사용자 분석 데이터
- `GET /admin/system/health` - 시스템 상태 확인
- `GET /admin/users/search` - 사용자 검색
- `GET /admin/users/{user_id}/activities` - 특정 사용자 활동 로그
- `POST /admin/users/{user_id}/verify` - 사용자 인증 (관리자 수동)
- `POST /admin/users/{user_id}/activate` - 사용자 계정 활성화
- `POST /admin/users/{user_id}/deactivate` - 사용자 계정 비활성화
- `POST /admin/users/{user_id}/promote` - 사용자 역할 승격
- `GET /admin/system/info` - 시스템 정보 조회

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

### 지역 정보 API

- `GET /local/cities` - 지원되는 도시 목록
- `GET /local/cities/{city}/info` - 도시 정보 조회
- `GET /local/restaurants` - 맛집 검색
- `GET /local/transportation` - 교통 정보 검색
- `GET /local/accommodations` - 숙소 정보 검색
- `POST /local/search` - 통합 검색 (인증 필요)
- `GET /local/favorites` - 사용자 즐겨찾기 조회 (인증 필요)
- `POST /local/favorites/{place_type}/{place_id}` - 즐겨찾기 추가 (인증 필요)
- `DELETE /local/favorites/{place_type}/{place_id}` - 즐겨찾기 제거 (인증 필요)
- `POST /local/reviews` - 리뷰 작성 (인증 필요)
- `GET /local/reviews/{place_type}/{place_id}` - 장소별 리뷰 조회
- `GET /local/categories` - 카테고리 목록 조회
- `GET /local/nearby` - 주변 장소 검색 (위치 기반)

### 네이버 지도 API

- `GET /map/search` - 장소 검색
- `GET /map/route` - 경로 안내
- `GET /map/nearby` - 주변 장소 검색
- `GET /map/restaurants/nearby` - 주변 맛집 검색
- `GET /map/hotels/nearby` - 주변 숙소 검색
- `GET /map/transportation/nearby` - 주변 교통 정보 검색
- `GET /map/coordinates/{city}` - 도시의 좌표 정보 조회
- `GET /map/embed` - 지도 임베드 URL 생성
- `GET /map/static` - 정적 지도 이미지 URL 생성
- `GET /map/widget` - 지도 위젯 HTML 생성
- `GET /map/place/{place_id}` - 장소 상세 정보 조회
- `GET /map/search/coordinates` - 좌표 기반 장소 검색
- `GET /map/cities` - 지원되는 도시 목록
- `GET /map/categories` - 검색 카테고리 목록

### 대기질 API

- `GET /air-quality/current/{city}` - 현재 대기질 정보 조회 (인증 필요)
- `GET /air-quality/forecast/{city}` - 대기질 예보 조회 (인증 필요)
- `GET /air-quality/stations/nearby` - 주변 측정소 조회 (인증 필요)
- `GET /air-quality/cities` - 지원되는 도시 목록
- `GET /air-quality/info` - 대기질 정보 안내
- `GET /air-quality/health/{city}` - 대기질 건강 조언 (인증 필요)
- `GET /air-quality/compare/{city}` - 여러 소스의 대기질 정보 비교 (인증 필요)
- `GET /air-quality/trends/{city}` - 대기질 추세 분석 (인증 필요)

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

## 사용법

### 1. 회원가입

```bash
curl -X POST "http://localhost:8000/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "username": "testuser",
       "password": "Password123!"
     }'
```

### 2. 로그인

```bash
curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=user@example.com&password=Password123!"
```

### 3. 관리자 계정 생성

```bash
python create_admin.py
```

### 4. 관리자 통계 조회

```bash
curl -X GET "http://localhost:8000/auth/admin/stats" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 5. WeatherAPI 현재 날씨 조회

```bash
# POST 방식
curl -X POST "http://localhost:8000/weather/current" \
     -H "Content-Type: application/json" \
     -d '{"city": "Seoul", "country": "KR"}'

# GET 방식
curl -X GET "http://localhost:8000/weather/current/Seoul?country=KR"
```

### 6. 기상청 현재 날씨 조회

```bash
curl -X GET "http://localhost:8000/kma/current/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 7. 기상청 단기예보 조회

```bash
curl -X GET "http://localhost:8000/kma/forecast/short/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 8. 기상청 중기예보 조회

```bash
curl -X GET "http://localhost:8000/kma/forecast/mid/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 9. 기상특보 조회

```bash
curl -X GET "http://localhost:8000/kma/warning/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 10. API 비교

```bash
curl -X GET "http://localhost:8000/kma/compare/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 11. 지역 정보 - 맛집 검색

```bash
curl -X GET "http://localhost:8000/local/restaurants?city=서울&category=한식&limit=10"
```

### 12. 지역 정보 - 교통 정보 검색

```bash
curl -X GET "http://localhost:8000/local/transportation?city=서울&transport_type=지하철"
```

### 13. 지역 정보 - 숙소 검색

```bash
curl -X GET "http://localhost:8000/local/accommodations?city=서울&accommodation_type=호텔"
```

### 14. 지역 정보 - 통합 검색

```bash
curl -X POST "http://localhost:8000/local/search" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "city": "서울",
       "category": "restaurant",
       "keyword": "맛집"
     }'
```

### 15. 네이버 지도 - 장소 검색

```bash
curl -X GET "http://localhost:8000/map/search?query=강남역&limit=10"
```

### 16. 네이버 지도 - 주변 맛집 검색

```bash
curl -X GET "http://localhost:8000/map/restaurants/nearby?latitude=37.5665&longitude=126.9780&radius=1000"
```

### 17. 네이버 지도 - 경로 안내

```bash
curl -X GET "http://localhost:8000/map/route?start=강남역&goal=홍대입구&mode=driving"
```

### 18. 네이버 지도 - 지도 임베드 URL 생성

```bash
curl -X GET "http://localhost:8000/map/embed?latitude=37.5665&longitude=126.9780&zoom=15&width=600&height=400"
```

### 19. 대기질 - 현재 대기질 정보 조회

```bash
curl -X GET "http://localhost:8000/air-quality/current/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 20. 대기질 - 대기질 예보 조회

```bash
curl -X GET "http://localhost:8000/air-quality/forecast/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 21. 대기질 - 건강 조언 조회

```bash
curl -X GET "http://localhost:8000/air-quality/health/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 22. 대기질 - 주변 측정소 조회

```bash
curl -X GET "http://localhost:8000/air-quality/stations/nearby?latitude=37.5665&longitude=126.9780&radius=5000" \
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

## 대기질 API 응답 예시

### 현재 대기질

```json
{
  "city": "서울",
  "source": "미세미세",
  "timestamp": "2024-01-01T12:00:00",
  "pm10": {
    "value": 45,
    "grade": "보통",
    "unit": "㎍/㎥"
  },
  "pm25": {
    "value": 25,
    "grade": "보통",
    "unit": "㎍/㎥"
  },
  "o3": {
    "value": 0.03,
    "grade": "좋음",
    "unit": "ppm"
  },
  "no2": {
    "value": 0.02,
    "grade": "좋음",
    "unit": "ppm"
  },
  "co": {
    "value": 0.5,
    "grade": "좋음",
    "unit": "ppm"
  },
  "so2": {
    "value": 0.005,
    "grade": "좋음",
    "unit": "ppm"
  },
  "air_quality_index": {
    "value": 45,
    "grade": "보통",
    "color": "#FFFF00"
  },
  "station_name": "종로구",
  "latitude": 37.5704,
  "longitude": 126.9997
}
```

### 대기질 예보

```json
{
  "city": "서울",
  "source": "공공데이터포털",
  "forecast_date": "2024-01-01",
  "forecasts": [
    {
      "date": "2024-01-01 00:00",
      "pm10_grade": "보통",
      "pm25_grade": "보통",
      "pm10_value": "45",
      "pm25_value": "25"
    },
    {
      "date": "2024-01-01 01:00",
      "pm10_grade": "보통",
      "pm25_grade": "보통",
      "pm10_value": "50",
      "pm25_value": "28"
    }
  ]
}
```

## 프로젝트 구조

```
weather-flick-back/
├── main.py              # 메인 애플리케이션
├── requirements.txt     # 의존성 목록
├── create_admin.py      # 관리자 계정 생성 스크립트
├── test_kma_api.py      # 기상청 API 테스트 스크립트
├── app/
│   ├── __init__.py
│   ├── config.py        # 설정 관리
│   ├── database.py      # 데이터베이스 설정
│   ├── models.py        # 데이터 모델
│   ├── auth.py          # 인증 유틸리티
│   ├── services/
│   │   ├── __init__.py
│   │   ├── weather_service.py      # WeatherAPI 서비스
│   │   ├── kma_weather_service.py  # 기상청 API 서비스
│   │   ├── local_info_service.py   # 지역 정보 서비스
│   │   ├── naver_map_service.py    # 네이버 지도 API 서비스
│   │   └── air_quality_service.py  # 대기질 API 서비스
│   ├── utils/
│   │   ├── __init__.py
│   │   └── kma_utils.py  # 기상청 API 유틸리티
│   └── routers/
│       ├── __init__.py
│       ├── auth.py      # 인증 라우터
│       ├── weather.py   # WeatherAPI 라우터
│       ├── kma_weather.py # 기상청 API 라우터
│       ├── admin.py     # 관리자 라우터
│       ├── local_info.py # 지역 정보 라우터
│       ├── naver_map.py # 네이버 지도 API 라우터
│       └── air_quality.py # 대기질 API 라우터
├── README.md
├── ADMIN_GUIDE.md       # 관리자 기능 가이드
├── KMA_API_GUIDE.md     # 기상청 API 가이드
├── NAVER_MAP_GUIDE.md   # 네이버 지도 API 가이드
└── AIR_QUALITY_GUIDE.md # 대기질 API 가이드
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

### 관리자 권한이 필요한 엔드포인트 추가

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

### 지역 정보 서비스 사용

```python
from app.services.local_info_service import local_info_service

# 맛집 검색
restaurants = await local_info_service.search_restaurants("서울", category="한식")

# 교통 정보 검색
transportation = await local_info_service.search_transportation("서울", transport_type="지하철")

# 숙소 검색
accommodations = await local_info_service.search_accommodations("서울", accommodation_type="호텔")
```

### 네이버 지도 API 서비스 사용

```python
from app.services.naver_map_service import naver_map_service

# 장소 검색
places = await naver_map_service.search_places("강남역")

# 주변 맛집 검색
restaurants = await naver_map_service.search_restaurants_nearby(37.5665, 126.9780, 1000)

# 경로 안내
route = await naver_map_service.get_route_guidance("강남역", "홍대입구")
```

### 대기질 API 서비스 사용

```python
from app.services.air_quality_service import air_quality_service

# 현재 대기질 정보 조회
air_quality = await air_quality_service.get_current_air_quality("서울")

# 대기질 예보 조회
forecast = await air_quality_service.get_air_quality_forecast("서울")

# 주변 측정소 조회
stations = await air_quality_service.get_nearby_stations(37.5665, 126.9780, 5000)
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
- 관리자 계정의 보안을 강화하세요
- 정기적인 보안 감사를 수행하세요

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

### 대기질 API

- **미세미세 API**: 일일 요청 제한 (API 제공업체 정책에 따라 다름)
- **공공데이터포털 API**: 일 1,000 요청
- **내장 데이터**: 제한 없음
- **대기질 등급**: 좋음, 보통, 나쁨, 매우나쁨
- **주요 오염물질**: PM10, PM2.5, O3, NO2, CO, SO2

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

## 대기질 등급 기준

### 미세먼지 (PM10)

| 등급     | 농도 (㎍/㎥) | 색상    | 설명                    |
| -------- | ------------ | ------- | ----------------------- |
| 좋음     | 0-30         | #00E400 | 대기질이 양호한 상태    |
| 보통     | 31-80        | #FFFF00 | 대기질이 보통인 상태    |
| 나쁨     | 81-150       | #FF7E00 | 대기질이 나쁜 상태      |
| 매우나쁨 | 151+         | #FF0000 | 대기질이 매우 나쁜 상태 |

### 초미세먼지 (PM2.5)

| 등급     | 농도 (㎍/㎥) | 색상    | 설명                    |
| -------- | ------------ | ------- | ----------------------- |
| 좋음     | 0-15         | #00E400 | 대기질이 양호한 상태    |
| 보통     | 16-35        | #FFFF00 | 대기질이 보통인 상태    |
| 나쁨     | 36-75        | #FF7E00 | 대기질이 나쁜 상태      |
| 매우나쁨 | 76+          | #FF0000 | 대기질이 매우 나쁜 상태 |

## 추가 문서

- [관리자 기능 가이드](ADMIN_GUIDE.md) - 관리자 기능 상세 사용법
- [기상청 API 가이드](KMA_API_GUIDE.md) - 기상청 API 상세 사용법
- [네이버 지도 API 가이드](NAVER_MAP_GUIDE.md) - 네이버 지도 API 상세 사용법
- [대기질 API 가이드](AIR_QUALITY_GUIDE.md) - 대기질 API 상세 사용법
- [API 문서](http://localhost:8000/docs) - Swagger UI
- [API 문서 (ReDoc)](http://localhost:8000/redoc) - ReDoc
