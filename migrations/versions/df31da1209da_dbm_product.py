"""dbm_product

Revision ID: df31da1209da
Revises: 3551a2541495
Create Date: 2022-01-10 17:02:10.288974

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "df31da1209da"
down_revision = "3551a2541495"
branch_labels = None
depends_on = None


def upgrade():
    print("Started updating product name to 'dbm'")
    conn = op.get_bind()
    conn.execute(
        """
    UPDATE message
    SET product_name = 'dbm'
    WHERE receiver in (
        SELECT distinct(receiver) FROM message
        WHERE content like 'Thank you for using DBm%%' 
        AND product_name != 'dbm'
    )
    OR sender in (
        SELECT distinct(receiver) FROM message
        WHERE content like 'Thank you for using DBm%%' 
        AND product_name != 'dbm'
    )
    """
    )
    print("Finished update product name to 'dbm'")


def downgrade():
    print("downgrade is not possible")
