"""add category scheduling columns

Revision ID: 21e2eb139372
Revises: e7cb93d109e7
Create Date: 2026-10-23 10:32:25.557585

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '21e2eb139372'
down_revision = 'e7cb93d109e7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cat_cols = [c['name'] for c in inspector.get_columns('categories')]
    with op.batch_alter_table('categories', schema=None) as batch_op:
        if 'start_date' not in cat_cols:
            batch_op.add_column(sa.Column('start_date', sa.Date(), nullable=True))
        if 'end_date' not in cat_cols:
            batch_op.add_column(sa.Column('end_date', sa.Date(), nullable=True))
        if 'start_time' not in cat_cols:
            batch_op.add_column(sa.Column('start_time', sa.String(length=5), nullable=True))
        if 'end_time' not in cat_cols:
            batch_op.add_column(sa.Column('end_time', sa.String(length=5), nullable=True))
        if 'daily_schedule' not in cat_cols:
            batch_op.add_column(sa.Column('daily_schedule', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_column('daily_schedule')
        batch_op.drop_column('end_time')
        batch_op.drop_column('start_time')
        batch_op.drop_column('end_date')
        batch_op.drop_column('start_date')
