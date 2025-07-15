"""remove_unused_tables_roles_user_activity_logs_reviews_recommend

Revision ID: 3414a5163f27
Revises: 46ae979c4203
Create Date: 2025-07-13 00:54:26.396456

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3414a5163f27'
down_revision: str | Sequence[str] | None = '46ae979c4203'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop foreign key constraints first
    op.drop_constraint('admin_roles_admin_id_fkey', 'admin_roles', type_='foreignkey')
    op.drop_constraint('admin_roles_role_id_fkey', 'admin_roles', type_='foreignkey')
    op.drop_constraint('user_activity_logs_user_id_fkey', 'user_activity_logs', type_='foreignkey')
    op.drop_constraint('review_likes_review_id_fkey', 'review_likes', type_='foreignkey')
    op.drop_constraint('reviews_recommend_parent_id_fkey', 'reviews_recommend', type_='foreignkey')

    # Drop tables
    op.drop_table('admin_roles')
    op.drop_table('roles')
    op.drop_table('user_activity_logs')
    op.drop_table('reviews_recommend')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate roles table
    op.create_table('roles',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.PrimaryKeyConstraint('role_id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_roles_role_id'), 'roles', ['role_id'], unique=False)

    # Recreate admin_roles table
    op.create_table('admin_roles',
        sa.Column('admin_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.admin_id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ),
        sa.PrimaryKeyConstraint('admin_id', 'role_id')
    )

    # Recreate user_activity_logs table
    op.create_table('user_activity_logs',
        sa.Column('log_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('activity_type', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('log_id')
    )
    op.create_index(op.f('ix_user_activity_logs_log_id'), 'user_activity_logs', ['log_id'], unique=False)

    # Recreate reviews_recommend table (structure unknown, basic table)
    op.create_table('reviews_recommend',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['reviews_recommend.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Recreate foreign key constraint for review_likes
    op.create_foreign_key('review_likes_review_id_fkey', 'review_likes', 'reviews_recommend', ['review_id'], ['id'])
