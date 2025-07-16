import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_current_user_optional
from app.database import get_db
from app.models import ChatMessage, User
from app.schema_models.chatbot import (
    ChatbotConfigResponse,
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    InitialMessageResponse,
)
from app.services.chatbot_service import ChatbotService
from app.services.chatbot_service_enhanced import EnhancedChatbotService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> ChatMessageResponse:
    """
    챗봇에게 메시지를 전송하고 응답을 받습니다.
    인증된 사용자의 경우 대화 히스토리가 저장되고, 익명 사용자는 저장되지 않습니다.
    """
    try:
        logger.info(f"받은 요청: message={request.message}, context={request.context}")
        logger.info(f"현재 사용자: {current_user.id if current_user else 'Anonymous'}")
        
        # 개인화 서비스 사용 여부 결정
        use_enhanced = request.context and request.context.get("use_personalized", True)
        
        # 임시로 기본 서비스 사용 (디버깅용)
        service = ChatbotService(db)

        # 기존 테이블 구조를 사용하여 메시지 저장 (인증된 사용자만)
        # 현재 chat_messages 테이블에는 id, user_id, message, response, created_at 컬럼만 있음

        # 챗봇 응답 생성 (사용자 ID는 선택적)
        bot_response = await service.generate_response(
            user_id=current_user.id if current_user else None,
            message=request.message,
            context=request.context
        )

        # 인증된 사용자의 경우에만 대화 저장 (새로운 컬럼 포함)
        if current_user:
            chat_message = ChatMessage(
                user_id=current_user.id,
                message=request.message,
                response=bot_response["response"],
                sender="user",  # 사용자가 보낸 메시지
                context=request.context,
                suggestions=bot_response.get("suggestions"),
                created_at=datetime.utcnow()
            )
            db.add(chat_message)
            db.commit()
            message_id = chat_message.id
        else:
            message_id = None

        response = ChatMessageResponse(
            id=message_id,
            text=bot_response["response"],
            sender="bot",
            timestamp=datetime.utcnow().isoformat(),
            suggestions=bot_response.get("suggestions", [])
        )
        logger.info(f"생성된 응답: {response.model_dump()}")
        return response

    except ValueError as e:
        logger.error(f"ValueError 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        user_info = f"사용자: {current_user.id}" if current_user else "익명 사용자"
        logger.error(f"챗봇 메시지 처리 실패: {e}, {user_info}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 처리 중 오류가 발생했습니다"
        )

@router.get("/history/{user_id}", response_model=list[ChatHistoryResponse])
async def get_chat_history(
    user_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatHistoryResponse]:
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
    current_user: User | None = Depends(get_current_user_optional),
) -> InitialMessageResponse:
    """
    챗봇 초기 메시지를 조회합니다.
    로그인한 사용자의 경우 개인화된 메시지를 반환합니다.
    """
    try:
        if current_user:
            # 로그인한 사용자는 개인화된 서비스 사용
            service = EnhancedChatbotService(db)
            # 사용자 프로필 조회
            user_profile = await service._get_user_profile(current_user.id)
            
            # 개인화된 환영 메시지 생성
            if user_profile and user_profile.get("nickname"):
                personalized_message = f"안녕하세요, {user_profile['nickname']}님! 🌟 "
                personalized_message += "Weather Flick 여행 도우미입니다. "
                
                # 선호 지역/테마 기반 메시지 추가
                if user_profile.get("preferred_region"):
                    personalized_message += f"오늘도 {user_profile['preferred_region']} 여행을 계획하고 계신가요? "
                elif user_profile.get("preferred_theme"):
                    personalized_message += f"{user_profile['preferred_theme']} 테마 여행에 관심이 있으신가요? "
                
                personalized_message += "무엇을 도와드릴까요?"
                
                # 개인화된 추천 질문
                suggestions = await service._generate_personalized_suggestions(
                    current_user.id, "", user_profile
                )
                
                return InitialMessageResponse(
                    message=personalized_message,
                    suggestions=suggestions
                )
        
        # 익명 사용자는 기본 서비스 사용
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
