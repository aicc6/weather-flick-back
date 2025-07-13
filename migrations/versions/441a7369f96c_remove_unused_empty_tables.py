"""remove_unused_empty_tables

Revision ID: 441a7369f96c
Revises: 3414a5163f27
Create Date: 2025-07-13 01:16:03.099397

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '441a7369f96c'
down_revision: Union[str, Sequence[str], None] = '3414a5163f27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop foreign key constraints that reference tables to be dropped
    # For destinations table
    op.drop_constraint('reviews_destination_id_fkey', 'reviews', type_='foreignkey')
    op.drop_constraint('fk_favorite_places_destination_id_destinations', 'favorite_places', type_='foreignkey')
    
    # Note: weather_data will be dropped, so its constraint will be removed automatically
    
    # Drop unused empty tables
    tables_to_drop = [
        'city_info',
        'legal_dong_codes',
        'weather_data',
        'historical_weather_daily',
        'destinations',
        'tour_destinations',
        'attraction_details',
        'tour_destination_details',
        'attraction_images',
        'tour_destination_images'
    ]
    
    for table in tables_to_drop:
        op.drop_table(table)


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate city_info
    op.create_table('city_info',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('city_name', sa.String(), nullable=True),
        sa.Column('region', sa.String(), nullable=True),
        sa.Column('population', sa.Integer(), nullable=True),
        sa.Column('area', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('attractions', sa.JSON(), nullable=True),
        sa.Column('weather_info', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate legal_dong_codes
    op.create_table('legal_dong_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('parent_code', sa.String(), nullable=True),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('sido_name', sa.String(), nullable=True),
        sa.Column('sigungu_name', sa.String(), nullable=True),
        sa.Column('eupmyeondong_name', sa.String(), nullable=True),
        sa.Column('level_depth', sa.Integer(), nullable=True),
        sa.Column('use_yn', sa.String(), nullable=True),
        sa.Column('raw_data_id', sa.UUID(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('processing_status', sa.String(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate weather_data
    op.create_table('weather_data',
        sa.Column('weather_id', sa.Integer(), nullable=False),
        sa.Column('destination_id', sa.Integer(), nullable=True),
        sa.Column('forecast_date', sa.Date(), nullable=True),
        sa.Column('temperature_max', sa.Float(), nullable=True),
        sa.Column('temperature_min', sa.Float(), nullable=True),
        sa.Column('humidity', sa.Float(), nullable=True),
        sa.Column('weather_condition', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('grid_x', sa.Integer(), nullable=True),
        sa.Column('grid_y', sa.Integer(), nullable=True),
        sa.Column('forecast_time', sa.DateTime(), nullable=True),
        sa.Column('base_date', sa.String(), nullable=True),
        sa.Column('base_time', sa.String(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('precipitation_probability', sa.Float(), nullable=True),
        sa.Column('precipitation_type', sa.String(), nullable=True),
        sa.Column('sky_condition', sa.String(), nullable=True),
        sa.Column('region_name', sa.String(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('weather_id')
    )
    
    # Recreate historical_weather_daily
    op.create_table('historical_weather_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('region_code', sa.String(), nullable=True),
        sa.Column('city_name', sa.String(), nullable=True),
        sa.Column('weather_date', sa.Date(), nullable=True),
        sa.Column('min_temperature', sa.Float(), nullable=True),
        sa.Column('max_temperature', sa.Float(), nullable=True),
        sa.Column('avg_temperature', sa.Float(), nullable=True),
        sa.Column('weather_condition', sa.String(), nullable=True),
        sa.Column('is_past', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate destinations
    op.create_table('destinations',
        sa.Column('destination_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('region', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('latitude', sa.DECIMAL(), nullable=True),
        sa.Column('longitude', sa.DECIMAL(), nullable=True),
        sa.Column('amenities', sa.JSON(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('recommendation_weight', sa.DECIMAL(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('province', sa.String(), nullable=False),
        sa.Column('is_indoor', sa.Boolean(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('destination_id')
    )
    
    # Recreate tour_destinations
    op.create_table('tour_destinations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content_id', sa.String(), nullable=True),
        sa.Column('region_code', sa.String(), nullable=True),
        sa.Column('destination_name', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('latitude', sa.DECIMAL(), nullable=True),
        sa.Column('longitude', sa.DECIMAL(), nullable=True),
        sa.Column('tel', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('sub_category', sa.String(), nullable=True),
        sa.Column('overview', sa.Text(), nullable=True),
        sa.Column('first_image', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate attraction_details
    op.create_table('attraction_details',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tourist_attraction_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate tour_destination_details
    op.create_table('tour_destination_details',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tour_destination_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate attraction_images
    op.create_table('attraction_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tourist_attraction_id', sa.Integer(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('image_description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate tour_destination_images
    op.create_table('tour_destination_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tour_destination_id', sa.Integer(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('image_description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate foreign key constraints
    op.create_foreign_key('weather_data_destination_id_fkey', 'weather_data', 'destinations', ['destination_id'], ['destination_id'])
    op.create_foreign_key('reviews_destination_id_fkey', 'reviews', 'destinations', ['destination_id'], ['destination_id'])
    op.create_foreign_key('fk_favorite_places_destination_id_destinations', 'favorite_places', 'destinations', ['destination_id'], ['destination_id'])
