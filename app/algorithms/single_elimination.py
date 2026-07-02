import math

def generate_single_elimination(participants, use_manual_seeding=True):
    """
    Generate single elimination bracket with proper bye distribution.
    
    Args:
        participants: List of Participant objects
        use_manual_seeding: If True, use manual_seed; else auto-assign
    
    Returns:
        List of match dictionaries with round, match_number, participant1_id, participant2_id
    
    Key Features:
    - Ensures bracket size is 2^n
    - Top seeds (lowest seed numbers) get byes
    - Proper seeding distribution (1 vs lowest, 2 vs second-lowest, etc.)
    """
    num_participants = len(participants)

    if num_participants < 2:
        return []

    # Calculate bracket size (next power of 2)
    num_rounds = math.ceil(math.log2(num_participants))
    bracket_size = 2 ** num_rounds
    num_byes = bracket_size - num_participants

    # Sort participants by seed
    if use_manual_seeding:
        # Use manual_seed if available, otherwise use auto seed, otherwise assign based on order
        participants_sorted = sorted(
            participants,
            key=lambda p: p.manual_seed if p.manual_seed else (p.seed if p.seed else 999)
        )
    else:
        participants_sorted = sorted(
            participants,
            key=lambda p: p.seed if p.seed else 999
        )

    # Assign seeds if not already assigned
    for i, p in enumerate(participants_sorted):
        if not p.seed:
            p.seed = i + 1

    # Create seeding slots for bracket (standard tournament seeding)
    # For 8 slots: [1, 8, 4, 5, 2, 7, 3, 6]
    # For 16 slots: [1, 16, 8, 9, 4, 13, 5, 12, 2, 15, 7, 10, 3, 14, 6, 11]
    seeding_order = generate_seeding_order(bracket_size)

    # Create participant slots (None for byes)
    participant_slots = [None] * bracket_size

    # Assign participants to their seeded positions
    # Top seeds get byes when their opponent position doesn't have a participant
    for participant in participants_sorted:
        # Find which slot this participant should be in based on their seed
        seed = participant.manual_seed if participant.manual_seed else participant.seed
        # Find the slot index where this seed appears in the seeding order
        try:
            slot_index = seeding_order.index(seed)
            participant_slots[slot_index] = participant
        except ValueError:
            # Seed number not in seeding order (shouldn't happen with proper setup)
            continue

    # Generate Round 1 matches
    matches = []
    match_number = 1

    for i in range(0, bracket_size, 2):
        p1 = participant_slots[i]
        p2 = participant_slots[i + 1]

        # Only create match if at least one participant exists
        if p1 or p2:
            match = {
                'round': 1,
                'match_number': match_number,
                'participant1_id': p1.id if p1 else None,
                'participant2_id': p2.id if p2 else None,
                'bracket_type': 'main',
                'match_type': 'knockout'
            }
            matches.append(match)
            match_number += 1

    # Generate subsequent rounds (empty matches to be filled as tournament progresses)
    current_round_matches = len(matches)

    for round_num in range(2, num_rounds + 1):
        next_round_matches = current_round_matches // 2

        for match_num in range(next_round_matches):
            match = {
                'round': round_num,
                'match_number': match_num + 1,
                'participant1_id': None,  # Will be filled by winners
                'participant2_id': None,
                'bracket_type': 'main',
                'match_type': 'knockout'
            }
            matches.append(match)

        current_round_matches = next_round_matches

    # Auto-advance players with byes to the next round
    for match in matches:
        if match['round'] == 1:
            # Check if this is a bye match (one participant is None, other is not)
            has_bye = (match['participant1_id'] is None) != (match['participant2_id'] is None)

            if has_bye:
                # Determine bye winner (the player who exists)
                bye_winner_id = match['participant1_id'] if match['participant1_id'] else match['participant2_id']

                # Find the next round match this player should advance to
                next_round = 2
                next_match_number = (match['match_number'] + 1) // 2

                # Find and update the next round match
                for next_match in matches:
                    if next_match['round'] == next_round and next_match['match_number'] == next_match_number:
                        # Determine which slot (participant1 or participant2)
                        if match['match_number'] % 2 == 1:
                            next_match['participant1_id'] = bye_winner_id
                        else:
                            next_match['participant2_id'] = bye_winner_id

                        # Mark current match as completed (Bye)
                        match['winner_id'] = bye_winner_id
                        match['status'] = 'completed'
                        match['score1'] = 'Bye' if match['participant2_id'] is None else ''
                        match['score2'] = 'Bye' if match['participant1_id'] is None else ''
                        break

    return matches


def generate_seeding_order(bracket_size):
    """
    Generate standard tournament seeding order for visual display.
    
    This ensures standard 'bracket' visual layout:
    - Seed 1 sub-bracket is at Top
    - Seed 2 sub-bracket is at Bottom
    - Seed 3 sub-bracket is above Seed 2
    - Seed 4 sub-bracket is below Seed 1
    
    Example (Size 4): [1, 4, 3, 2] -> Matches: (1vs4), (3vs2).
    Example (Size 8): [1, 8, 4, 5, 6, 3, 7, 2] -> Matches: (1vs8), (4vs5), (6vs3), (7vs2).
    """
    if bracket_size == 2:
        return [1, 2]

    # Recursive approach to build seeding
    previous_round = generate_seeding_order(bracket_size // 2)
    seeding = []

    # Split previous round into top and bottom halves
    # For the top half, we expand normally (Seed, Opponent)
    # For the bottom half, we expand inverted (Opponent, Seed) to keep strong seeds at bottom

    half_idx = len(previous_round) // 2
    top_half = previous_round[:half_idx]
    bottom_half = previous_round[half_idx:]

    for seed in top_half:
        seeding.append(seed)
        seeding.append(bracket_size + 1 - seed)

    for seed in bottom_half:
        seeding.append(bracket_size + 1 - seed)
        seeding.append(seed)

    return seeding


def calculate_final_rankings(category):
    """
    Calculate final rankings after tournament completion.
    
    Returns:
        dict with 'winner', 'runner_up', 'semi_finalists' (list of 2)
    """
    from app.models import Match, Participant

    # Find the final match (highest round number)
    final_match = Match.query.filter_by(
        category_id=category.id,
        match_type='knockout'
    ).order_by(Match.round.desc()).first()

    if not final_match or not final_match.winner_id:
        return None

    # Winner is the winner of the final
    winner = Participant.query.get(final_match.winner_id)

    # Runner-up is the loser of the final
    if final_match.participant1_id == final_match.winner_id:
        runner_up_id = final_match.participant2_id
    else:
        runner_up_id = final_match.participant1_id
    runner_up = Participant.query.get(runner_up_id)

    # Semi-finalists are losers of semi-final matches
    semi_final_round = final_match.round - 1
    semi_final_matches = Match.query.filter_by(
        category_id=category.id,
        round=semi_final_round,
        match_type='knockout'
    ).all()

    semi_finalists = []
    for match in semi_final_matches:
        if match.winner_id:
            # Find the loser
            if match.participant1_id == match.winner_id:
                loser_id = match.participant2_id
            else:
                loser_id = match.participant1_id

            if loser_id:
                loser = Participant.query.get(loser_id)
                semi_finalists.append(loser)

    # Update final ranks
    if winner:
        winner.final_rank = 1
    if runner_up:
        runner_up.final_rank = 2
    for i, sf in enumerate(semi_finalists):
        sf.final_rank = 3  # Both semi-finalists get rank 3

    return {
        'winner': winner,
        'runner_up': runner_up,
        'semi_finalists': semi_finalists
    }
