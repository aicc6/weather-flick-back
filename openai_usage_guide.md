# 🤖 Weather Flick OpenAI 기능 사용 가이드

## 📋 개요

Weather Flick에 통합된 OpenAI 기능을 사용하여 지능형 여행 챗봇 서비스를 이용할 수 있습니다.

## 🔧 설정 방법

### 1. 환경변수 설정

`.env` 파일에 다음 설정을 추가하세요:

```bash
# OpenAI 설정
OPENAI_API_KEY=""
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=1500
OPENAI_TEMPERATURE=0.5
```

### 2. OpenAI API 키 발급

1. https://platform.openai.com/ 방문
2. 계정 생성/로그인
3. API Keys 섹션에서 새 키 생성
4. 생성된 키를 `.env` 파일에 설정

## 🚀 API 사용법

### 1. 챗봇 메시지 전송

**엔드포인트**: `POST /api/chatbot/message`

```bash
curl -X POST "http://localhost:8000/api/chatbot/message" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "message": "제주도 여행을 계획하고 있어요. 날씨 정보와 추천 관광지를 알려주세요.",
    "context": {
      "travel_dates": ["2024-03-01", "2024-03-03"],
      "preferences": "자연 관광"
    }
  }'
```

**응답 예시**:

```json
{
  "id": 123,
  "text": "제주도는 3월에 방문하기 좋은 시기입니다! 현재 날씨는 온화하며...",
  "sender": "bot",
  "timestamp": "2024-01-15T10:30:00Z",
  "suggestions": [
    "한라산 등반 코스 알려주세요",
    "제주도 맛집 추천해주세요",
    "렌터카 정보 알려주세요"
  ]
}
```

### 2. 대화 기록 조회

**엔드포인트**: `GET /api/chatbot/history/{user_id}`

```bash
curl -X GET "http://localhost:8000/api/chatbot/history/1" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. 초기 메시지 조회

**엔드포인트**: `GET /api/chatbot/initial`

```bash
curl -X GET "http://localhost:8000/api/chatbot/initial"
```

## 🎯 주요 기능

### 1. 지능형 응답 시스템

- **OpenAI 우선**: 고품질 AI 응답 생성
- **Fallback 시스템**: OpenAI 실패 시 규칙 기반 응답
- **컨텍스트 인식**: 대화 기록을 바탕으로 맥락 이해

### 2. 여행 전문 지식

- 날씨 기반 여행 추천
- 지역별 관광지 정보
- 숙박 및 교통 안내
- 맛집 및 특산물 추천
- 여행 일정 계획 도움

### 3. 스마트 추천 시스템

- 사용자 질문에 따른 동적 추천
- 상황별 맞춤 제안
- 대화 흐름을 고려한 연속 질문

## 💻 프론트엔드 연동 예시

### React 컴포넌트 예시

```jsx
import React, { useState } from "react";
import axios from "axios";

const ChatBot = () => {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!message.trim()) return;

    setLoading(true);
    try {
      const response = await axios.post(
        "/api/chatbot/message",
        {
          message: message,
          context: {
            preferences: "nature",
          },
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        }
      );

      setMessages((prev) => [
        ...prev,
        { text: message, sender: "user" },
        {
          text: response.data.text,
          sender: "bot",
          suggestions: response.data.suggestions,
        },
      ]);
      setMessage("");
    } catch (error) {
      console.error("챗봇 오류:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chatbot">
      <div className="messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.sender}`}>
            {msg.text}
            {msg.suggestions && (
              <div className="suggestions">
                {msg.suggestions.map((suggestion, i) => (
                  <button key={i} onClick={() => setMessage(suggestion)}>
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="input">
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && sendMessage()}
          placeholder="메시지를 입력하세요..."
        />
        <button onClick={sendMessage} disabled={loading}>
          {loading ? "전송 중..." : "전송"}
        </button>
      </div>
    </div>
  );
};

export default ChatBot;
```

## 🔍 테스트 방법

### 1. 서버 실행

```bash
cd weather-flick-back
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 챗봇 테스트

```bash
# 1. 로그인하여 JWT 토큰 획득
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'

# 2. 챗봇 메시지 전송
curl -X POST "http://localhost:8000/api/chatbot/message" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"message": "안녕하세요! 제주도 여행 추천해주세요."}'
```

## 📊 응답 품질 최적화

### 1. OpenAI 설정 조정

```bash
# 창의적인 응답을 위해
OPENAI_TEMPERATURE=0.9

# 일관된 응답을 위해
OPENAI_TEMPERATURE=0.3

# 더 긴 응답을 위해
OPENAI_MAX_TOKENS=2000
```

### 2. 프롬프트 최적화

서비스에서 자동으로 최적화된 프롬프트를 사용하지만, 필요시 `openai_service.py`에서 프롬프트를 수정할 수 있습니다.

## 🚨 주의사항

1. **API 키 보안**: `.env` 파일을 절대 git에 커밋하지 마세요
2. **사용량 모니터링**: OpenAI API는 사용량에 따라 과금됩니다
3. **에러 처리**: API 키가 없거나 잘못된 경우 자동으로 규칙 기반 응답으로 전환됩니다
4. **속도 제한**: OpenAI API에는 분당 요청 제한이 있습니다

## 🔧 문제 해결

### OpenAI가 작동하지 않는 경우

1. `.env` 파일에 `OPENAI_API_KEY`가 설정되어 있는지 확인
2. API 키가 유효한지 확인 (https://platform.openai.com/account/api-keys)
3. 계정에 크레딧이 있는지 확인
4. 로그를 확인하여 구체적인 오류 메시지 파악

### 규칙 기반 응답만 나오는 경우

- OpenAI 설정이 제대로 되지 않았거나 API 호출이 실패한 경우입니다
- 로그에서 "OpenAI 챗봇 응답 생성 완료" 메시지가 나오는지 확인하세요

## 📈 향후 개선 계획

1. **GPT-4 지원**: 더 고품질 응답을 위한 GPT-4 옵션 추가
2. **기능 호출**: OpenAI Function Calling을 통한 실시간 데이터 연동
3. **개인화**: 사용자별 선호도 학습 및 맞춤 응답
4. **다국어 지원**: 영어, 중국어, 일본어 등 다국어 챗봇 지원
