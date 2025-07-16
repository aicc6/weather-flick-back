from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SenderType(str, Enum):
    """메시지 발신자 타입"""
    USER = "user"
    BOT = "bot"

class ChatMessageRequest(BaseModel):
    """챗봇 메시지 요청 스키마"""
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(..., min_length=1, max_length=1000, description="사용자 메시지")
    context: dict[str, Any] | None = Field(None, description="대화 컨텍스트")

class ChatMessageResponse(BaseModel):
    """챗봇 메시지 응답 스키마"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = Field(None, description="메시지 ID (익명 사용자는 None)")
    text: str = Field(..., description="메시지 내용")
    sender: SenderType = Field(..., description="발신자 타입")
    timestamp: str = Field(..., description="메시지 시간")
    suggestions: list[str] | None = Field(None, description="추천 질문 목록")

class ChatHistoryResponse(BaseModel):
    """챗봇 대화 히스토리 응답 스키마"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str = Field(..., description="메시지 내용")
    sender: SenderType = Field(..., description="발신자 타입")
    timestamp: str = Field(..., description="메시지 시간")
    suggestions: list[str] | None = Field(None, description="추천 질문 목록")

class InitialMessageResponse(BaseModel):
    """챗봇 초기 메시지 응답 스키마"""
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(..., description="초기 메시지")
    suggestions: list[str] = Field(default_factory=list, description="추천 질문 목록")

class ChatbotConfigResponse(BaseModel):
    """챗봇 설정 응답 스키마"""
    model_config = ConfigDict(from_attributes=True)

    welcome_delay: int = Field(..., ge=0, le=10000, description="환영 메시지 지연 시간 (ms)")
    typing_delay: int = Field(..., ge=0, le=10000, description="타이핑 애니메이션 지연 시간 (ms)")
    max_context_length: int = Field(..., ge=1, le=1000, description="최대 컨텍스트 길이")
    max_suggestions: int = Field(..., ge=1, le=10, description="최대 추천 질문 개수")
