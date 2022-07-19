"""add trustomer product fields

Revision ID: 2d8ea21b1aa6
Revises: 2d01a355c380
Create Date: 2020-11-27 15:28:00.737749

"""
import sqlalchemy as sa
from alembic import op
from environs import Env
from she_logging import logger

# revision identifiers, used by Alembic.
revision = "2d8ea21b1aa6"
down_revision = "2d01a355c380"
branch_labels = None
depends_on = None


def upgrade():
    logger.info("Adding column 'product_name'")
    op.add_column("message", sa.Column("product_name", sa.String(), nullable=True))
    op.execute("UPDATE message SET product_name='gdm' WHERE product_name IS NULL")
    op.alter_column("message", "product_name", nullable=False)

    logger.info("Adding column 'trustomer_code'")
    trustomer_code: str = Env().str("CUSTOMER_CODE", "unknown")
    op.add_column("message", sa.Column("trustomer_code", sa.String(), nullable=True))
    op.execute(
        f"UPDATE message SET trustomer_code='{trustomer_code}' WHERE trustomer_code IS NULL"
    )
    op.alter_column("message", "trustomer_code", nullable=False)

    logger.info("Adding indexes")
    op.create_index(
        op.f("ix_message_product_name"), "message", ["product_name"], unique=False
    )
    op.create_index(op.f("ix_message_receiver"), "message", ["receiver"], unique=False)
    op.create_index(
        op.f("ix_message_trustomer_code"), "message", ["trustomer_code"], unique=False
    )


def downgrade():
    logger.info("Dropping columns 'trustomer_code' and 'product_name'")
    op.drop_column("message", "trustomer_code")
    op.drop_column("message", "product_name")
    op.drop_index(op.f("ix_message_trustomer_code"), table_name="message")
    op.drop_index(op.f("ix_message_receiver"), table_name="message")
    op.drop_index(op.f("ix_message_product_name"), table_name="message")
