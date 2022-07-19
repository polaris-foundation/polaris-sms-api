"""redacted_column


Revision ID: 3551a2541495
Revises: 2d8ea21b1aa6
Create Date: 2020-12-03 12:31:18.638361

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3551a2541495"
down_revision = "2d8ea21b1aa6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("message", sa.Column("redacted", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_message_redacted"), "message", ["redacted"], unique=False)
    op.create_index(op.f("ix_message_status"), "message", ["status"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_message_status"), table_name="message")
    op.drop_index(op.f("ix_message_redacted"), table_name="message")
    op.drop_column("message", "redacted")
