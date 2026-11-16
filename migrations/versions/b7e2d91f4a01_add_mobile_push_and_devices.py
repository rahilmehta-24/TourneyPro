"""add mobile push, notifications, and device tables

Revision ID: b7e2d91f4a01
Revises: f2a4b8c91d03
Create Date: 2026-11-15 12:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7e2d91f4a01'
down_revision = 'f2a4b8c91d03'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # 1. device_registrations table
    if 'device_registrations' not in tables:
        op.create_table(
            'device_registrations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('device_token', sa.String(length=512), nullable=False),
            sa.Column('platform', sa.String(length=20), nullable=False),
            sa.Column('device_name', sa.String(length=100), nullable=True),
            sa.Column('os_version', sa.String(length=50), nullable=True),
            sa.Column('app_version', sa.String(length=50), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('1')),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('device_token')
        )
        op.create_index('idx_device_reg_user', 'device_registrations', ['user_id'])
        op.create_index('idx_device_reg_token', 'device_registrations', ['device_token'])

    # 2. in_app_notifications table
    if 'in_app_notifications' not in tables:
        op.create_table(
            'in_app_notifications',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=150), nullable=False),
            sa.Column('body', sa.Text(), nullable=False),
            sa.Column('notification_type', sa.String(length=50), nullable=False),
            sa.Column('reference_type', sa.String(length=50), nullable=True),
            sa.Column('reference_id', sa.Integer(), nullable=True),
            sa.Column('is_read', sa.Boolean(), nullable=True, server_default=sa.text('0')),
            sa.Column('read_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_notifications_user_unread', 'in_app_notifications', ['user_id', 'is_read', 'created_at'])

    # 3. user_notification_preferences table
    if 'user_notification_preferences' not in tables:
        op.create_table(
            'user_notification_preferences',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('notify_match_called', sa.Boolean(), nullable=True, server_default=sa.text('1')),
            sa.Column('notify_draw_published', sa.Boolean(), nullable=True, server_default=sa.text('1')),
            sa.Column('notify_registration_updates', sa.Boolean(), nullable=True, server_default=sa.text('1')),
            sa.Column('notify_match_results', sa.Boolean(), nullable=True, server_default=sa.text('1')),
            sa.Column('notify_academy_announcements', sa.Boolean(), nullable=True, server_default=sa.text('1')),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id')
        )

    # 4. Composite indexes for high-throughput mobile performance
    if 'matches' in tables:
        match_indexes = [idx['name'] for idx in inspector.get_indexes('matches')]
        if 'idx_matches_category_round_num' not in match_indexes:
            op.create_index('idx_matches_category_round_num', 'matches', ['category_id', 'round', 'match_number'])

    if 'registrations' in tables:
        reg_indexes = [idx['name'] for idx in inspector.get_indexes('registrations')]
        if 'idx_registrations_user_tourn' not in reg_indexes:
            op.create_index('idx_registrations_user_tourn', 'registrations', ['user_id', 'tournament_id'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'registrations' in tables:
        reg_indexes = [idx['name'] for idx in inspector.get_indexes('registrations')]
        if 'idx_registrations_user_tourn' in reg_indexes:
            op.drop_index('idx_registrations_user_tourn', table_name='registrations')

    if 'matches' in tables:
        match_indexes = [idx['name'] for idx in inspector.get_indexes('matches')]
        if 'idx_matches_category_round_num' in match_indexes:
            op.drop_index('idx_matches_category_round_num', table_name='matches')

    if 'user_notification_preferences' in tables:
        op.drop_table('user_notification_preferences')

    if 'in_app_notifications' in tables:
        op.drop_index('idx_notifications_user_unread', table_name='in_app_notifications')
        op.drop_table('in_app_notifications')

    if 'device_registrations' in tables:
        op.drop_index('idx_device_reg_token', table_name='device_registrations')
        op.drop_index('idx_device_reg_user', table_name='device_registrations')
        op.drop_table('device_registrations')

