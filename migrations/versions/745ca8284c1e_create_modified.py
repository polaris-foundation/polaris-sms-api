"""create_modified

Revision ID: 745ca8284c1e
Revises: f5c5ab61577c
Create Date: 2018-04-24 08:41:37.740158

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "745ca8284c1e"
down_revision = "f5c5ab61577c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "message",
        sa.Column("created_by_", sa.String(), nullable=False, server_default="sys"),
    )
    op.add_column(
        "message",
        sa.Column("modified_by_", sa.String(), nullable=False, server_default="sys"),
    )


def downgrade():
    op.drop_column("message", "modified_by_")
    op.drop_column("message", "created_by_")
