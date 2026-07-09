from flask_marshmallow import Marshmallow
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields
from .models import Tournament, Category, Match, Participant, User, Player

ma = Marshmallow()

class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        exclude = ("password_hash",)

class PlayerSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Player

class ParticipantSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Participant
        include_fk = True

class MatchSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Match
        include_fk = True
    
    # We can nest participants if needed, but keeping it flat with FKs is often better for lists
    participant1 = fields.Nested(ParticipantSchema, only=("id", "name", "seed"))
    participant2 = fields.Nested(ParticipantSchema, only=("id", "name", "seed"))
    winner = fields.Nested(ParticipantSchema, only=("id", "name"))

class CategorySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Category
        include_fk = True
        
    matches = fields.List(fields.Nested(MatchSchema(only=("id", "round", "match_number", "status", "scheduled_time", "score1", "score2", "participant1_id", "participant2_id", "winner_id"))))
    participants = fields.List(fields.Nested(ParticipantSchema(only=("id", "name", "seed", "final_rank"))))

class TournamentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Tournament
        include_fk = True
        
    categories = fields.List(fields.Nested(CategorySchema(only=("id", "name", "format", "status", "num_sets", "games_per_set"))))

user_schema = UserSchema()
users_schema = UserSchema(many=True)

tournament_schema = TournamentSchema()
tournaments_schema = TournamentSchema(many=True)

category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)

match_schema = MatchSchema()
matches_schema = MatchSchema(many=True)

participant_schema = ParticipantSchema()
participants_schema = ParticipantSchema(many=True)
