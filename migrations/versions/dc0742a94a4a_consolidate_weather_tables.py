"""consolidate_weather_tables

Revision ID: dc0742a94a4a
Revises: accdbd0b595a
Create Date: 2025-07-13 07:53:19.740600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc0742a94a4a'
down_revision: Union[str, Sequence[str], None] = 'accdbd0b595a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Consolidate weather tables into weather_forecasts table."""
    
    # 0. weather_forecasts 테이블 구조 수정 - forecast_time을 날짜/시간 타입으로 변경
    op.execute("""
        -- 기존 forecast_time 데이터 백업
        ALTER TABLE weather_forecasts ADD COLUMN IF NOT EXISTS forecast_time_backup VARCHAR(4);
        UPDATE weather_forecasts SET forecast_time_backup = forecast_time WHERE forecast_time IS NOT NULL;
        
        -- forecast_time 컬럼을 timestamp로 변경
        ALTER TABLE weather_forecasts DROP COLUMN forecast_time;
        ALTER TABLE weather_forecasts ADD COLUMN forecast_time TIMESTAMP;
    """)
    
    # 1. weather_forecasts 테이블에 forecast_type 컬럼이 없으면 추가
    # 이미 존재할 수 있으므로 체크 후 추가
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'weather_forecasts' 
                AND column_name = 'forecast_type'
            ) THEN
                ALTER TABLE weather_forecasts 
                ADD COLUMN forecast_type VARCHAR;
            END IF;
        END$$;
    """)
    
    # 2. current_weather 데이터를 weather_forecasts로 마이그레이션
    op.execute("""
        INSERT INTO weather_forecasts (
            region_code, nx, ny, forecast_time, temperature, humidity, 
            precipitation, wind_speed, wind_direction, sky_condition, 
            weather_condition, base_date, base_time, forecast_type, forecast_date, created_at
        )
        SELECT 
            cw.region_code,
            COALESCE(r.grid_x, 0) as nx,
            COALESCE(r.grid_y, 0) as ny,
            cw.observed_at as forecast_time,
            cw.temperature,
            cw.humidity,
            cw.precipitation,
            cw.wind_speed,
            cw.wind_direction,
            '' as sky_condition,
            cw.weather_condition,
            TO_CHAR(cw.observed_at, 'YYYYMMDD') as base_date,
            TO_CHAR(cw.observed_at, 'HH24MI') as base_time,
            'current' as forecast_type,
            DATE(cw.observed_at) as forecast_date,
            cw.created_at
        FROM current_weather cw
        LEFT JOIN regions r ON cw.region_code = r.region_code
    """)
    
    # 3. city_weather_data를 weather_forecasts로 마이그레이션
    op.execute("""
        INSERT INTO weather_forecasts (
            region_code, nx, ny, forecast_time, temperature, humidity, 
            precipitation, wind_speed, wind_direction, sky_condition, 
            weather_condition, base_date, base_time, forecast_type, forecast_date, created_at
        )
        SELECT 
            r.region_code,
            cwd.nx,
            cwd.ny,
            cwd.forecast_time,
            cwd.temperature,
            cwd.humidity,
            cwd.precipitation,
            cwd.wind_speed,
            cwd.wind_direction,
            cwd.sky_condition,
            cwd.weather_description as weather_condition,
            cwd.base_date,
            cwd.base_time,
            'city' as forecast_type,
            DATE(cwd.forecast_time) as forecast_date,
            cwd.created_at
        FROM city_weather_data cwd
        LEFT JOIN regions r ON r.region_name = cwd.city_name
        WHERE r.region_code IS NOT NULL
    """)
    
    # 4. 기존 weather_forecasts 데이터의 forecast_type 업데이트
    op.execute("""
        UPDATE weather_forecasts 
        SET forecast_type = 'forecast' 
        WHERE forecast_type IS NULL
    """)
    
    # 5. 삭제할 테이블들 삭제
    op.drop_table('current_weather')
    op.drop_table('city_weather_data')


def downgrade() -> None:
    """Restore current_weather and city_weather_data tables."""
    
    # 1. current_weather 테이블 재생성
    op.create_table('current_weather',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('region_code', sa.String(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('feels_like', sa.Float(), nullable=True),
        sa.Column('humidity', sa.Integer(), nullable=True),
        sa.Column('precipitation', sa.Float(), nullable=True),
        sa.Column('wind_speed', sa.Float(), nullable=True),
        sa.Column('wind_direction', sa.Integer(), nullable=True),
        sa.Column('weather_condition', sa.String(), nullable=True),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_current_weather_region_code'), 'current_weather', ['region_code'], unique=False)
    
    # 2. city_weather_data 테이블 재생성
    op.create_table('city_weather_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('city_name', sa.String(), nullable=False),
        sa.Column('nx', sa.Integer(), nullable=False),
        sa.Column('ny', sa.Integer(), nullable=False),
        sa.Column('base_date', sa.String(8), nullable=False),
        sa.Column('base_time', sa.String(4), nullable=False),
        sa.Column('forecast_time', sa.DateTime(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('humidity', sa.Float(), nullable=True),
        sa.Column('precipitation', sa.Float(), nullable=True),
        sa.Column('precipitation_type', sa.String(), nullable=True),
        sa.Column('wind_speed', sa.Float(), nullable=True),
        sa.Column('wind_direction', sa.Float(), nullable=True),
        sa.Column('sky_condition', sa.String(), nullable=True),
        sa.Column('weather_description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_city_weather_city_forecast', 'city_weather_data', ['city_name', 'forecast_time'], unique=False)
    
    # 3. weather_forecasts에서 forecast_type 컬럼 제거
    op.drop_column('weather_forecasts', 'forecast_type')
