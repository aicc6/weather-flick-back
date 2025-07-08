from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.database import get_db
from app.auth import get_current_user_optional, get_current_user
from app.models import User, ChatMessage
from app.schemas.chatbot import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
    InitialMessageResponse,
    ChatbotConfigResponse,
)
from app.services.chatbot_service import ChatbotService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> ChatMessageResponse:
    """
    챗봇에게 메시지를 전송하고 응답을 받습니다.
    인증된 사용자의 경우 대화 히스토리가 저장되고, 익명 사용자는 저장되지 않습니다.
    """
    try:
        service = ChatbotService(db)

        # 인증된 사용자의 경우에만 메시지 저장
        if current_user:
            user_message = ChatMessage(
                user_id=current_user.id,
                message=request.message,
                sender="user",
                context=request.context,
                created_at=datetime.utcnow()
            )
            db.add(user_message)
            db.commit()

        # 챗봇 응답 생성 (사용자 ID는 선택적)
        bot_response = await service.generate_response(
            user_id=current_user.id if current_user else None,
            message=request.message,
            context=request.context
        )

        # 인증된 사용자의 경우에만 챗봇 응답 저장
        if current_user:
            bot_message = ChatMessage(
                user_id=current_user.id,
                message=bot_response["response"],
                sender="bot",
                suggestions=bot_response.get("suggestions", []),
                created_at=datetime.utcnow()
            )
            db.add(bot_message)
            db.commit()
            message_id = bot_message.id
        else:
            message_id = None

        return ChatMessageResponse(
            id=message_id,
            text=bot_response["response"],
            sender="bot",
            timestamp=datetime.utcnow().isoformat(),
            suggestions=bot_response.get("suggestions", [])
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        user_info = f"사용자: {current_user.id}" if current_user else "익명 사용자"
        logger.error(f"챗봇 메시지 처리 실패: {e}, {user_info}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 처리 중 오류가 발생했습니다"
        )

@router.get("/history/{user_id}", response_model=List[ChatHistoryResponse])
async def get_chat_history(
    user_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ChatHistoryResponse]:
    """
    사용자의 챗봇 대화 히스토리를 조회합니다.
    """
    try:
        # 본인 또는 관리자만 조회 가능
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="대화 히스토리 조회 권한이 없습니다"
            )

        service = ChatbotService(db)
        history = await service.get_chat_history(user_id, limit)

        return [
            ChatHistoryResponse(
                id=msg.id,
                text=msg.message,
                sender=msg.sender,
                timestamp=msg.created_at.isoformat(),
                suggestions=msg.suggestions or []
            )
            for msg in history
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"챗봇 히스토리 조회 실패: {e}, 사용자: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="대화 히스토리 조회 중 오류가 발생했습니다"
        )

@router.get("/initial", response_model=InitialMessageResponse)
async def get_initial_message(
    db: Session = Depends(get_db),
) -> InitialMessageResponse:
    """
    챗봇 초기 메시지를 조회합니다.
    """
    try:
        service = ChatbotService(db)
        initial_message = await service.get_initial_message()

        return InitialMessageResponse(
            message=initial_message["message"],
            suggestions=initial_message.get("suggestions", [])
        )

    except Exception as e:
        logger.error(f"초기 메시지 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="초기 메시지 조회 중 오류가 발생했습니다"
        )

@router.get("/config", response_model=ChatbotConfigResponse)
async def get_chatbot_config(
    db: Session = Depends(get_db),
) -> ChatbotConfigResponse:
    """
    챗봇 설정을 조회합니다.
    """
    try:
        service = ChatbotService(db)
        config = await service.get_config()

        return ChatbotConfigResponse(
            welcome_delay=config["welcome_delay"],
            typing_delay=config["typing_delay"],
            max_context_length=config["max_context_length"],
            max_suggestions=config["max_suggestions"]
        )

    except Exception as e:
        logger.error(f"챗봇 설정 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="챗봇 설정 조회 중 오류가 발생했습니다"
        )
