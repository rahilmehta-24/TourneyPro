def generate_round_robin(participants):
    """
    Generate round-robin tournament where everyone plays everyone.
    
    Args:
        participants: List of Participant objects
    
    Returns:
        List of match dictionaries
    """
    matches = []
    match_number = 1
    
    # Generate all possible pairings
    for i in range(len(participants)):
        for j in range(i + 1, len(participants)):
            match = {
                'round': 1,  # All matches are in "round 1" for round robin
                'match_number': match_number,
                'participant1_id': participants[i].id,
                'participant2_id': participants[j].id,
                'bracket_type': 'main',
                'match_type': 'round_robin'
            }
            matches.append(match)
            match_number += 1
    
    return matches


def calculate_round_robin_standings(category_id):
    """
    Calculate standings for round robin based on wins/losses.
    
    Returns:
        List of participants sorted by wins (desc), losses (asc)
    """
    from app.models import Participant, Match, db
    
    participants = Participant.query.filter_by(category_id=category_id).all()
    
    # Calculate wins and losses
    standings = []
    
    for participant in participants:
        wins = Match.query.filter(
            Match.category_id == category_id,
            Match.match_type == 'round_robin',
            Match.winner_id == participant.id,
            Match.status == 'completed'
        ).count()
        
        # Count losses
        losses = Match.query.filter(
            Match.category_id == category_id,
            Match.match_type == 'round_robin',
            Match.status == 'completed',
            db.or_(
                Match.participant1_id == participant.id,
                Match.participant2_id == participant.id
            ),
            Match.winner_id != participant.id
        ).count()
        
        standings.append({
            'participant': participant,
            'wins': wins,
            'losses': losses,
            'points': wins * 3  # 3 points per win
        })
    
    # Sort by wins (desc), then losses (asc)
    standings.sort(key=lambda x: (-x['wins'], x['losses']))
    
    # Update final ranks
    for i, standing in enumerate(standings):
        standing['participant'].final_rank = i + 1
    
    db.session.commit()
    
    return standings
