# Weather Flick API

날씨와 사용자 성향을 기반으로 여행지와 현재 진행중인 축제 정보를 추천하는 API 서버입니다.

## 주요 기능

- **날씨 정보**: 대한민국 주요 도시의 현재 날씨 및 예보 정보 제공 (기상청 API 연동)
- **여행지 추천**: 날씨(맑음, 비 등)와 여행지 특성(실내/실외 등)을 기반으로 여행지 추천
- **개인화 추천**: 사용자가 선호하는 여행 태그(#카페, #산책 등)를 프로필에 저장하고, 추천 점수에 반영
- **축제/이벤트 정보**: '맑은 날'에는 현재 위치에서 진행중인 축제 및 이벤트 정보를 가져와 추천 목록에 포함 (한국관광공사 TourAPI 연동)
- **사용자 인증**: JWT 기반의 안전한 회원가입 및 로그인 기능

## 주요 기술 스택

- **Backend**: FastAPI, Python 3.11
- **Database**: SQLAlchemy (ORM), Alembic (Migration), SQLite (기본)
- **Containerization**: Docker, Docker Compose
- **Authentication**: JWT (JSON Web Tokens)
- **Schema Validation**: Pydantic

## 실행 방법 (Docker 사용 - 권장)

로컬 환경의 복잡한 설정 없이, Docker를 사용하여 어떤 컴퓨터에서든 동일한 환경으로 애플리케이션을 실행할 수 있습니다.

### 1. 사전 준비

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)을 설치하고 실행합니다.

### 2. 환경 변수 설정

프로젝트 루트 디렉터리에 `.env` 파일을 생성하고, 아래 내용을 입력하세요. 한국관광공사 API 키가 필요합니다.

```env
# 한국관광공사 TourAPI 일반 인증키 (URL 인코딩된 키)
TOUR_API_KEY="여기에_발급받은_API_키를_입력하세요"
```

> **API 키 발급 방법:**
>
> 1. [공공데이터포털](https://www.data.go.kr/) 회원가입 및 로그인
> 2. '한국관광공사 국문 관광정보 서비스' 검색 및 활용 신청
> 3. 발급받은 **일반 인증키(URL 인코딩)** 를 복사하여 `.env` 파일에 붙여넣기

### 3. 애플리케이션 실행

터미널에서 아래 명령어를 실행하세요.

```bash
docker-compose up --build
```

- `--build` 옵션은 Docker 이미지를 새로 빌드할 때 사용합니다. 최초 실행 시 또는 Dockerfile 변경 시 필요합니다.
- 실행 후, 브라우저에서 `http://localhost:8000/docs` 로 접속하여 API 문서를 확인할 수 있습니다.

### 4. 애플리케이션 중지

터미널에서 `Ctrl + C`를 눌러 중지할 수 있습니다. 컨테이너를 완전히 내리려면 아래 명령어를 사용하세요.

```bash
docker-compose down
```

## API 엔드포인트 목록

API 문서는 서버 실행 후 `http://localhost:8000/docs` 에서 실시간으로 확인하고 테스트할 수 있습니다.

### 인증 (`/auth`)

- `POST /register`: 회원가입
- `POST /login`: 로그인
- `GET /me`: 현재 사용자 정보 조회 (인증 필요)
- `PUT /me`: 사용자 프로필(선호 태그 포함) 업데이트 (인증 필요)

### 기상청 날씨 (`/kma`)

- `GET /current/all-cities`: 전국 주요 도시 현재 날씨 일괄 조회
- `GET /provinces`: 날씨 조회를 지원하는 도/광역시 목록 조회
- `GET /current/by-province/{province_name}`: 특정 '도'에 속한 모든 도시의 현재 날씨 조회

### 여행지 (`/destinations`)

- `POST /`: 새로운 여행지 정보 추가
- `GET /`: 전체 여행지 목록 조회

### 날씨 기반 추천 (`/recommendations`)

- `POST /weather-based`: 날씨와 사용자 선호도 기반 여행지 및 축제 추천 (인증 필요)
  - **Request Body 예시**:
    ```json
    {
      "weather_status": "맑음",
      "city": "수원"
    }
    ```

### 이벤트 (`/events`)

- `GET /{area_code}`: 특정 지역의 현재 진행중인 축제/이벤트 목록 조회
  - **예시**: `GET /events/31` (경기도 지역 이벤트 조회)

## 프로젝트 구조

```
weather-flick-back/
├── .env                  # (Git 미포함) API 키, 데이터베이스 접속 정보 등 민감한 환경 변수를 저장합니다.
├── alembic.ini           # Alembic 데이터베이스 마이그레이션 도구의 설정 파일입니다.
├── docker-compose.yml    # Docker 컨테이너의 빌드 및 실행 방법을 정의하는 파일입니다.
├── Dockerfile            # 우리 애플리케이션의 Docker 이미지를 생성하기 위한 레시피입니다.
├── main.py               # FastAPI 애플리케이션을 초기화하고 모든 라우터를 포함하는 진입점입니다.
├── README.md             # 프로젝트 설명서 (현재 보고 있는 파일)
├── requirements.txt      # 프로젝트에 필요한 모든 Python 라이브러리 목록입니다.
│
├── app/                  # FastAPI 애플리케이션의 핵심 로직이 담긴 메인 패키지입니다.
│   ├── __init__.py
│   ├── auth.py           # JWT 토큰 생성, 사용자 인증, 비밀번호 암호화 등 인증 관련 로직을 담당합니다.
│   ├── config.py         # .env 파일에서 환경 변수를 불러와 관리하는 설정 파일입니다.
│   ├── database.py       # 데이터베이스 연결 및 세션 관리를 설정합니다.
│   ├── models.py         # SQLAlchemy ORM 모델(테이블 스키마)을 정의합니다.
│   │
│   ├── routers/          # API 엔드포인트(경로)를 기능별로 정의하는 곳입니다. (Controller 역할)
│   │   ├── __init__.py
│   │   ├── auth.py           # /auth 경로의 API (회원가입, 로그인 등)
│   │   ├── destinations.py   # /destinations 경로의 API (여행지 정보)
│   │   ├── events.py         # /events 경로의 API (축제/이벤트 정보)
│   │   ├── kma_weather.py    # /kma 경로의 API (기상청 날씨 정보)
│   │   └── recommendations.py# /recommendations 경로의 API (날씨 기반 추천)
│   │
│   ├── services/         # 실제 비즈니스 로직을 처리하는 부분입니다. (Service 역할)
│   │   ├── __init__.py
│   │   ├── destination_service.py    # 여행지 관련 비즈니스 로직
│   │   ├── kma_weather_service.py  # 기상청 API 연동 로직
│   │   ├── recommendation_service.py # 날씨 기반 추천 생성 로직
│   │   └── tour_api_service.py     # 한국관광공사 API 연동 로직
│   │
│   └── utils/            # 여러 곳에서 공통으로 사용되는 보조 함수들을 모아놓은 곳입니다.
│       ├── __init__.py
│       └── kma_utils.py      # 기상청 API 관련 좌표 변환 등 유틸리티 함수
│
└── migrations/             # Alembic을 통해 생성된 데이터베이스 스키마 변경 이력 파일들을 저장합니다.
    ├── env.py            # Alembic 실행 환경 설정
    ├── script.py.mako    # 마이그레이션 파일 템플릿
    └── versions/
        └── ...           # 실제 데이터베이스 변경 내용이 담긴 버전별 파이썬 파일들
```
