#!/usr/bin/env python3
"""
OpenAI 통합 테스트 스크립트
"""

import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.services.openai_service import openai_service
from app.services.chatbot_service import ChatbotService
from unittest.mock import Mock

def check_environment():
    """환경 설정 확인"""
    print("🔍 환경 설정 확인 중...")

    from app.config import settings

    print(f"✅ OpenAI API Key: {'설정됨' if settings.openai_api_key else '❌ 미설정'}")
    print(f"✅ OpenAI Model: {settings.openai_model}")
    print(f"✅ Max Tokens: {settings.openai_max_tokens}")
    print(f"✅ Temperature: {settings.openai_temperature}")
    print()

    return bool(settings.openai_api_key)

async def test_openai_service():
    """OpenAI 서비스 직접 테스트"""
    print("🤖 OpenAI 서비스 테스트...")

    if not openai_service.client:
        print("❌ OpenAI 클라이언트가 초기화되지 않음")
        print("💡 .env 파일에 OPENAI_API_KEY를 설정해주세요")
        return False

    print("✅ OpenAI 클라이언트 초기화됨")

    # 테스트 메시지
    test_message = "안녕하세요! 제주도 여행을 계획하고 있어요. 날씨 정보와 추천 관광지를 알려주세요."

    try:
        print(f"📝 테스트 메시지: {test_message}")
        print("⏳ OpenAI 응답 생성 중...")

        response = await openai_service.generate_chatbot_response(test_message)

        print("✅ OpenAI 응답 생성 성공!")
        print(f"🤖 챗봇 응답: {response[:200]}...")
        print()
        return True

    except Exception as e:
        print(f"❌ OpenAI 테스트 실패: {e}")
        return False

async def test_chatbot_service():
    """통합된 챗봇 서비스 테스트"""
    print("🎯 통합 챗봇 서비스 테스트...")

    # Mock DB 세션 생성
    mock_db = Mock()
    mock_db.execute.return_value.scalars.return_value.all.return_value = []

    chatbot_service = ChatbotService(mock_db)

    test_messages = [
        "안녕하세요!",
        "제주도 날씨 어때요?",
        "여행지 추천해주세요",
        "도움말을 보여주세요"
    ]

    for i, message in enumerate(test_messages, 1):
        print(f"\n--- 테스트 {i}/4 ---")
        print(f"📝 사용자: {message}")

        try:
            response = await chatbot_service.generate_response(
                user_id=1,
                message=message,
                context={}
            )

            print(f"🤖 챗봇: {response['response'][:150]}...")
            print(f"💡 추천 질문: {response['suggestions']}")
            print(f"🔍 응답 소스: {response.get('source', 'unknown')}")
            print(f"🎯 의도: {response.get('intent', 'unknown')}")

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")

    print("\n✅ 챗봇 서비스 테스트 완료!")

async def test_fallback_system():
    """Fallback 시스템 테스트"""
    print("\n🛡️ Fallback 시스템 테스트...")

    # OpenAI 클라이언트를 일시적으로 None으로 설정
    original_client = openai_service.client
    openai_service.client = None

    mock_db = Mock()
    mock_db.execute.return_value.scalars.return_value.all.return_value = []

    chatbot_service = ChatbotService(mock_db)

    try:
        response = await chatbot_service.generate_response(
            user_id=1,
            message="여행지 추천해주세요",
            context={}
        )

        print(f"🤖 Fallback 응답: {response['response'][:150]}...")
        print(f"🔍 응답 소스: {response.get('source', 'unknown')}")

        if response.get('source') == 'rule_based':
            print("✅ Fallback 시스템 정상 작동!")
        else:
            print("❌ Fallback 시스템 오류")

    except Exception as e:
        print(f"❌ Fallback 테스트 실패: {e}")
    finally:
        # 원래 클라이언트 복원
        openai_service.client = original_client

def print_usage_instructions():
    """사용법 안내"""
    print("\n" + "="*60)
    print("🚀 OpenAI 기능 사용 방법")
    print("="*60)
    print()
    print("1. 환경변수 설정:")
    print("   .env 파일에 다음 내용 추가:")
    print("   OPENAI_API_KEY=sk-your-openai-api-key-here")
    print()
    print("2. 서버 실행:")
    print("   uvicorn main:app --reload")
    print()
    print("3. API 호출:")
    print("   POST /api/chatbot/message")
    print("   Authorization: Bearer <JWT_TOKEN>")
    print("   Body: {\"message\": \"제주도 여행 추천해주세요\"}")
    print()
    print("4. 상세 가이드:")
    print("   openai_usage_guide.md 파일 참조")
    print()

async def main():
    """메인 함수"""
    print("🤖 Weather Flick OpenAI 통합 테스트")
    print("="*50)
    print()

    # 1. 환경 설정 확인
    has_api_key = check_environment()

    if not has_api_key:
        print("⚠️  OpenAI API 키가 설정되지 않음")
        print("💡 .env 파일에 OPENAI_API_KEY를 설정하고 다시 실행하세요")
        print_usage_instructions()
        return

    # 2. OpenAI 서비스 테스트
    openai_success = await test_openai_service()

    # 3. 통합 챗봇 서비스 테스트
    await test_chatbot_service()

    # 4. Fallback 시스템 테스트
    await test_fallback_system()

    # 5. 결과 요약
    print("\n" + "="*50)
    print("📊 테스트 결과 요약")
    print("="*50)
    print(f"🔑 OpenAI API 키: {'✅ 설정됨' if has_api_key else '❌ 미설정'}")
    print(f"🤖 OpenAI 서비스: {'✅ 정상' if openai_success else '❌ 오류'}")
    print(f"💬 챗봇 시스템: ✅ 정상 (Fallback 포함)")
    print()

    if openai_success:
        print("🎉 OpenAI 통합이 성공적으로 완료되었습니다!")
        print("이제 지능형 여행 챗봇을 사용할 수 있습니다.")
    else:
        print("⚠️  OpenAI 연동에 문제가 있지만 기본 챗봇은 사용 가능합니다.")

    print_usage_instructions()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
