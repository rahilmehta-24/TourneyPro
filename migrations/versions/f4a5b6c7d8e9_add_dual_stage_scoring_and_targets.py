"""add dual stage scoring, stage targets, and group stats columns

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-11-27 10:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4a5b6c7d8e9'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Update categories table
    cat_cols = [c['name'] for c in inspector.get_columns('categories')]
    with op.batch_alter_table('categories', schema=None) as batch_op:
        if 'knockout_scoring_format' not in cat_cols:
            batch_op.add_column(sa.Column('knockout_scoring_format', sa.String(length=20), server_default='same', nullable=True))
        if 'win_by_margin' not in cat_cols:
            batch_op.add_column(sa.Column('win_by_margin', sa.Integer(), server_default='2', nullable=True))
        if 'score_cap' not in cat_cols:
            batch_op.add_column(sa.Column('score_cap', sa.Integer(), nullable=True))
        if 'semifinal_target' not in cat_cols:
            batch_op.add_column(sa.Column('semifinal_target', sa.Integer(), nullable=True))
        if 'final_target' not in cat_cols:
            batch_op.add_column(sa.Column('final_target', sa.Integer(), nullable=True))
        if 'has_third_place_match' not in cat_cols:
            batch_op.add_column(sa.Column('has_third_place_match', sa.Boolean(), server_default='0', nullable=True))
        if 'tiebreak_at' not in cat_cols:
            batch_op.add_column(sa.Column('tiebreak_at', sa.Integer(), server_default='6', nullable=True))
        if 'tiebreak_points' not in cat_cols:
            batch_op.add_column(sa.Column('tiebreak_points', sa.Integer(), server_default='7', nullable=True))
        if 'final_num_sets' not in cat_cols:
            batch_op.add_column(sa.Column('final_num_sets', sa.Integer(), nullable=True))

    # 2. Update participants table
    part_cols = [c['name'] for c in inspector.get_columns('participants')]
    with op.batch_alter_table('participants', schema=None) as batch_op:
        if 'group_points_conceded' not in part_cols:
            batch_op.add_column(sa.Column('group_points_conceded', sa.Integer(), server_default='0', nullable=True))
        if 'group_point_diff' not in part_cols:
            batch_op.add_column(sa.Column('group_point_diff', sa.Integer(), server_default='0', nullable=True))
        if 'group_sets_won' not in part_cols:
            batch_op.add_column(sa.Column('group_sets_won', sa.Integer(), server_default='0', nullable=True))
        if 'group_sets_lost' not in part_cols:
            batch_op.add_column(sa.Column('group_sets_lost', sa.Integer(), server_default='0', nullable=True))

    # 3. Update matches table
    match_cols = [c['name'] for c in inspector.get_columns('matches')]
    with op.batch_alter_table('matches', schema=None) as batch_op:
        if 'match_stage' not in match_cols:
            batch_op.add_column(sa.Column('match_stage', sa.String(length=20), nullable=True))
        if 'is_final_group_round' not in match_cols:
            batch_op.add_column(sa.Column('is_final_group_round', sa.Boolean(), server_default='0', nullable=True))
        if 'win_by_margin' not in match_cols:
            batch_op.add_column(sa.Column('win_by_margin', sa.Integer(), nullable=True))
        if 'score_cap' not in match_cols:
            batch_op.add_column(sa.Column('score_cap', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_column('score_cap')
        batch_op.drop_column('win_by_margin')
        batch_op.drop_column('is_final_group_round')
        batch_op.drop_column('match_stage')

    with op.batch_alter_table('participants', schema=None) as batch_op:
        batch_op.drop_column('group_sets_lost')
        batch_op.drop_column('group_sets_won')
        batch_op.drop_column('group_point_diff')
        batch_op.drop_column('group_points_conceded')

    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_column('final_num_sets')
        batch_op.drop_column('tiebreak_points')
        batch_op.drop_column('tiebreak_at')
        batch_op.drop_column('has_third_place_match')
        batch_op.drop_column('final_target')
        batch_op.drop_column('semifinal_target')
        batch_op.drop_column('score_cap')
        batch_op.drop_column('win_by_margin')
        batch_op.drop_column('knockout_scoring_format')
