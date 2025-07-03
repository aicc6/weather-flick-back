"""add_role_column_to_users

Revision ID: fb2ec0935be9
Revises: 2a45c1ef874e
Create Date: 2025-07-03 22:09:56.703400

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fb2ec0935be9'
down_revision: Union[str, Sequence[str], None] = '2a45c1ef874e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add role column to users table."""
    # Create enum type first
    userrole_enum = sa.Enum('USER', 'ADMIN', name='userrole')
    userrole_enum.create(op.get_bind())
    
    # Add role column to users table
    op.add_column('users', sa.Column('role', userrole_enum, nullable=True))
    
    # Set default value for existing users
    op.execute("UPDATE users SET role = 'USER' WHERE role IS NULL")
    
    # Make the column non-nullable after setting default values
    op.alter_column('users', 'role', nullable=False)


def downgrade() -> None:
    """Downgrade schema - Remove role column from users table."""
    op.drop_column('users', 'role')
    op.execute("DROP TYPE IF EXISTS userrole")