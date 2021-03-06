"""open dataset flag for user

Revision ID: 0a8ddda4eb56
Revises: f343b188fb38
Create Date: 2020-11-13 16:45:15.741531

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0a8ddda4eb56"
down_revision = "f343b188fb38"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("grp_licence_association")
    op.add_column("user", sa.Column("open_dataset", sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("user", "open_dataset")
    op.create_table(
        "grp_licence_association",
        sa.Column("grp_licence_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("user_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["grp_licence_id"],
            ["group_license.id"],
            name="grp_licence_association_grp_licence_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name="grp_licence_association_user_id_fkey"
        ),
    )
    # ### end Alembic commands ###
