"""consolidate_region_tables

Revision ID: accdbd0b595a
Revises: 441a7369f96c
Create Date: 2025-07-13 01:24:12.869011

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'accdbd0b595a'
down_revision: str | Sequence[str] | None = '441a7369f96c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Consolidate region tables into regions table."""

    # 1. regions 테이블에 필요한 컬럼 추가
    op.add_column('regions', sa.Column('grid_x', sa.Integer(), nullable=True))
    op.add_column('regions', sa.Column('grid_y', sa.Integer(), nullable=True))
    op.add_column('regions', sa.Column('region_name_full', sa.String(), nullable=True))
    op.add_column('regions', sa.Column('region_name_en', sa.String(), nullable=True))
    op.add_column('regions', sa.Column('center_latitude', sa.DECIMAL(10, 8), nullable=True))
    op.add_column('regions', sa.Column('center_longitude', sa.DECIMAL(11, 8), nullable=True))
    op.add_column('regions', sa.Column('administrative_code', sa.String(), nullable=True))
    op.add_column('regions', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True))
    op.add_column('regions', sa.Column('boundary_data', sa.JSON(), nullable=True))

    # 2. unified_regions에서 regions로 데이터 마이그레이션
    op.execute("""
        UPDATE regions r
        SET 
            region_name_full = ur.region_name_full,
            region_name_en = ur.region_name_en,
            center_latitude = ur.center_latitude,
            center_longitude = ur.center_longitude,
            administrative_code = ur.administrative_code,
            is_active = ur.is_active,
            boundary_data = ur.boundary_data
        FROM unified_regions ur
        WHERE r.region_code = ur.region_code
    """)

    # 3. unified_regions에만 있는 데이터를 regions로 추가
    # parent_region_id가 UUID이므로, parent unified_region의 region_code를 찾아 매핑
    op.execute("""
        INSERT INTO regions (
            region_code, region_name, parent_region_code, region_level,
            latitude, longitude, created_at, updated_at,
            region_name_full, region_name_en, center_latitude, center_longitude,
            administrative_code, is_active
        )
        SELECT 
            ur.region_code, ur.region_name, 
            parent_ur.region_code as parent_region_code,  -- UUID를 region_code로 변환
            ur.region_level,
            ur.center_latitude, ur.center_longitude, ur.created_at, ur.updated_at,
            ur.region_name_full, ur.region_name_en, ur.center_latitude, ur.center_longitude,
            ur.administrative_code, ur.is_active
        FROM unified_regions ur
        LEFT JOIN unified_regions parent_ur ON ur.parent_region_id = parent_ur.region_id
        WHERE NOT EXISTS (
            SELECT 1 FROM regions r 
            WHERE r.region_code = ur.region_code
        )
    """)

    # 4. weather_regions에서 grid 정보 업데이트
    op.execute("""
        UPDATE regions r
        SET 
            grid_x = wr.grid_x,
            grid_y = wr.grid_y
        FROM weather_regions wr
        WHERE r.region_code = wr.region_code
    """)

    # 5. 외래 키 제약조건 삭제
    op.drop_constraint('region_api_mappings_region_id_fkey', 'region_api_mappings', type_='foreignkey')
    op.drop_constraint('coordinate_transformations_region_id_fkey', 'coordinate_transformations', type_='foreignkey')

    # 6. unified_regions, weather_regions 테이블 삭제
    op.drop_table('unified_regions')
    op.drop_table('weather_regions')


def downgrade() -> None:
    """Restore unified_regions and weather_regions tables."""

    # 1. unified_regions 테이블 재생성
    op.create_table('unified_regions',
        sa.Column('region_id', sa.UUID(), nullable=False),
        sa.Column('region_code', sa.String(), nullable=False),
        sa.Column('region_name', sa.String(), nullable=False),
        sa.Column('region_name_full', sa.String(), nullable=True),
        sa.Column('region_name_en', sa.String(), nullable=True),
        sa.Column('parent_region_id', sa.UUID(), nullable=True),
        sa.Column('region_level', sa.Integer(), nullable=False),
        sa.Column('center_latitude', sa.DECIMAL(10, 8), nullable=True),
        sa.Column('center_longitude', sa.DECIMAL(11, 8), nullable=True),
        sa.Column('boundary_data', sa.JSON(), nullable=True),
        sa.Column('administrative_code', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_region_id'], ['unified_regions.region_id'], ),
        sa.PrimaryKeyConstraint('region_id'),
        sa.UniqueConstraint('region_code')
    )

    # 2. weather_regions 테이블 재생성
    op.create_table('weather_regions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('region_code', sa.String(), nullable=False),
        sa.Column('region_name', sa.String(), nullable=False),
        sa.Column('grid_x', sa.Integer(), nullable=False),
        sa.Column('grid_y', sa.Integer(), nullable=False),
        sa.Column('latitude', sa.DECIMAL(10, 8), nullable=True),
        sa.Column('longitude', sa.DECIMAL(11, 8), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('region_code')
    )

    # 3. 외래 키 복원
    op.create_foreign_key('region_api_mappings_region_id_fkey', 'region_api_mappings', 'unified_regions', ['region_id'], ['region_id'])
    op.create_foreign_key('coordinate_transformations_region_id_fkey', 'coordinate_transformations', 'unified_regions', ['region_id'], ['region_id'])

    # 4. regions 테이블에서 추가된 컬럼 제거
    op.drop_column('regions', 'boundary_data')
    op.drop_column('regions', 'is_active')
    op.drop_column('regions', 'administrative_code')
    op.drop_column('regions', 'center_longitude')
    op.drop_column('regions', 'center_latitude')
    op.drop_column('regions', 'region_name_en')
    op.drop_column('regions', 'region_name_full')
    op.drop_column('regions', 'grid_y')
    op.drop_column('regions', 'grid_x')
