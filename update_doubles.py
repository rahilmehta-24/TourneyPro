from app import create_app, db
from app.models import PlayerTournamentRecord, Participant, Category, Player

app = create_app()
with app.app_context():
    # Find all doubles categories
    doubles_categories = Category.query.filter_by(format='doubles_elimination', status='completed').all()
    count = 0
    for category in doubles_categories:
        # Get participants in this category
        participants = Participant.query.filter_by(category_id=category.id).all()
        for p in participants:
            if not p.player2_id:
                continue
            
            p1 = Player.query.get(p.player_id)
            p2 = Player.query.get(p.player2_id)
            
            # Find record for p1
            record1 = PlayerTournamentRecord.query.filter_by(
                player_id=p1.id, 
            ).filter(PlayerTournamentRecord.tournament_name.like(f"%{category.name}%")).first()
            
            if record1 and "(Partner:" not in record1.tournament_name:
                record1.tournament_name += f" (Partner: {p2.name})"
                count += 1
                
            # Find record for p2
            record2 = PlayerTournamentRecord.query.filter_by(
                player_id=p2.id,
            ).filter(PlayerTournamentRecord.tournament_name.like(f"%{category.name}%")).first()
            
            if record2 and "(Partner:" not in record2.tournament_name:
                record2.tournament_name += f" (Partner: {p1.name})"
                count += 1
                
    db.session.commit()
    print(f"Updated {count} records.")
