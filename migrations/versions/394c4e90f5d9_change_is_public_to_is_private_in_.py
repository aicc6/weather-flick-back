"""change_is_public_to_is_private_in_contact

Revision ID: 394c4e90f5d9
Revises: 7ce960f66923
Create Date: 2025-07-15 19:09:39.001584

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '394c4e90f5d9'
down_revision: Union[str, Sequence[str], None] = '7ce960f66923'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. is_private 칼럼 추가 (기본값 False로 설정)
    op.add_column('contact', sa.Column('is_private', sa.Boolean(), nullable=True, server_default='false'))
    
    # 2. 기존 is_public 값을 반대로 하여 is_private에 복사
    # is_public=True -> is_private=False (공개)
    # is_public=False -> is_private=True (비공개)
    op.execute("UPDATE contact SET is_private = NOT COALESCE(is_public, true)")
    
    # 3. is_private를 NOT NULL로 변경
    op.alter_column('contact', 'is_private', nullable=False)
    
    # 4. is_public 칼럼 삭제
    op.drop_column('contact', 'is_public')


def downgrade() -> None:
    """Downgrade schema."""
    # 1. is_public 칼럼 추가
    op.add_column('contact', sa.Column('is_public', sa.Boolean(), nullable=True, server_default='true'))
    
    # 2. is_private 값을 반대로 하여 is_public에 복사
    op.execute("UPDATE contact SET is_public = NOT is_private")
    
    # 3. is_public을 NOT NULL로 변경
    op.alter_column('contact', 'is_public', nullable=False)
    
    # 4. is_private 칼럼 삭제
    op.drop_column('contact', 'is_private')
