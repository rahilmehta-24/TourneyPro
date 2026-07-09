from app import create_app, db
from app.models import Tournament, Player, Participant, Match, Category, Group, TournamentSettings, MatchAttachment, PlayerTournamentRecord

app = create_app()

with app.app_context():
    print("Deleting all tables...")
    # Drop all except users? Wait, if we drop all, we lose users.
    # It's better to just delete data from the tables.
    MatchAttachment.query.delete()
    Match.query.delete()
    Participant.query.delete()
    Group.query.delete()
    Category.query.delete()
    TournamentSettings.query.delete()
    Tournament.query.delete()
    PlayerTournamentRecord.query.delete()
    Player.query.delete()
    db.session.commit()
    print("Database cleared. Users were kept.")
