"""001_initial_empty

Revision ID: 96f81c1ff1b8
Revises:
Create Date: 2026-05-02 12:09:49.822519

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "96f81c1ff1b8"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
