"""merge heads

Revision ID: 46ae979c4203
Revises: 20240711_add_user_id_to_travel_course_likes, 21d1f2517000
Create Date: 2025-07-11 11:51:28.119865

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '46ae979c4203'
down_revision: str | Sequence[str] | None = ('20240711_add_user_id_to_travel_course_likes', '21d1f2517000')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
