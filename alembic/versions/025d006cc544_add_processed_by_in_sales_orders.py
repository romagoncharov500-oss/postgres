"""add processed_by in sales.orders

Revision ID: 025d006cc544
Revises: 583dc7bf1f2c
Create Date: 2026-07-11 20:32:07.119481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '025d006cc544'
down_revision: Union[str, None] = '583dc7bf1f2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())