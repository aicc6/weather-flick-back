"""
Revision ID: 20240610_add_travel_course_likes
Revises:
Create Date: 2024-06-10

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '20240610_add_travel_course_likes'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'travel_course_likes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('subtitle', sa.String(length=255)),
        sa.Column('summary', sa.Text()),
        sa.Column('description', sa.Text()),
        sa.Column('region', sa.String(length=50)),
        sa.Column('itinerary', sa.JSON()),
    )

def downgrade():
    op.drop_table('travel_course_likes')
