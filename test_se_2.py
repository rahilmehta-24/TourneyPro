from app import create_app
from app.models import db, Category, Participant, Match
from app.leaderboard_logic import update_live_player_stats

app = create_app()
with app.app_context():
    cat = Category.query.filter_by(format='single_elimination').first()
    parts = Participant.query.filter_by(category_id=cat.id).all()
    if len(parts) >= 2:
        p1, p2 = parts[0], parts[1]
        
        match = Match(
            category_id=cat.id,
            tournament_id=cat.tournament_id,
            round=1,
            match_number=1,
            participant1_id=p1.id,
            participant2_id=p2.id,
            bracket_type='main',
            match_type='knockout',
            score1="6-4, 6-4",
            score2="4-6, 4-6",
            winner_id=p1.id,
            status='completed'
        )
        db.session.add(match)
        db.session.commit()
        
        try:
            update_live_player_stats(match)
            print("update_live_player_stats successful!")
        except Exception as e:
            print("Error in update_live_player_stats:", e)
            import traceback
            traceback.print_exc()

