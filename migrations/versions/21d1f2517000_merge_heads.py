"""merge heads

Revision ID: 21d1f2517000
Revises: 20240610_add_travel_course_likes, 8831066fc75a
Create Date: 2025-07-11 10:55:23.706621

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '21d1f2517000'
down_revision: str | Sequence[str] | None = ('20240610_add_travel_course_likes', '8831066fc75a')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
