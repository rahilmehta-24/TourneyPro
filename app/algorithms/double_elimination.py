import math

def generate_double_elimination(participants, use_manual_seeding=True):
    """
    Generate double elimination bracket.
    
    Args:
        participants: List of Participant objects
        use_manual_seeding: If True, use manual_seed
    
    Returns:
        List of match dictionaries for both winners and losers brackets
    
    Structure:
    - Winners Bracket: Standard single elimination
    - Losers Bracket: Losers from winners bracket get second chance
    - Grand Finals: Winner of each bracket meets
    """
    from algorithms.single_elimination import generate_single_elimination
    
    # Generate winners bracket (same as single elimination)
    winners_matches = generate_single_elimination(participants, use_manual_seeding)
    
    # Mark all matches as winners bracket
    for match in winners_matches:
        match['bracket_type'] = 'winners'
    
    # Calculate losers bracket structure
    num_participants = len(participants)
    num_rounds_winners = math.ceil(math.log2(num_participants))
    
    # Losers bracket has (2 * num_rounds_winners - 1) rounds
    # Each round in winners bracket feeds into losers bracket
    losers_matches = []
    losers_match_number = 1
    
    # Losers bracket Round 1: First round losers from winners bracket
    num_first_round_losers = len([m for m in winners_matches if m['round'] == 1])
    
    for i in range(0, num_first_round_losers, 2):
        match = {
            'round': 1,
            'match_number': losers_match_number,
            'participant1_id': None,  # Will be filled by losers
            'participant2_id': None,
            'bracket_type': 'losers',
            'match_type': 'knockout'
        }
        losers_matches.append(match)
        losers_match_number += 1
    
    # Subsequent losers bracket rounds alternate between:
    # 1. Losers from winners bracket
    # 2. Winners from previous losers round
    current_losers_round = 2
    current_round_matches = len([m for m in losers_matches if m['round'] == 1])
    
    for winners_round in range(2, num_rounds_winners + 1):
        # Losers from this winners round enter losers bracket
        num_new_losers = len([m for m in winners_matches if m['round'] == winners_round])
        
        # These losers play against winners from previous losers round
        for i in range(num_new_losers):
            match = {
                'round': current_losers_round,
                'match_number': losers_match_number,
                'participant1_id': None,
                'participant2_id': None,
                'bracket_type': 'losers',
                'match_type': 'knockout'
            }
            losers_matches.append(match)
            losers_match_number += 1
        
        current_losers_round += 1
        
        # Next round: winners from previous losers round play each other
        if current_losers_round < (2 * num_rounds_winners):
            num_matches = len([m for m in losers_matches if m['round'] == current_losers_round - 1]) // 2
            for i in range(num_matches):
                match = {
                    'round': current_losers_round,
                    'match_number': losers_match_number,
                    'participant1_id': None,
                    'participant2_id': None,
                    'bracket_type': 'losers',
                    'match_type': 'knockout'
                }
                losers_matches.append(match)
                losers_match_number += 1
            
            current_losers_round += 1
    
    # Grand Finals: Winner of winners bracket vs winner of losers bracket
    grand_finals = {
        'round': num_rounds_winners + 1,
        'match_number': 1,
        'participant1_id': None,  # Winner of winners bracket
        'participant2_id': None,  # Winner of losers bracket
        'bracket_type': 'grand_finals',
        'match_type': 'knockout'
    }
    
    # Combine all matches
    all_matches = winners_matches + losers_matches + [grand_finals]
    
    return all_matches


def calculate_double_elimination_rankings(category):
    """
    Calculate final rankings for double elimination.
    
    Returns:
        dict with 'winner', 'runner_up', 'semi_finalists'
    """
    from app.models import Match, Participant
    
    # Find grand finals
    grand_finals = Match.query.filter_by(
        category_id=category.id,
        bracket_type='grand_finals'
    ).first()
    
    if not grand_finals or not grand_finals.winner_id:
        return None
    
    winner = Participant.query.get(grand_finals.winner_id)
    
    # Runner-up is loser of grand finals
    if grand_finals.participant1_id == grand_finals.winner_id:
        runner_up_id = grand_finals.participant2_id
    else:
        runner_up_id = grand_finals.participant1_id
    runner_up = Participant.query.get(runner_up_id)
    
    # Semi-finalists: loser of winners bracket final and loser of losers bracket final
    winners_final = Match.query.filter_by(
        category_id=category.id,
        bracket_type='winners'
    ).order_by(Match.round.desc()).first()
    
    losers_final = Match.query.filter_by(
        category_id=category.id,
        bracket_type='losers'
    ).order_by(Match.round.desc()).first()
    
    semi_finalists = []
    
    for match in [winners_final, losers_final]:
        if match and match.winner_id:
            if match.participant1_id == match.winner_id:
                loser_id = match.participant2_id
            else:
                loser_id = match.participant1_id
            
            if loser_id:
                loser = Participant.query.get(loser_id)
                if loser and loser.id != runner_up.id:  # Don't duplicate runner-up
                    semi_finalists.append(loser)
    
    # Update ranks
    if winner:
        winner.final_rank = 1
    if runner_up:
        runner_up.final_rank = 2
    for sf in semi_finalists:
        sf.final_rank = 3
    
    return {
        'winner': winner,
        'runner_up': runner_up,
        'semi_finalists': semi_finalists
    }
