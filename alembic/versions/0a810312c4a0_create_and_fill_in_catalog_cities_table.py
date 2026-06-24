"""create and fill in catalog.cities table

Revision ID: 0a810312c4a0
Revises: bc9109abba45
Create Date: 2026-06-24 19:12:15.806446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a810312c4a0'
down_revision: Union[str, None] = 'bc9109abba45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())