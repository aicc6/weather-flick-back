"""add sharing and collaboration tables

Revision ID: add_sharing_collaboration
Revises: 
Create Date: 2025-01-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_sharing_collaboration'
down_revision = 'aae1984d85e0'
branch_labels = None
depends_on = None


def upgrade():
    # Create travel_plan_shares table
    op.create_table(
        'travel_plan_shares',
        sa.Column('share_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('share_token', sa.String(length=100), nullable=False),
        sa.Column('permission', sa.String(length=20), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('use_count', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['plan_id'], ['travel_plans.plan_id'], ),
        sa.PrimaryKeyConstraint('share_id')
    )
    op.create_index(op.f('ix_travel_plan_shares_share_id'), 'travel_plan_shares', ['share_id'], unique=False)
    op.create_index(op.f('ix_travel_plan_shares_share_token'), 'travel_plan_shares', ['share_token'], unique=True)

    # Create travel_plan_versions table
    op.create_table(
        'travel_plan_versions',
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('itinerary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('change_description', sa.String(length=500), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['plan_id'], ['travel_plans.plan_id'], ),
        sa.PrimaryKeyConstraint('version_id')
    )
    op.create_index(op.f('ix_travel_plan_versions_version_id'), 'travel_plan_versions', ['version_id'], unique=False)

    # Create travel_plan_comments table
    op.create_table(
        'travel_plan_comments',
        sa.Column('comment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_comment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('day_number', sa.Integer(), nullable=True),
        sa.Column('place_index', sa.Integer(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['parent_comment_id'], ['travel_plan_comments.comment_id'], ),
        sa.ForeignKeyConstraint(['plan_id'], ['travel_plans.plan_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('comment_id')
    )
    op.create_index(op.f('ix_travel_plan_comments_comment_id'), 'travel_plan_comments', ['comment_id'], unique=False)

    # Create travel_plan_collaborators table
    op.create_table(
        'travel_plan_collaborators',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission', sa.String(length=20), nullable=True),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('joined_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_viewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['invited_by'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['plan_id'], ['travel_plans.plan_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_id', 'user_id', name='uq_plan_collaborator')
    )
    op.create_index(op.f('ix_travel_plan_collaborators_id'), 'travel_plan_collaborators', ['id'], unique=False)

    # Set default values
    op.execute("UPDATE travel_plan_shares SET permission = 'view' WHERE permission IS NULL")
    op.execute("UPDATE travel_plan_shares SET use_count = 0 WHERE use_count IS NULL")
    op.execute("UPDATE travel_plan_shares SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE travel_plan_comments SET is_deleted = false WHERE is_deleted IS NULL")
    op.execute("UPDATE travel_plan_collaborators SET permission = 'edit' WHERE permission IS NULL")


def downgrade():
    op.drop_index(op.f('ix_travel_plan_collaborators_id'), table_name='travel_plan_collaborators')
    op.drop_table('travel_plan_collaborators')
    op.drop_index(op.f('ix_travel_plan_comments_comment_id'), table_name='travel_plan_comments')
    op.drop_table('travel_plan_comments')
    op.drop_index(op.f('ix_travel_plan_versions_version_id'), table_name='travel_plan_versions')
    op.drop_table('travel_plan_versions')
    op.drop_index(op.f('ix_travel_plan_shares_share_token'), table_name='travel_plan_shares')
    op.drop_index(op.f('ix_travel_plan_shares_share_id'), table_name='travel_plan_shares')
    op.drop_table('travel_plan_shares')