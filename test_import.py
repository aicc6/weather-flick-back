#!/usr/bin/env python3
"""
Import 테스트 스크립트
"""

try:
    print("1. 기본 모듈 import 시작...")
    from fastapi import FastAPI
    print("✅ FastAPI import 성공")

    from sqlalchemy.orm import Session
    print("✅ SQLAlchemy import 성공")

    print("\n2. 앱 모듈 import 시작...")
    from app.database import get_db
    print("✅ database import 성공")

    from app.auth import get_current_user_optional, get_current_user
    print("✅ auth import 성공")

    from app.models import User, ChatMessage
    print("✅ models import 성공")

    from app.schemas.chatbot import (
        ChatMessageRequest,
        ChatMessageResponse,
        ChatHistoryResponse,
        InitialMessageResponse,
        ChatbotConfigResponse,
    )
    print("✅ chatbot schemas import 성공")

    from app.services.chatbot_service import ChatbotService
    print("✅ chatbot service import 성공")

    print("\n3. 챗봇 라우터 import 시작...")
    from app.routers.chatbot import router
    print("✅ chatbot router import 성공")

    print("\n🎉 모든 import 테스트 통과!")

except Exception as e:
    print(f"❌ Import 오류 발생: {e}")
    import traceback
    traceback.print_exc()