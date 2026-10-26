"""add payment method and status fields

Revision ID: f2a4b8c91d03
Revises: 21e2eb139372
Create Date: 2026-10-24 15:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a4b8c91d03'
down_revision = '21e2eb139372'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'registrations' in tables:
        reg_cols = [c['name'] for c in inspector.get_columns('registrations')]
        with op.batch_alter_table('registrations', schema=None) as batch_op:
            if 'payment_method' not in reg_cols:
                batch_op.add_column(sa.Column('payment_method', sa.String(length=50), nullable=True))

    if 'participants' in tables:
        part_cols = [c['name'] for c in inspector.get_columns('participants')]
        with op.batch_alter_table('participants', schema=None) as batch_op:
            if 'payment_status' not in part_cols:
                batch_op.add_column(sa.Column('payment_status', sa.String(length=20), nullable=True, server_default='paid'))
            if 'payment_method' not in part_cols:
                batch_op.add_column(sa.Column('payment_method', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('participants', schema=None) as batch_op:
        batch_op.drop_column('payment_method')
        batch_op.drop_column('payment_status')

    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.drop_column('payment_method')
