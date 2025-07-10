"""merge heads

Revision ID: 09a536f1e451
Revises: 20240610_add_reviews_recommend_table, travel_routes_001
Create Date: 2025-07-10 12:05:45.601154

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09a536f1e451'
down_revision: Union[str, Sequence[str], None] = ('20240610_add_reviews_recommend_table', 'travel_routes_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
