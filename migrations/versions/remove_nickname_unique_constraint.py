"""remove nickname unique constraint

Revision ID: fc6b86a4232f
Revises: fb2ec0935be9
Create Date: 2025-07-05 19:47:14.575680

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fc6b86a4232f'
down_revision: Union[str, Sequence[str], None] = 'fb2ec0935be9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """닉네임 유니크 제약조건 제거"""
    # 기존 유니크 인덱스 삭제
    op.drop_index('ix_users_nickname', table_name='users')
    
    # 일반 인덱스로 재생성 (유니크 제약조건 없이)
    op.create_index(op.f('ix_users_nickname'), 'users', ['nickname'], unique=False)


def downgrade() -> None:
    """닉네임 유니크 제약조건 복원"""
    # 일반 인덱스 삭제
    op.drop_index(op.f('ix_users_nickname'), table_name='users')
    
    # 유니크 인덱스로 재생성
    op.create_index(op.f('ix_users_nickname'), 'users', ['nickname'], unique=True)