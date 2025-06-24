# 네이버 지도 API 사용 가이드

## 개요

Weather Flick API는 네이버 지도 API를 통합하여 지도 표시, 장소 검색, 경로 안내, 주변 검색 등의 기능을 제공합니다.

## API 키 발급

### 1. 네이버 개발자 센터 가입

1. [네이버 개발자 센터](https://developers.naver.com/)에 가입
2. 애플리케이션 등록
3. 다음 API 서비스 신청:
   - 검색 API (지역 검색)
   - 지도 API (웹 서비스용)

### 2. 환경 변수 설정

`.env` 파일에 다음 내용을 추가하세요:

```env
# 네이버 API 설정
NAVER_CLIENT_ID=your_naver_client_id_here
NAVER_CLIENT_SECRET=your_naver_client_secret_here
NAVER_API_URL=https://openapi.naver.com/v1
```

## API 엔드포인트

### 기본 지도 API

#### 1. 장소 검색

```bash
curl -X GET "http://localhost:8000/map/search?query=강남역&limit=10"
```

**응답 예시:**

```json
{
  "places": [
    {
      "title": "강남역",
      "address": "서울특별시 강남구 역삼동",
      "road_address": "서울특별시 강남구 강남대로 396",
      "category": "지하철역",
      "description": "서울 지하철 2호선 강남역",
      "telephone": "02-6110-1234",
      "mapx": 127.0276,
      "mapy": 37.498,
      "source": "네이버"
    }
  ],
  "total": 1,
  "query": "강남역"
}
```

#### 2. 경로 안내

```bash
curl -X GET "http://localhost:8000/map/route?start=강남역&goal=홍대입구&mode=driving"
```

**응답 예시:**

```json
{
  "start": "강남역",
  "goal": "홍대입구",
  "mode": "driving",
  "map_url": "https://map.naver.com/v5/directions/강남역/홍대입구",
  "message": "네이버 지도에서 경로를 확인하세요."
}
```

#### 3. 주변 장소 검색

```bash
curl -X GET "http://localhost:8000/map/nearby?latitude=37.5665&longitude=126.9780&radius=1000&category=맛집"
```

**응답 예시:**

```json
{
  "places": [
    {
      "title": "명동교자",
      "address": "서울특별시 중구 명동10길 29",
      "road_address": "서울특별시 중구 명동10길 29",
      "category": "음식점",
      "description": "유명한 칼국수와 만두",
      "telephone": "02-776-5348",
      "mapx": 126.9834,
      "mapy": 37.5636,
      "source": "네이버"
    }
  ],
  "total": 1,
  "center": {
    "latitude": 37.5665,
    "longitude": 126.978
  },
  "radius": 1000
}
```

### 특화 검색 API

#### 1. 주변 맛집 검색

```bash
curl -X GET "http://localhost:8000/map/restaurants/nearby?latitude=37.5665&longitude=126.9780&radius=1000"
```

#### 2. 주변 숙소 검색

```bash
curl -X GET "http://localhost:8000/map/hotels/nearby?latitude=37.5665&longitude=126.9780&radius=1000"
```

#### 3. 주변 교통 정보 검색

```bash
curl -X GET "http://localhost:8000/map/transportation/nearby?latitude=37.5665&longitude=126.9780&radius=1000"
```

### 지도 표시 API

#### 1. 도시 좌표 조회

```bash
curl -X GET "http://localhost:8000/map/coordinates/서울"
```

**응답 예시:**

```json
{
  "latitude": 37.5665,
  "longitude": 126.978
}
```

#### 2. 지도 임베드 URL 생성

```bash
curl -X GET "http://localhost:8000/map/embed?latitude=37.5665&longitude=126.9780&zoom=15&width=600&height=400"
```

**응답 예시:**

```json
{
  "embed_url": "https://map.naver.com/v5/embed/place/37.5665,126.9780?zoom=15&width=600&height=400",
  "coordinates": {
    "latitude": 37.5665,
    "longitude": 126.978
  },
  "zoom": 15,
  "size": {
    "width": 600,
    "height": 400
  }
}
```

#### 3. 지도 위젯 HTML 생성

```bash
curl -X GET "http://localhost:8000/map/widget?latitude=37.5665&longitude=126.9780&zoom=15&width=600&height=400"
```

**응답 예시:**

```json
{
  "html": "<div id=\"map\" style=\"width:600px;height:400px;\"></div><script type=\"text/javascript\" src=\"https://openapi.map.naver.com/openapi/v3/maps.js?ncpClientId=your_client_id\"></script><script>var map = new naver.maps.Map('map', {center: new naver.maps.LatLng(37.5665, 126.9780), zoom: 15}); var marker = new naver.maps.Marker({position: new naver.maps.LatLng(37.5665, 126.9780), map: map});</script>",
  "coordinates": {
    "latitude": 37.5665,
    "longitude": 126.978
  },
  "zoom": 15,
  "size": {
    "width": 600,
    "height": 400
  }
}
```

### 기타 API

#### 1. 좌표 기반 검색

```bash
curl -X GET "http://localhost:8000/map/search/coordinates?latitude=37.5665&longitude=126.9780&query=카페&limit=10"
```

#### 2. 지원 도시 목록

```bash
curl -X GET "http://localhost:8000/map/cities"
```

#### 3. 검색 카테고리 목록

```bash
curl -X GET "http://localhost:8000/map/categories"
```

## 프론트엔드 연동 예시

### 1. HTML에서 지도 표시

```html
<!DOCTYPE html>
<html>
  <head>
    <title>네이버 지도 예시</title>
  </head>
  <body>
    <div id="map" style="width:600px;height:400px;"></div>

    <script
      type="text/javascript"
      src="https://openapi.map.naver.com/openapi/v3/maps.js?ncpClientId=YOUR_CLIENT_ID"
    ></script>
    <script>
      var map = new naver.maps.Map("map", {
        center: new naver.maps.LatLng(37.5665, 126.978),
        zoom: 15,
      });

      var marker = new naver.maps.Marker({
        position: new naver.maps.LatLng(37.5665, 126.978),
        map: map,
      });
    </script>
  </body>
</html>
```

### 2. JavaScript에서 API 호출

```javascript
// 장소 검색
async function searchPlaces(query) {
  const response = await fetch(
    `/map/search?query=${encodeURIComponent(query)}`
  );
  const data = await response.json();
  return data.places;
}

// 주변 맛집 검색
async function searchNearbyRestaurants(lat, lng, radius = 1000) {
  const response = await fetch(
    `/map/restaurants/nearby?latitude=${lat}&longitude=${lng}&radius=${radius}`
  );
  const data = await response.json();
  return data.restaurants;
}

// 지도에 마커 추가
function addMarkerToMap(map, place) {
  const marker = new naver.maps.Marker({
    position: new naver.maps.LatLng(place.mapy, place.mapx),
    map: map,
  });

  const infoWindow = new naver.maps.InfoWindow({
    content: `
            <div>
                <h3>${place.title}</h3>
                <p>${place.address}</p>
                <p>${place.telephone}</p>
            </div>
        `,
  });

  naver.maps.Event.addListener(marker, "click", function () {
    infoWindow.open(map, marker);
  });
}
```

### 3. React 컴포넌트 예시

```jsx
import React, { useEffect, useRef } from "react";

const NaverMap = ({ latitude, longitude, zoom = 15 }) => {
  const mapRef = useRef(null);

  useEffect(() => {
    const initMap = () => {
      const map = new window.naver.maps.Map(mapRef.current, {
        center: new window.naver.maps.LatLng(latitude, longitude),
        zoom: zoom,
      });

      new window.naver.maps.Marker({
        position: new window.naver.maps.LatLng(latitude, longitude),
        map: map,
      });
    };

    if (window.naver && window.naver.maps) {
      initMap();
    } else {
      const script = document.createElement("script");
      script.src = `https://openapi.map.naver.com/openapi/v3/maps.js?ncpClientId=${process.env.REACT_APP_NAVER_CLIENT_ID}`;
      script.onload = initMap;
      document.head.appendChild(script);
    }
  }, [latitude, longitude, zoom]);

  return <div ref={mapRef} style={{ width: "100%", height: "400px" }} />;
};

export default NaverMap;
```

## 주요 도시 좌표

| 도시 | 위도    | 경도     |
| ---- | ------- | -------- |
| 서울 | 37.5665 | 126.9780 |
| 부산 | 35.1796 | 129.0756 |
| 대구 | 35.8714 | 128.6014 |
| 인천 | 37.4563 | 126.7052 |
| 광주 | 35.1595 | 126.8526 |
| 대전 | 36.3504 | 127.3845 |
| 울산 | 35.5384 | 129.3114 |
| 세종 | 36.4800 | 127.2890 |
| 수원 | 37.2636 | 127.0286 |
| 고양 | 37.6584 | 126.8320 |
| 용인 | 37.2411 | 127.1776 |
| 창원 | 35.2278 | 128.6817 |
| 포항 | 36.0320 | 129.3650 |
| 제주 | 33.4996 | 126.5312 |

## 검색 카테고리

### 음식점

- 맛집, 카페

### 숙박

- 호텔, 펜션, 게스트하우스, 모텔, 리조트

### 교통

- 지하철역, 버스정류장, 공항, 기차역

### 기타

- 관광지, 쇼핑몰, 병원, 약국, 은행, 편의점, 주유소, 주차장

## 제한사항

### 네이버 API 제한

- 검색 API: 일 25,000건
- 지도 API: 일 100,000건
- 웹 서비스용 지도 API: 무제한

### 사용 시 주의사항

- API 키는 클라이언트에 노출되지 않도록 주의
- CORS 설정 확인
- 요청 제한 준수
- 네이버 개발자 센터 이용약관 준수

## 문제 해결

### 1. API 키 오류

```
"error": "API 키가 설정되지 않았습니다."
```

- 환경 변수 확인
- 네이버 개발자 센터에서 API 키 상태 확인

### 2. 검색 결과 없음

- 검색어 확인
- 카테고리 필터 확인
- 위치 정보 확인

### 3. 지도 표시 오류

- 클라이언트 ID 확인
- HTTPS 환경에서 사용 권장
- 브라우저 콘솔 오류 확인

## 추가 기능

### 1. 경로 안내 개선

- 실시간 교통 정보
- 대중교통 경로
- 도보 경로

### 2. 지도 스타일 커스터마이징

- 테마 변경
- 마커 스타일 변경
- 오버레이 추가

### 3. 실시간 정보

- 실시간 교통 정보
- 실시간 날씨 정보
- 실시간 인구 밀도

이 가이드를 통해 네이버 지도 API를 효과적으로 활용할 수 있습니다.
