# 대기질 API 사용 가이드

## 개요

Weather Flick API는 [미세미세](https://www.misemise.co.kr/) API와 공공데이터포털 API를 통합하여 실시간 대기질 정보, 예보, 건강 조언 등을 제공합니다.

## API 키 발급

### 1. 미세미세 API 키 발급

1. [미세미세](https://www.misemise.co.kr/)에 가입
2. API 서비스 신청
3. API 키 발급
4. `.env` 파일의 `MISEMISE_API_KEY`에 발급받은 키 입력

### 2. 공공데이터포털 API 키 발급

1. [공공데이터포털](https://www.data.go.kr/)에 가입
2. 다음 API 서비스 신청:
   - 실시간 대기질 조회서비스
   - 대기질 예보 조회서비스
   - 측정소 정보 조회서비스
3. `.env` 파일의 `PUBLIC_DATA_API_KEY`에 발급받은 키 입력

### 3. 환경 변수 설정

`.env` 파일에 다음 내용을 추가하세요:

```env
# 미세미세 API 설정 (대기질 정보)
MISEMISE_API_KEY=your_misemise_api_key_here
MISEMISE_API_URL=https://www.misemise.co.kr/api

# 공공데이터포털 API 설정 (대기질 정보)
PUBLIC_DATA_API_KEY=your_public_data_api_key_here
PUBLIC_DATA_API_URL=http://apis.data.go.kr/B552584
```

## API 엔드포인트

### 기본 대기질 API

#### 1. 현재 대기질 정보 조회

```bash
curl -X GET "http://localhost:8000/air-quality/current/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**응답 예시:**

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

#### 2. 대기질 예보 조회

```bash
curl -X GET "http://localhost:8000/air-quality/forecast/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**응답 예시:**

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

#### 3. 주변 측정소 조회

```bash
curl -X GET "http://localhost:8000/air-quality/stations/nearby?latitude=37.5665&longitude=126.9780&radius=5000" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**응답 예시:**

```json
{
  "stations": [
    {
      "station_name": "종로구",
      "address": "서울특별시 종로구",
      "latitude": 37.5704,
      "longitude": 126.9997,
      "distance": 0.5
    },
    {
      "station_name": "중구",
      "address": "서울특별시 중구",
      "latitude": 37.5636,
      "longitude": 126.9834,
      "distance": 1.2
    }
  ],
  "total": 2,
  "center": {
    "latitude": 37.5665,
    "longitude": 126.978
  },
  "radius": 5000
}
```

### 정보 및 조언 API

#### 1. 대기질 정보 안내

```bash
curl -X GET "http://localhost:8000/air-quality/info"
```

**응답 예시:**

```json
{
  "description": "대기질 정보 API",
  "sources": [
    {
      "name": "미세미세",
      "description": "미세미세 API를 통한 실시간 대기질 정보",
      "priority": 1
    },
    {
      "name": "공공데이터포털",
      "description": "환경부 대기질 정보 API",
      "priority": 2
    },
    {
      "name": "내장 데이터",
      "description": "기본 대기질 정보 (API 키 없을 때)",
      "priority": 3
    }
  ],
  "pollutants": {
    "pm10": {
      "name": "미세먼지 (PM10)",
      "unit": "㎍/㎥",
      "description": "지름 10마이크로미터 이하의 미세먼지"
    },
    "pm25": {
      "name": "초미세먼지 (PM2.5)",
      "unit": "㎍/㎥",
      "description": "지름 2.5마이크로미터 이하의 초미세먼지"
    }
  },
  "grades": {
    "좋음": {
      "color": "#00E400",
      "description": "대기질이 양호한 상태"
    },
    "보통": {
      "color": "#FFFF00",
      "description": "대기질이 보통인 상태"
    },
    "나쁨": {
      "color": "#FF7E00",
      "description": "대기질이 나쁜 상태"
    },
    "매우나쁨": {
      "color": "#FF0000",
      "description": "대기질이 매우 나쁜 상태"
    }
  }
}
```

#### 2. 대기질 건강 조언

```bash
curl -X GET "http://localhost:8000/air-quality/health/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**응답 예시:**

```json
{
  "city": "서울",
  "air_quality_grade": "보통",
  "timestamp": "2024-01-01T12:00:00",
  "health_advice": {
    "general": "대기질이 보통입니다. 대부분의 사람들에게는 영향이 없습니다.",
    "sensitive_groups": "민감군은 장시간 실외활동을 줄이는 것이 좋습니다.",
    "activities": ["야외운동", "등산", "자전거", "산책"],
    "recommendations": ["정상적인 실외활동 가능", "민감군은 주의"]
  },
  "current_data": {
    "pm10": { "value": 45, "grade": "보통", "unit": "㎍/㎥" },
    "pm25": { "value": 25, "grade": "보통", "unit": "㎍/㎥" }
  }
}
```

### 분석 API

#### 1. 여러 소스 비교

```bash
curl -X GET "http://localhost:8000/air-quality/compare/서울" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**응답 예시:**

```json
{
  "city": "서울",
  "timestamp": "2024-01-01T12:00:00",
  "sources": {
    "misemise": {
      "pm10": { "value": 45, "grade": "보통" },
      "pm25": { "value": 25, "grade": "보통" }
    },
    "public_data": {
      "pm10": { "value": 48, "grade": "보통" },
      "pm25": { "value": 27, "grade": "보통" }
    },
    "local_data": {
      "pm10": { "value": 45, "grade": "보통" },
      "pm25": { "value": 25, "grade": "보통" }
    }
  },
  "summary": {
    "available_sources": 3,
    "primary_source": "misemise"
  }
}
```

#### 2. 대기질 추세 분석

```bash
curl -X GET "http://localhost:8000/air-quality/trends/서울?days=7" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**응답 예시:**

```json
{
  "city": "서울",
  "period": "7일",
  "trends": [
    {
      "date": "2024-01-01",
      "pm10": { "value": 45, "grade": "보통" },
      "pm25": { "value": 25, "grade": "보통" }
    },
    {
      "date": "2023-12-31",
      "pm10": { "value": 55, "grade": "보통" },
      "pm25": { "value": 30, "grade": "보통" }
    }
  ],
  "summary": {
    "avg_pm10": 50.0,
    "avg_pm25": 27.5,
    "best_day": "2024-01-01",
    "worst_day": "2023-12-31"
  }
}
```

### 기타 API

#### 1. 지원 도시 목록

```bash
curl -X GET "http://localhost:8000/air-quality/cities"
```

**응답 예시:**

```json
{
  "cities": [
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "수원",
    "고양",
    "용인",
    "창원",
    "포항",
    "제주"
  ]
}
```

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

## 오염물질 정보

### 주요 오염물질

1. **PM10 (미세먼지)**

   - 지름 10마이크로미터 이하의 미세먼지
   - 호흡기 질환 유발 가능
   - 단위: ㎍/㎥

2. **PM2.5 (초미세먼지)**

   - 지름 2.5마이크로미터 이하의 초미세먼지
   - 폐 깊숙이 침투하여 건강에 더 큰 영향
   - 단위: ㎍/㎥

3. **O3 (오존)**

   - 지표면 오존 농도
   - 광화학 스모그의 주요 성분
   - 단위: ppm

4. **NO2 (이산화질소)**

   - 자동차 배기가스의 주요 성분
   - 호흡기 자극 유발
   - 단위: ppm

5. **CO (일산화탄소)**

   - 불완전 연소 시 생성
   - 혈액의 산소 운반 능력 저하
   - 단위: ppm

6. **SO2 (이산화황)**
   - 화석연료 연소 시 생성
   - 호흡기 자극 및 산성비 원인
   - 단위: ppm

## 건강 조언

### 대기질 등급별 건강 조언

#### 좋음 (0-30)

- **일반인**: 정상적인 실외활동 가능
- **민감군**: 정상적인 실외활동 가능
- **권장 활동**: 야외운동, 등산, 자전거, 산책

#### 보통 (31-80)

- **일반인**: 정상적인 실외활동 가능
- **민감군**: 장시간 실외활동 줄이기
- **권장 활동**: 야외운동, 등산, 자전거, 산책

#### 나쁨 (81-150)

- **일반인**: 실외활동 줄이기
- **민감군**: 실외활동 피하기
- **권장 활동**: 가벼운 산책, 짧은 실외활동
- **주의사항**: 마스크 착용, 창문 닫기

#### 매우나쁨 (151+)

- **일반인**: 실외활동 금지
- **민감군**: 실외활동 금지
- **권장 활동**: 실내활동만
- **주의사항**: 마스크 필수, 공기청정기 사용

## 프론트엔드 연동 예시

### 1. JavaScript에서 API 호출

```javascript
// 현재 대기질 정보 조회
async function getCurrentAirQuality(city) {
  const response = await fetch(`/air-quality/current/${city}`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
    },
  });
  const data = await response.json();
  return data;
}

// 대기질 예보 조회
async function getAirQualityForecast(city) {
  const response = await fetch(`/air-quality/forecast/${city}`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
    },
  });
  const data = await response.json();
  return data;
}

// 건강 조언 조회
async function getHealthAdvice(city) {
  const response = await fetch(`/air-quality/health/${city}`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
    },
  });
  const data = await response.json();
  return data;
}
```

### 2. React 컴포넌트 예시

```jsx
import React, { useState, useEffect } from "react";

const AirQualityWidget = ({ city }) => {
  const [airQuality, setAirQuality] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAirQuality = async () => {
      try {
        const data = await getCurrentAirQuality(city);
        setAirQuality(data);
      } catch (error) {
        console.error("대기질 정보 조회 실패:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchAirQuality();
  }, [city]);

  if (loading) return <div>로딩 중...</div>;
  if (!airQuality) return <div>데이터를 불러올 수 없습니다.</div>;

  const { pm10, pm25, air_quality_index } = airQuality;

  return (
    <div className="air-quality-widget">
      <h3>{city} 대기질</h3>
      <div
        className="aqi-display"
        style={{ backgroundColor: air_quality_index.color }}
      >
        <div className="aqi-value">{air_quality_index.value}</div>
        <div className="aqi-grade">{air_quality_index.grade}</div>
      </div>
      <div className="pollutants">
        <div className="pollutant">
          <span>PM10: {pm10.value} ㎍/㎥</span>
          <span className={`grade ${pm10.grade}`}>{pm10.grade}</span>
        </div>
        <div className="pollutant">
          <span>PM2.5: {pm25.value} ㎍/㎥</span>
          <span className={`grade ${pm25.grade}`}>{pm25.grade}</span>
        </div>
      </div>
    </div>
  );
};

export default AirQualityWidget;
```

### 3. CSS 스타일 예시

```css
.air-quality-widget {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  max-width: 300px;
}

.aqi-display {
  text-align: center;
  padding: 20px;
  border-radius: 8px;
  color: white;
  margin: 16px 0;
}

.aqi-value {
  font-size: 2em;
  font-weight: bold;
}

.aqi-grade {
  font-size: 1.2em;
  margin-top: 8px;
}

.pollutants {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pollutant {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.grade {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.9em;
  font-weight: bold;
}

.grade.좋음 {
  background-color: #00e400;
  color: white;
}
.grade.보통 {
  background-color: #ffff00;
  color: black;
}
.grade.나쁨 {
  background-color: #ff7e00;
  color: white;
}
.grade.매우나쁨 {
  background-color: #ff0000;
  color: white;
}
```

## 제한사항

### API 제한

- **미세미세 API**: 일일 요청 제한 (API 제공업체 정책에 따라 다름)
- **공공데이터포털 API**: 일 1,000 요청
- **내장 데이터**: 제한 없음

### 사용 시 주의사항

- API 키는 클라이언트에 노출되지 않도록 주의
- 대기질 데이터는 실시간으로 변동될 수 있음
- 민감군(어린이, 노인, 호흡기 질환자)에게 특별한 주의 필요
- 대기질이 나쁠 때는 실외활동을 줄이는 것이 좋음

## 문제 해결

### 1. API 키 오류

```
"error": "API 키가 설정되지 않았습니다."
```

- 환경 변수 확인
- API 키 발급 상태 확인

### 2. 데이터 없음

```
"error": "Air quality data for city '도시명' not found"
```

- 지원되는 도시 목록 확인
- API 서비스 상태 확인

### 3. 인증 오류

```
"error": "Not authenticated"
```

- 로그인 상태 확인
- 액세스 토큰 유효성 확인

## 추가 기능

### 1. 실시간 알림

- 대기질 등급 변경 시 푸시 알림
- 일일 대기질 리포트
- 건강 조언 알림

### 2. 데이터 시각화

- 대기질 추세 그래프
- 지역별 대기질 비교
- 시간대별 대기질 변화

### 3. 개인화 기능

- 관심 지역 설정
- 개인 건강 상태에 따른 맞춤 조언
- 대기질 기반 활동 계획 추천

이 가이드를 통해 대기질 API를 효과적으로 활용할 수 있습니다.
