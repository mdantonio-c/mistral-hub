"""notify_on_successful_request

Revision ID: 4610a4e35cec
Revises: 6f2d3541412e
Create Date: 2026-04-17 09:16:50.095378

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4610a4e35cec'
down_revision = '6f2d3541412e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'notify_on_successful_request',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('true'),
            )
        )


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('notify_on_successful_request')
