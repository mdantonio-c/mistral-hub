"""dsn field for license_groups

Revision ID: 1cd1cab394b6
Revises: ea9aac95eb23
Create Date: 2021-01-12 15:31:43.223978

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1cd1cab394b6"
down_revision = "ea9aac95eb23"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "group_license", sa.Column("dballe_dsn", sa.String(length=64), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("group_license", "dballe_dsn")
    # ### end Alembic commands ###
