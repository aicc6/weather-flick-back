# 기상청 API 사용 가이드

## 개요

이 프로젝트는 기상청 공공데이터포털 API를 사용하여 국내 날씨 정보를 제공합니다. WeatherAPI와 함께 사용하여 더 정확하고 상세한 날씨 정보를 제공할 수 있습니다.

## 기상청 API 키 발급

### 1. 공공데이터포털 가입

1. [공공데이터포털](https://www.data.go.kr/)에 접속
2. 회원가입 및 로그인

### 2. 기상청 API 신청

다음 API들을 신청해야 합니다:

#### 필수 API

- **단기예보 조회서비스** (VilageFcstInfoService_2.0)
- **중기예보 조회서비스** (MidFcstInfoService)
- **현재날씨 조회서비스** (VilageFcstInfoService_2.0)
- **특보 조회서비스** (WarningInfoService)

#### 신청 방법

1. 공공데이터포털에서 "기상청" 검색
2. 각 API 서비스별로 신청
3. 승인 후 API 키 발급

### 3. 환경 변수 설정

`.env` 파일에 API 키 추가:

```env
KMA_API_KEY=your_kma_api_key_here
```

## API 엔드포인트

### 1. 지원 도시 목록

```bash
GET /kma/cities
```

### 2. 현재 날씨 조회

```bash
GET /kma/current/{city}
```

- `city`: 도시명 (예: 서울, 부산, 대구 등)
- 인증 필요

### 3. 단기예보 조회 (3일)

```bash
GET /kma/forecast/short/{city}
```

- `city`: 도시명
- 인증 필요

### 4. 중기예보 조회 (3~10일)

```bash
GET /kma/forecast/mid/{city}
```

- `city`: 도시명
- 인증 필요

### 5. 기상특보 조회

```bash
GET /kma/warning/{area}
```

- `area`: 지역명
- 인증 필요

### 6. API 비교

```bash
GET /kma/compare/{city}
```

- WeatherAPI와 기상청 API 데이터 비교
- 인증 필요

### 7. 도시 좌표 조회

```bash
GET /kma/coordinates/{city}
```

- 도시의 격자 좌표(nx, ny) 조회

## 지원되는 도시

### 주요 도시 목록

- 서울 (nx=60, ny=127)
- 부산 (nx=97, ny=74)
- 대구 (nx=89, ny=90)
- 인천 (nx=55, ny=124)
- 광주 (nx=58, ny=74)
- 대전 (nx=67, ny=100)
- 울산 (nx=102, ny=84)
- 세종 (nx=66, ny=103)
- 수원 (nx=60, ny=120)
- 고양 (nx=57, ny=128)
- 용인 (nx=64, ny=119)
- 창원 (nx=89, ny=76)
- 포항 (nx=102, ny=94)
- 제주 (nx=53, ny=38)

## 사용 예시

### 1. 현재 날씨 조회

```bash
curl -X GET "http://localhost:8000/kma/current/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

응답 예시:

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

### 2. 단기예보 조회

```bash
curl -X GET "http://localhost:8000/kma/forecast/short/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. 중기예보 조회

```bash
curl -X GET "http://localhost:8000/kma/forecast/mid/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. API 비교

```bash
curl -X GET "http://localhost:8000/kma/compare/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 테스트

### 테스트 스크립트 실행

```bash
python test_kma_api.py
```

이 스크립트는 다음을 테스트합니다:

1. 지원되는 도시 목록 확인
2. 서울 현재 날씨 조회
3. 서울 단기예보 조회
4. 서울 중기예보 조회
5. 서울 기상특보 조회

## 기상청 API 특징

### 장점

- **정확성**: 기상청 공식 데이터
- **상세성**: 격자 단위 상세 정보
- **실시간성**: 실시간 관측 데이터
- **무료**: 공공데이터로 무료 사용
- **한국어**: 한국어 데이터 제공

### 제한사항

- **요청 제한**: 일 1,000 요청
- **격자 좌표**: nx, ny 좌표 필요
- **지역 제한**: 한국 지역만 지원
- **API 복잡성**: 복잡한 파라미터 구조

### WeatherAPI와의 차이점

| 구분        | 기상청 API     | WeatherAPI         |
| ----------- | -------------- | ------------------ |
| 데이터 출처 | 기상청 공식    | 다국적 기상 데이터 |
| 정확도      | 한국 지역 최고 | 전 세계 균등       |
| 언어        | 한국어         | 다국어 지원        |
| 요청 제한   | 일 1,000회     | 월 1,000,000회     |
| 사용 난이도 | 높음           | 낮음               |
| 비용        | 무료           | 무료/유료          |

## 문제 해결

### 1. API 키 오류

```
기상청 API 오류: 401 Unauthorized
```

- API 키가 올바른지 확인
- API 신청이 승인되었는지 확인

### 2. 도시명 오류

```
지원하지 않는 도시입니다: {city}
```

- 지원되는 도시 목록 확인
- 도시명 철자 확인

### 3. 데이터 없음

```
기상청 API 서비스 불가
```

- 네트워크 연결 확인
- API 서비스 상태 확인

### 4. 기준시간 오류

기상청 API는 특정 시간에만 데이터를 제공합니다:

- 02:00, 05:00, 08:00, 11:00
- 14:00, 17:00, 20:00, 23:00

## 개발 팁

### 1. 격자 좌표 찾기

새로운 도시를 추가하려면 격자 좌표가 필요합니다:

```python
from app.utils.kma_utils import get_nearest_city

# 가장 가까운 도시 찾기
nearest = get_nearest_city(nx, ny)
```

### 2. 데이터 포맷팅

```python
from app.utils.kma_utils import format_weather_data

# 날씨 데이터 포맷팅
formatted_data = format_weather_data(raw_data)
```

### 3. 기준시간 계산

```python
from app.utils.kma_utils import get_base_time

# 기상청 API 기준시간 계산
base_date, base_time = get_base_time()
```

## 추가 정보

- [기상청 공공데이터포털](https://www.data.go.kr/)
- [기상청 API 문서](https://www.data.go.kr/data/15084084/openapi.do)
- [격자 좌표 시스템](https://www.weather.go.kr/w/obs-climate/land/city-obs.do)
