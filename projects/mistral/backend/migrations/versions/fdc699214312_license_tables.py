"""empty message

Revision ID: fdc699214312
Revises: 5850215a445e
Create Date: 2020-07-03 07:37:02.647251

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fdc699214312"
down_revision = "5850215a445e"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "attribution",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("descr", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attribution_name"), "attribution", ["name"], unique=False)
    op.create_table(
        "group_license",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("descr", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_group_license_name"), "group_license", ["name"], unique=False
    )
    op.create_table(
        "license",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_license_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("descr", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_license_id"],
            ["group_license.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_license_name"), "license", ["name"], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_license_name"), table_name="license")
    op.drop_table("license")
    op.drop_index(op.f("ix_group_license_name"), table_name="group_license")
    op.drop_table("group_license")
    op.drop_index(op.f("ix_attribution_name"), table_name="attribution")
    op.drop_table("attribution")
    # ### end Alembic commands ###
