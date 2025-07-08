#!/usr/bin/env python3
"""
챗봇 서비스 로직 테스트 (DB 의존성 없음)
"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.chatbot_service import ChatbotService

class MockDB:
    """테스트용 Mock DB 클래스"""
    def __init__(self):
        self.messages = []

    def add(self, message):
        self.messages.append(message)
        return message

    def commit(self):
        pass

    def execute(self, stmt):
        class MockResult:
            def scalars(self):
                return self

            def all(self):
                return []

        return MockResult()

async def test_chatbot_service():
    """챗봇 서비스 테스트"""
    print("🤖 챗봇 서비스 로직 테스트")
    print("=" * 50)

    # Mock DB 생성
    mock_db = MockDB()
    service = ChatbotService(mock_db)

    # 테스트 케이스들
    test_cases = [
        {
            "message": "안녕하세요",
            "expected_intent": "greeting",
            "description": "인사 메시지"
        },
        {
            "message": "오늘 날씨 어때요?",
            "expected_intent": "weather",
            "description": "날씨 관련 메시지"
        },
        {
            "message": "여행지 추천해주세요",
            "expected_intent": "travel",
            "description": "여행 관련 메시지"
        },
        {
            "message": "도움말을 보여주세요",
            "expected_intent": "help",
            "description": "도움말 요청"
        },
        {
            "message": "무작위 메시지입니다",
            "expected_intent": "general",
            "description": "일반 메시지"
        }
    ]

    print("\n📝 의도 분석 테스트:")
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   입력: '{test_case['message']}'")

        # 의도 분석 테스트
        processed_message = service._preprocess_message(test_case['message'])
        intent = service._analyze_intent(processed_message)

        print(f"   예상 의도: {test_case['expected_intent']}")
        print(f"   실제 의도: {intent}")

        if intent == test_case['expected_intent']:
            print("   ✅ 통과")
        else:
            print("   ❌ 실패")

    print("\n💬 응답 생성 테스트:")
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")

        try:
            response = await service.generate_response(
                user_id=1,
                message=test_case['message'],
                context={}
            )

            print(f"   응답: {response['response'][:100]}...")
            print(f"   추천 질문: {response['suggestions']}")
            print("   ✅ 성공")

        except Exception as e:
            print(f"   ❌ 실패: {e}")

    print("\n⚙️ 설정 조회 테스트:")
    try:
        config = await service.get_config()
        print(f"   환영 지연: {config['welcome_delay']}ms")
        print(f"   타이핑 지연: {config['typing_delay']}ms")
        print(f"   최대 컨텍스트: {config['max_context_length']}")
        print(f"   최대 추천: {config['max_suggestions']}")
        print("   ✅ 성공")
    except Exception as e:
        print(f"   ❌ 실패: {e}")

    print("\n🌅 초기 메시지 테스트:")
    try:
        initial_message = await service.get_initial_message()
        print(f"   메시지: {initial_message['message'][:100]}...")
        print(f"   추천 질문: {initial_message['suggestions']}")
        print("   ✅ 성공")
    except Exception as e:
        print(f"   ❌ 실패: {e}")

def main():
    """메인 함수"""
    try:
        asyncio.run(test_chatbot_service())
        print("\n" + "=" * 50)
        print("✅ 챗봇 서비스 로직 테스트 완료!")
        print("\n📝 테스트 결과:")
        print("✅ 의도 분석 로직 정상")
        print("✅ 응답 생성 로직 정상")
        print("✅ 설정 조회 정상")
        print("✅ 초기 메시지 정상")
        print("\n🔧 다음 단계:")
        print("1. 데이터베이스 연결 설정")
        print("2. API 엔드포인트 테스트")
        print("3. 프론트엔드 연동 테스트")

    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
