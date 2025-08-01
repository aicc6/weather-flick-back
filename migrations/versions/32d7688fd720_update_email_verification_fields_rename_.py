"""Update email verification fields: rename is_verified to is_email_verified in users table and remove is_verified from email_verifications table

Revision ID: 32d7688fd720
Revises: f5dbf3ed9a01
Create Date: 2025-06-30 17:42:28.257778

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '32d7688fd720'
down_revision: str | Sequence[str] | None = 'f5dbf3ed9a01'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('email_verifications', 'is_verified')
    op.add_column('users', sa.Column('is_email_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.drop_column('users', 'account_type')
    # Handle NULL values in weather_data.destination_id before setting NOT NULL
    op.execute("DELETE FROM weather_data WHERE destination_id IS NULL")
    op.alter_column('weather_data', 'destination_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('weather_data', 'base_date')
    op.drop_column('weather_data', 'precipitation_probability')
    op.drop_column('weather_data', 'region_name')
    op.drop_column('weather_data', 'grid_x')
    op.drop_column('weather_data', 'raw_data')
    op.drop_column('weather_data', 'precipitation_type')
    op.drop_column('weather_data', 'grid_y')
    op.drop_column('weather_data', 'base_time')
    op.drop_column('weather_data', 'temperature')
    op.drop_column('weather_data', 'forecast_time')
    op.drop_column('weather_data', 'sky_condition')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('weather_data', sa.Column('sky_condition', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('weather_data', sa.Column('forecast_time', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('weather_data', sa.Column('temperature', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('weather_data', sa.Column('base_time', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('weather_data', sa.Column('grid_y', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('weather_data', sa.Column('precipitation_type', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('weather_data', sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.add_column('weather_data', sa.Column('grid_x', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('weather_data', sa.Column('region_name', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('weather_data', sa.Column('precipitation_probability', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('weather_data', sa.Column('base_date', sa.DATE(), autoincrement=False, nullable=True))
    op.alter_column('weather_data', 'destination_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.add_column('users', sa.Column('account_type', postgresql.ENUM('USER', 'ADMIN', name='accounttype'), autoincrement=False, nullable=True))
    op.drop_column('users', 'is_email_verified')
    op.add_column('email_verifications', sa.Column('is_verified', sa.BOOLEAN(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
