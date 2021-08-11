"""request_expiration_deletion

Revision ID: 6ad6f2099373
Revises: 4ae0e00df227
Create Date: 2021-08-11 13:56:28.857307

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "6ad6f2099373"
down_revision = "4ae0e00df227"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "user", sa.Column("requests_expiration_delete", sa.Boolean(), nullable=True)
    )
    role = sa.table("user", sa.Column("requests_expiration_delete"))
    op.execute(role.update().values(requests_expiration_delete=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("user", "requests_expiration_delete")
    # ### end Alembic commands ###
