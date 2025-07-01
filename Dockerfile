# 1. 베이스 이미지 설정: Python 3.11 슬림 버전을 사용합니다.
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 환경 변수 설정: Python이 .pyc 파일을 생성하지 않도록 하고, 버퍼링을 비활성화합니다.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 4. 의존성 설치: requirements.txt 파일을 먼저 복사하여 의존성을 설치합니다.
#    이렇게 하면 코드 변경 시 매번 의존성을 새로 설치하는 것을 방지하여 빌드 속도를 높일 수 있습니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 애플리케이션 코드 복사: 나머지 모든 프로젝트 파일을 컨테이너의 작업 디렉토리로 복사합니다.
COPY . .

# 6. 포트 노출: 컨테이너의 8000번 포트를 외부에 노출합니다.
EXPOSE 8000

# 7. 애플리케이션 실행: uvicorn을 사용하여 FastAPI 애플리케이션을 실행합니다.
#    --host 0.0.0.0 옵션은 컨테이너 외부에서 접근할 수 있도록 합니다.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
