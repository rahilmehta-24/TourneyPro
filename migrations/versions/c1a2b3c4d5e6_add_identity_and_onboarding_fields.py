"""add identity, email verification, and two-stage onboarding fields

Revision ID: c1a2b3c4d5e6
Revises: b7e2d91f4a01
Create Date: 2026-11-17 14:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1a2b3c4d5e6'
down_revision = 'b7e2d91f4a01'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_cols = [c['name'] for c in inspector.get_columns('users')]
    player_cols = [c['name'] for c in inspector.get_columns('players')]

    with op.batch_alter_table('users', schema=None) as batch_op:
        if 'full_name' not in user_cols:
            batch_op.add_column(sa.Column('full_name', sa.String(length=120), nullable=True))
        if 'phone_number' not in user_cols:
            batch_op.add_column(sa.Column('phone_number', sa.String(length=20), nullable=True))
        if 'is_email_verified' not in user_cols:
            batch_op.add_column(sa.Column('is_email_verified', sa.Boolean(), nullable=True, server_default=sa.text('0')))
        if 'email_verification_token' not in user_cols:
            batch_op.add_column(sa.Column('email_verification_token', sa.String(length=100), nullable=True))
            batch_op.create_index('idx_users_email_verification_token', ['email_verification_token'])
        if 'email_verified_at' not in user_cols:
            batch_op.add_column(sa.Column('email_verified_at', sa.DateTime(), nullable=True))
        if 'password_reset_token' not in user_cols:
            batch_op.add_column(sa.Column('password_reset_token', sa.String(length=100), nullable=True))
        if 'password_reset_expires_at' not in user_cols:
            batch_op.add_column(sa.Column('password_reset_expires_at', sa.DateTime(), nullable=True))
        if 'registration_intent' not in user_cols:
            batch_op.add_column(sa.Column('registration_intent', sa.String(length=20), nullable=True, server_default='user'))
        if 'profile_completed' not in user_cols:
            batch_op.add_column(sa.Column('profile_completed', sa.Boolean(), nullable=True, server_default=sa.text('0')))
        if 'completion_percentage' not in user_cols:
            batch_op.add_column(sa.Column('completion_percentage', sa.Integer(), nullable=True, server_default=sa.text('0')))
        if 'account_status' not in user_cols:
            batch_op.add_column(sa.Column('account_status', sa.String(length=20), nullable=True, server_default='ACTIVE'))

    with op.batch_alter_table('players', schema=None) as batch_op:
        if 'profile_status' not in player_cols:
            batch_op.add_column(sa.Column('profile_status', sa.String(length=20), nullable=True, server_default='incomplete'))
        if 'emergency_contact_name' not in player_cols:
            batch_op.add_column(sa.Column('emergency_contact_name', sa.String(length=100), nullable=True))
        if 'emergency_contact_phone' not in player_cols:
            batch_op.add_column(sa.Column('emergency_contact_phone', sa.String(length=20), nullable=True))
        if 'primary_sport' not in player_cols:
            batch_op.add_column(sa.Column('primary_sport', sa.String(length=50), nullable=True, server_default='Tennis'))
        if 'skill_level' not in player_cols:
            batch_op.add_column(sa.Column('skill_level', sa.String(length=20), nullable=True))
        if 'preferred_competition_category' not in player_cols:
            batch_op.add_column(sa.Column('preferred_competition_category', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.drop_column('preferred_competition_category')
        batch_op.drop_column('skill_level')
        batch_op.drop_column('primary_sport')
        batch_op.drop_column('emergency_contact_phone')
        batch_op.drop_column('emergency_contact_name')
        batch_op.drop_column('profile_status')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('idx_users_email_verification_token')
        batch_op.drop_column('account_status')
        batch_op.drop_column('completion_percentage')
        batch_op.drop_column('profile_completed')
        batch_op.drop_column('registration_intent')
        batch_op.drop_column('password_reset_expires_at')
        batch_op.drop_column('password_reset_token')
        batch_op.drop_column('email_verified_at')
        batch_op.drop_column('email_verification_token')
        batch_op.drop_column('is_email_verified')
        batch_op.drop_column('phone_number')
        batch_op.drop_column('full_name')

