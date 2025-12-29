
from app import app, db
from models import Match

def fix_bye_matches():
    with app.app_context():
        # Find all matches where one participant is None but status is not completed
        bye_matches = Match.query.filter(
            ((Match.participant1_id == None) | (Match.participant2_id == None)),
            Match.status != 'completed'
        ).all()
        
        print(f"Found {len(bye_matches)} pending bye matches.")
        
        for match in bye_matches:
            # Determine winner
            winner_id = match.participant1_id if match.participant1_id else match.participant2_id
            
            if winner_id:
                print(f"Fixing match {match.id}: Winner {winner_id}")
                match.winner_id = winner_id
                match.status = 'completed'
                if match.participant2_id is None:
                    match.score1 = 'Bye'
                    match.score2 = 'Bye'
                else:
                    match.score1 = 'Bye'
                    match.score2 = 'Bye'
            else:
                print(f"Skipping match {match.id} (both None?)")
        
        db.session.commit()
        print("Done.")

if __name__ == "__main__":
    fix_bye_matches()
