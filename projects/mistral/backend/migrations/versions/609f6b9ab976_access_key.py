"""access key

Revision ID: 609f6b9ab976
Revises: 355c4eeed661
Create Date: 2025-11-13 12:51:11.915486

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "609f6b9ab976"
down_revision = "355c4eeed661"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "access_key",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("creation", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expiration", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.String(length=128), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    with op.batch_alter_table("access_key", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_access_key_key"), ["key"], unique=True)


def downgrade():
    with op.batch_alter_table("access_key", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_access_key_key"))

    op.drop_table("access_key")
