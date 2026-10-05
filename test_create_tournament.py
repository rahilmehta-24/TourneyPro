from app import create_app, db
from app.domain.models import Tournament, TournamentSettings, User

app = create_app()
with app.app_context():
    user = User.query.first()
    try:
        t = Tournament(
            user_id=user.id if user else None,
            name="Test",
            url_slug="test-123",
            has_categories=True,
            is_internal=False
        )
        db.session.add(t)
        db.session.commit()
        
        settings = TournamentSettings(tournament_id=t.id)
        db.session.add(settings)
        db.session.commit()
        print("Success")
    except Exception as e:
        db.session.rollback()
        print(f"Exception: {e}")
