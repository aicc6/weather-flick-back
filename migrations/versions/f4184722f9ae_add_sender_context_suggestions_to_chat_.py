"""add_sender_context_suggestions_to_chat_messages

Revision ID: f4184722f9ae
Revises: 394c4e90f5d9
Create Date: 2025-07-16 10:14:11.418481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4184722f9ae'
down_revision: Union[str, Sequence[str], None] = '394c4e90f5d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # chat_messages 테이블에 새로운 컬럼 추가
    op.add_column('chat_messages', sa.Column('sender', sa.String(50), nullable=True, server_default='user'))
    op.add_column('chat_messages', sa.Column('context', sa.JSON(), nullable=True))
    op.add_column('chat_messages', sa.Column('suggestions', sa.ARRAY(sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # chat_messages 테이블에서 컬럼 제거
    op.drop_column('chat_messages', 'suggestions')
    op.drop_column('chat_messages', 'context')
    op.drop_column('chat_messages', 'sender')
