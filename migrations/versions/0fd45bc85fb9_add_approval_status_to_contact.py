"""Add approval_status to contact

Revision ID: 0fd45bc85fb9
Revises: 8e3ae7ff2fa5
Create Date: 2025-07-15 15:17:15.400720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# ENUM 타입 정의
approval_status_enum = sa.Enum('PENDING', 'PROCESSING', 'COMPLETE', name='approval_status')

# revision identifiers, used by Alembic.
revision: str = '0fd45bc85fb9'
down_revision: Union[str, Sequence[str], None] = '8e3ae7ff2fa5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. ENUM 타입 먼저 생성
    approval_status_enum.create(op.get_bind(), checkfirst=True)
    # 2. 컬럼 추가
    op.add_column('contact', sa.Column(
        'approval_status',
        approval_status_enum,
        nullable=False,
        server_default='PENDING'
    ))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # 1. 컬럼 먼저 삭제
    op.drop_column('contact', 'approval_status')
    # 2. ENUM 타입 삭제
    approval_status_enum.drop(op.get_bind(), checkfirst=False)
    # ### end Alembic commands ###
