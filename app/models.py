from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Tournament(db.Model):
    __tablename__ = 'tournaments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    creator_name = db.Column(db.String(100))
    name = db.Column(db.String(200), nullable=False)
    url_slug = db.Column(db.String(200), unique=True, nullable=False)
    description = db.Column(db.Text)
    game_info = db.Column(db.String(200))
    format = db.Column(db.String(50))  # Legacy field, kept for backward compatibility
    tournament_type = db.Column(db.String(20), default='single_stage')
    status = db.Column(db.String(20), default='setup')  # setup, registration, in_progress, completed
    max_participants = db.Column(db.Integer)
    is_private = db.Column(db.Boolean, default=False)
    has_categories = db.Column(db.Boolean, default=False)  # True if using category system
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    num_sets = db.Column(db.Integer, default=1)  # 1, 2 or 3 sets
    games_per_set = db.Column(db.Integer, default=6)  # games to win a set

    # Relationships
    categories = db.relationship('Category', backref='tournament', lazy=True, cascade='all, delete-orphan')
    participants = db.relationship('Participant', backref='tournament', lazy=True, cascade='all, delete-orphan')
    matches = db.relationship('Match', backref='tournament', lazy=True, cascade='all, delete-orphan')
    settings = db.relationship('TournamentSettings', backref='tournament', uselist=False, cascade='all, delete-orphan')

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)  # e.g., "Men's Singles", "Women's Doubles"
    gender = db.Column(db.String(50), default='Unspecified')
    age_category = db.Column(db.String(50), default='Unspecified')
    format = db.Column(db.String(50), nullable=False)  # single_elimination, double_elimination, round_robin, group_stage
    status = db.Column(db.String(20), default='setup')  # setup, in_progress, completed
    max_participants = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    num_sets = db.Column(db.Integer, default=1)  # 1, 2 or 3 sets
    games_per_set = db.Column(db.Integer, default=6)  # games to win a set

    # Group stage specific fields
    has_group_stage = db.Column(db.Boolean, default=False)
    num_groups = db.Column(db.Integer)
    teams_per_group = db.Column(db.Integer)
    matches_per_team_pair = db.Column(db.Integer, default=1)  # Custom matches between teams in group
    qualifiers_per_group = db.Column(db.Integer)  # How many advance to knockout
    allow_lucky_losers = db.Column(db.Boolean, default=False)
    max_players_per_team = db.Column(db.Integer)
    total_games = db.Column(db.Integer)
    scoring_format = db.Column(db.String(20), default='games') # 'games' or 'points'
    points_to_win = db.Column(db.Integer)

    # Relationships
    participants = db.relationship('Participant', backref='category', lazy=True, cascade='all, delete-orphan')
    matches = db.relationship('Match', backref='category', lazy=True, cascade='all, delete-orphan')
    groups = db.relationship('Group', backref='category', lazy=True, cascade='all, delete-orphan')

class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)  # "Group A", "Group B", etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    participants = db.relationship('Participant', backref='group', lazy=True)
    matches = db.relationship('Match', backref='group', lazy=True)

class Participant(db.Model):
    __tablename__ = 'participants'

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))  # Nullable for backward compatibility
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))  # For group stage
    player_id = db.Column(db.Integer, db.ForeignKey('players.id')) # Link to global player
    player2_id = db.Column(db.Integer, db.ForeignKey('players.id')) # Link to global player 2 for Doubles
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    seed = db.Column(db.Integer)  # Auto-assigned seed
    manual_seed = db.Column(db.Integer)  # Manually assigned seed (takes priority)
    checked_in = db.Column(db.Boolean, default=False)
    eliminated = db.Column(db.Boolean, default=False)
    final_rank = db.Column(db.Integer)  # 1=Winner, 2=Runner-up, 3-4=Semi-finalists

    # Group stage stats
    group_wins = db.Column(db.Integer, default=0)
    group_losses = db.Column(db.Integer, default=0)
    group_points = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))  # Nullable for backward compatibility
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))  # For group stage matches
    round = db.Column(db.Integer, nullable=False)
    match_number = db.Column(db.Integer, nullable=False)
    participant1_id = db.Column(db.Integer, db.ForeignKey('participants.id'))
    participant2_id = db.Column(db.Integer, db.ForeignKey('participants.id'))
    winner_id = db.Column(db.Integer, db.ForeignKey('participants.id'))
    score1 = db.Column(db.String(50))
    score2 = db.Column(db.String(50))
    bracket_type = db.Column(db.String(20), default='main')  # main, winners, losers
    match_type = db.Column(db.String(20), default='knockout')  # knockout, group_stage, round_robin
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    scheduled_time = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Match-specific scoring overrides (only for knockout)
    scoring_format = db.Column(db.String(20)) # 'games', 'points', or None to inherit
    num_sets = db.Column(db.Integer)
    games_per_set = db.Column(db.Integer)
    points_to_win = db.Column(db.Integer)

    # Relationships for participants
    participant1 = db.relationship('Participant', foreign_keys=[participant1_id], backref='matches_as_p1')
    participant2 = db.relationship('Participant', foreign_keys=[participant2_id], backref='matches_as_p2')
    winner = db.relationship('Participant', foreign_keys=[winner_id], backref='matches_won')

class TournamentSettings(db.Model):
    __tablename__ = 'tournament_settings'

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), unique=True, nullable=False)
    allow_self_registration = db.Column(db.Boolean, default=False)
    require_check_in = db.Column(db.Boolean, default=False)
    allow_match_attachments = db.Column(db.Boolean, default=False)
    hide_seeds = db.Column(db.Boolean, default=False)
    quick_advance = db.Column(db.Boolean, default=False)
    custom_round_labels = db.Column(db.Text)  # JSON string
    registration_fields = db.Column(db.Text)  # JSON string

class MatchAttachment(db.Model):
    __tablename__ = 'match_attachments'

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    match = db.relationship('Match', backref='attachments')
    participant = db.relationship('Participant', backref='attachments')

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'superadmin', 'admin', 'user'
    admin_requested = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tournaments = db.relationship('Tournament', backref='owner', lazy=True)
    players = db.relationship('Player', backref='owner', lazy=True)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

class Player(db.Model):
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False) # e.g. Boys, Girls, Mens, Womens
    age_category = db.Column(db.String(20), nullable=False) # e.g. U8, U10, U12, U14, U18, Open
    total_points = db.Column(db.Float, default=0.0)
    matches_played = db.Column(db.Integer, default=0)
    matches_won = db.Column(db.Integer, default=0)
    matches_lost = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tournament_records = db.relationship('PlayerTournamentRecord', backref='player', lazy=True, cascade='all, delete-orphan')
    participants = db.relationship('Participant', foreign_keys='Participant.player_id', backref='player', lazy=True)

class PlayerTournamentRecord(db.Model):
    __tablename__ = 'player_tournament_records'

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    tournament_name = db.Column(db.String(200), nullable=False)
    level = db.Column(db.String(50), default='Regular') # Regular, State, National
    round_reached = db.Column(db.String(50)) # Round 1, Round 2, QF, SF, Runner-up, Winner
    points_earned = db.Column(db.Float, default=0.0)
    is_manual = db.Column(db.Boolean, default=False)
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action_type = db.Column(db.String(100), nullable=False)
    target_id = db.Column(db.Integer)
    target_name = db.Column(db.String(200))
    reason = db.Column(db.String(100), nullable=False)
    explanation = db.Column(db.Text)
    details = db.Column(db.Text) # JSON diffs or additional metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='audit_logs', lazy=True)
