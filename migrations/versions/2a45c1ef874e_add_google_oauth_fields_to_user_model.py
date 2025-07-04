"""add google oauth fields to user model

Revision ID: 2a45c1ef874e
Revises: 5e5b9b89a12b
Create Date: 2025-07-01 21:09:21.058867

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2a45c1ef874e'
down_revision: str | Sequence[str] | None = '5e5b9b89a12b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Google OAuth 필드만 추가
    op.add_column('users', sa.Column('google_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(), nullable=True))
    op.alter_column('users', 'hashed_password',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.create_unique_constraint(None, 'users', ['google_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Google OAuth 필드 제거
    op.drop_constraint(None, 'users', type_='unique')
    op.alter_column('users', 'hashed_password',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'google_id')
