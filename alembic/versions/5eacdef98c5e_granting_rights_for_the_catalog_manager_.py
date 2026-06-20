"""granting rights for the catalog_manager and sales_manager roles

Revision ID: 5eacdef98c5e
Revises: 8eb32655fe9a
Create Date: 2026-06-20 21:02:29.607355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5eacdef98c5e'
down_revision: Union[str, None] = '8eb32655fe9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())