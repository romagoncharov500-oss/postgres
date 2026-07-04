"""create inventory schema

Revision ID: 583dc7bf1f2c
Revises: 0a810312c4a0
Create Date: 2026-06-27 19:19:37.460783

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '583dc7bf1f2c'
down_revision: Union[str, None] = '0a810312c4a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())