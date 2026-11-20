"""add flexible registration and csv import

Revision ID: e3f4a5b6c7d8
Revises: d2b3c4d5e6f7
Create Date: 2026-11-20 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3f4a5b6c7d8'
down_revision = 'd2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Update tournaments table
    tourn_cols = [c['name'] for c in inspector.get_columns('tournaments')]
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        if 'format_status' not in tourn_cols:
            batch_op.add_column(sa.Column('format_status', sa.String(length=20), server_default='NOT_DECIDED', nullable=False))
        if 'registration_status' not in tourn_cols:
            batch_op.add_column(sa.Column('registration_status', sa.String(length=20), server_default='DRAFT', nullable=False))
        if 'registration_opens_at' not in tourn_cols:
            batch_op.add_column(sa.Column('registration_opens_at', sa.DateTime(), nullable=True))
        if 'is_published' not in tourn_cols:
            batch_op.add_column(sa.Column('is_published', sa.Boolean(), server_default='1', nullable=False))

    # 2. Update categories table
    cat_cols = [c['name'] for c in inspector.get_columns('categories')]
    with op.batch_alter_table('categories', schema=None) as batch_op:
        if 'format' in cat_cols:
            batch_op.alter_column('format', existing_type=sa.String(length=50), nullable=True)
        if 'format_status' not in cat_cols:
            batch_op.add_column(sa.Column('format_status', sa.String(length=20), server_default='NOT_DECIDED', nullable=False))
        if 'registration_status' not in cat_cols:
            batch_op.add_column(sa.Column('registration_status', sa.String(length=20), server_default='OPEN', nullable=False))
        if 'is_registration_open' not in cat_cols:
            batch_op.add_column(sa.Column('is_registration_open', sa.Boolean(), server_default='1', nullable=False))

    # 3. Create import_batches table if not exists
    tables = inspector.get_table_names()
    if 'import_batches' not in tables:
        op.create_table(
            'import_batches',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tournament_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('filename', sa.String(length=255), nullable=False),
            sa.Column('file_hash', sa.String(length=64), nullable=False),
            sa.Column('total_rows', sa.Integer(), server_default='0', nullable=True),
            sa.Column('valid_rows', sa.Integer(), server_default='0', nullable=True),
            sa.Column('invalid_rows', sa.Integer(), server_default='0', nullable=True),
            sa.Column('duplicate_rows', sa.Integer(), server_default='0', nullable=True),
            sa.Column('imported_rows', sa.Integer(), server_default='0', nullable=True),
            sa.Column('status', sa.String(length=30), server_default='PENDING_CONFIRMATION', nullable=False),
            sa.Column('error_data', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('import_batches', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_import_batches_file_hash'), ['file_hash'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'import_batches' in tables:
        with op.batch_alter_table('import_batches', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_import_batches_file_hash'))
        op.drop_table('import_batches')

    cat_cols = [c['name'] for c in inspector.get_columns('categories')]
    with op.batch_alter_table('categories', schema=None) as batch_op:
        if 'is_registration_open' in cat_cols:
            batch_op.drop_column('is_registration_open')
        if 'registration_status' in cat_cols:
            batch_op.drop_column('registration_status')
        if 'format_status' in cat_cols:
            batch_op.drop_column('format_status')

    tourn_cols = [c['name'] for c in inspector.get_columns('tournaments')]
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        if 'is_published' in tourn_cols:
            batch_op.drop_column('is_published')
        if 'registration_opens_at' in tourn_cols:
            batch_op.drop_column('registration_opens_at')
        if 'registration_status' in tourn_cols:
            batch_op.drop_column('registration_status')
        if 'format_status' in tourn_cols:
            batch_op.drop_column('format_status')
