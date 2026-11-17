"""add academy verification, academy applications, and membership status

Revision ID: d2b3c4d5e6f7
Revises: c1a2b3c4d5e6
Create Date: 2026-11-17 15:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2b3c4d5e6f7'
down_revision = 'c1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Update academies table
    academy_cols = [c['name'] for c in inspector.get_columns('academies')]
    with op.batch_alter_table('academies', schema=None) as batch_op:
        if 'status' not in academy_cols:
            batch_op.add_column(sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False))
        if 'address' not in academy_cols:
            batch_op.add_column(sa.Column('address', sa.String(length=255), nullable=True))
        if 'city' not in academy_cols:
            batch_op.add_column(sa.Column('city', sa.String(length=100), nullable=True))
        if 'state' not in academy_cols:
            batch_op.add_column(sa.Column('state', sa.String(length=100), nullable=True))
        if 'country' not in academy_cols:
            batch_op.add_column(sa.Column('country', sa.String(length=100), nullable=True))
        if 'contact_email' not in academy_cols:
            batch_op.add_column(sa.Column('contact_email', sa.String(length=120), nullable=True))
        if 'contact_phone' not in academy_cols:
            batch_op.add_column(sa.Column('contact_phone', sa.String(length=20), nullable=True))
        if 'sports_offered' not in academy_cols:
            batch_op.add_column(sa.Column('sports_offered', sa.Text(), nullable=True))
        if 'website_url' not in academy_cols:
            batch_op.add_column(sa.Column('website_url', sa.String(length=255), nullable=True))
        if 'logo_url' not in academy_cols:
            batch_op.add_column(sa.Column('logo_url', sa.String(length=255), nullable=True))
        if 'verified_at' not in academy_cols:
            batch_op.add_column(sa.Column('verified_at', sa.DateTime(), nullable=True))
        if 'verified_by_id' not in academy_cols:
            batch_op.add_column(sa.Column('verified_by_id', sa.Integer(), nullable=True))

    # 1.1 Update tournaments table for logo_url
    tourn_cols = [c['name'] for c in inspector.get_columns('tournaments')]
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        if 'logo_url' not in tourn_cols:
            batch_op.add_column(sa.Column('logo_url', sa.String(length=255), nullable=True))

    # 2. Update academy_members table
    member_cols = [c['name'] for c in inspector.get_columns('academy_members')]
    with op.batch_alter_table('academy_members', schema=None) as batch_op:
        if 'membership_status' not in member_cols:
            batch_op.add_column(sa.Column('membership_status', sa.String(length=20), server_default='ACTIVE', nullable=False))
        if 'left_at' not in member_cols:
            batch_op.add_column(sa.Column('left_at', sa.DateTime(), nullable=True))

    # 3. Update registrations table
    reg_cols = [c['name'] for c in inspector.get_columns('registrations')]
    with op.batch_alter_table('registrations', schema=None) as batch_op:
        if 'academy_id_snapshot' not in reg_cols:
            batch_op.add_column(sa.Column('academy_id_snapshot', sa.Integer(), nullable=True))

    # 4. Create academy_applications table if not exists
    tables = inspector.get_table_names()
    if 'academy_applications' not in tables:
        op.create_table(
            'academy_applications',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('applicant_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('address', sa.String(length=255), nullable=True),
            sa.Column('city', sa.String(length=100), nullable=True),
            sa.Column('state', sa.String(length=100), nullable=True),
            sa.Column('country', sa.String(length=100), nullable=True),
            sa.Column('contact_email', sa.String(length=120), nullable=False),
            sa.Column('contact_phone', sa.String(length=20), nullable=True),
            sa.Column('sports_offered', sa.Text(), nullable=True),
            sa.Column('website_url', sa.String(length=255), nullable=True),
            sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
            sa.Column('reviewed_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('academy_id', sa.Integer(), sa.ForeignKey('academies.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # 5. Create match_score_revisions table if not exists
    if 'match_score_revisions' not in tables:
        op.create_table(
            'match_score_revisions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('match_id', sa.Integer(), sa.ForeignKey('matches.id', ondelete='CASCADE'), nullable=False),
            sa.Column('edited_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('previous_score1', sa.String(length=50), nullable=True),
            sa.Column('previous_score2', sa.String(length=50), nullable=True),
            sa.Column('previous_winner_id', sa.Integer(), nullable=True),
            sa.Column('new_score1', sa.String(length=50), nullable=True),
            sa.Column('new_score2', sa.String(length=50), nullable=True),
            sa.Column('new_winner_id', sa.Integer(), nullable=True),
            sa.Column('reason', sa.String(length=255), nullable=False),
            sa.Column('explanation', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )


def downgrade():
    op.drop_table('match_score_revisions')
    op.drop_table('academy_applications')
    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.drop_column('academy_id_snapshot')
    with op.batch_alter_table('academy_members', schema=None) as batch_op:
        batch_op.drop_column('left_at')
        batch_op.drop_column('membership_status')
    with op.batch_alter_table('academies', schema=None) as batch_op:
        batch_op.drop_column('verified_by_id')
        batch_op.drop_column('verified_at')
        batch_op.drop_column('website_url')
        batch_op.drop_column('sports_offered')
        batch_op.drop_column('contact_phone')
        batch_op.drop_column('contact_email')
        batch_op.drop_column('country')
        batch_op.drop_column('state')
        batch_op.drop_column('city')
        batch_op.drop_column('address')
        batch_op.drop_column('status')
