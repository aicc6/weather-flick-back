"""add travel routes and transportation details tables

Revision ID: travel_routes_001
Revises: c81ebbb9afa1
Create Date: 2025-01-09 16:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = 'travel_routes_001'
down_revision = 'c81ebbb9afa1'
branch_labels = None
depends_on = None


def upgrade():
    # Create travel_routes table
    op.create_table('travel_routes',
        sa.Column('route_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('day', sa.Integer(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('departure_name', sa.String(), nullable=False),
        sa.Column('departure_lat', sa.Float(), nullable=True),
        sa.Column('departure_lng', sa.Float(), nullable=True),
        sa.Column('destination_name', sa.String(), nullable=False),
        sa.Column('destination_lat', sa.Float(), nullable=True),
        sa.Column('destination_lng', sa.Float(), nullable=True),
        sa.Column('transport_type', sa.String(), nullable=True),
        sa.Column('route_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('distance', sa.Float(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['travel_plans.plan_id'], ),
        sa.PrimaryKeyConstraint('route_id')
    )
    op.create_index(op.f('ix_travel_routes_route_id'), 'travel_routes', ['route_id'], unique=False)

    # Create transportation_details table
    op.create_table('transportation_details',
        sa.Column('detail_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('route_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transport_name', sa.String(), nullable=True),
        sa.Column('transport_color', sa.String(), nullable=True),
        sa.Column('departure_station', sa.String(), nullable=True),
        sa.Column('arrival_station', sa.String(), nullable=True),
        sa.Column('departure_time', sa.DateTime(), nullable=True),
        sa.Column('arrival_time', sa.DateTime(), nullable=True),
        sa.Column('fare', sa.Float(), nullable=True),
        sa.Column('transfer_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['route_id'], ['travel_routes.route_id'], ),
        sa.PrimaryKeyConstraint('detail_id')
    )
    op.create_index(op.f('ix_transportation_details_detail_id'), 'transportation_details', ['detail_id'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_index(op.f('ix_transportation_details_detail_id'), table_name='transportation_details')
    op.drop_table('transportation_details')
    op.drop_index(op.f('ix_travel_routes_route_id'), table_name='travel_routes')
    op.drop_table('travel_routes')
