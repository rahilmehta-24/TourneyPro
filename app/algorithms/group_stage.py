from app.models import db, Match, Participant, Group

def generate_group_stage(category, participants):
    """
    Generate group stage with round-robin within groups.
    
    Args:
        category: Category object with group stage configuration
        participants: List of Participant objects
    
    Returns:
        List of match dictionaries for group stage
    """
    num_groups = category.num_groups
    teams_per_group = category.teams_per_group
    matches_per_pair = category.matches_per_team_pair or 1

    # Create groups
    groups = []
    for i in range(num_groups):
        group = Group(
            category_id=category.id,
            name=f"Group {chr(65 + i)}"  # Group A, Group B, etc.
        )
        db.session.add(group)
        db.session.flush()
        groups.append(group)

    # Assign participants to groups (snake draft style for fairness)
    participants_sorted = sorted(participants, key=lambda p: p.manual_seed or p.seed or 999)

    for i, participant in enumerate(participants_sorted):
        round_num = i // num_groups
        if round_num % 2 == 0:
            group_index = i % num_groups
        else:
            group_index = (num_groups - 1) - (i % num_groups)
        participant.group_id = groups[group_index].id

    db.session.commit()

    # Generate round-robin matches within each group
    matches = []
    match_number = 1

    for group in groups:
        group_participants = [p for p in participants if p.group_id == group.id]

        # Generate all possible pairings
        for i in range(len(group_participants)):
            for j in range(i + 1, len(group_participants)):
                p1 = group_participants[i]
                p2 = group_participants[j]

                # Create multiple matches if configured
                for match_iteration in range(matches_per_pair):
                    match = {
                        'category_id': category.id,
                        'group_id': group.id,
                        'round': match_iteration + 1,  # Round 1, 2, 3 for multiple matches
                        'match_number': match_number,
                        'participant1_id': p1.id,
                        'participant2_id': p2.id,
                        'match_type': 'group_stage'
                    }
                    matches.append(match)
                    match_number += 1

    return matches


def calculate_group_standings(group_id):
    """
    Calculate standings for a group based on match results.
    
    Returns:
        List of participants sorted by: wins (desc), then losses (asc)
    """
    participants = Participant.query.filter_by(group_id=group_id).all()

    # Reset stats
    for p in participants:
        p.group_wins = 0
        p.group_losses = 0
        p.group_points = 0

    # Calculate wins/losses from matches
    matches = Match.query.filter_by(group_id=group_id, match_type='group_stage').all()

    for match in matches:
        if match.status == 'completed' and match.winner_id:
            winner = next((p for p in participants if p.id == match.winner_id), None)

            # Determine loser
            if match.participant1_id == match.winner_id:
                loser_id = match.participant2_id
            else:
                loser_id = match.participant1_id

            loser = next((p for p in participants if p.id == loser_id), None)

            if winner:
                winner.group_wins += 1
                winner.group_points += 3  # 3 points for a win

            if loser:
                loser.group_losses += 1

    db.session.commit()

    # Sort by points (desc), then wins (desc), then losses (asc)
    standings = sorted(
        participants,
        key=lambda p: (-p.group_points, -p.group_wins, p.group_losses)
    )

    return standings


def get_qualified_participants(category):
    """
    Get participants who qualified from group stage to knockout.
    
    Returns:
        List of qualified participants, seeded by group performance
    """
    qualifiers_per_group = category.qualifiers_per_group or 2
    groups = Group.query.filter_by(category_id=category.id).all()

    qualified = []

    for group in groups:
        standings = calculate_group_standings(group.id)
        # Take top N from each group
        group_qualifiers = standings[:qualifiers_per_group]
        qualified.extend(group_qualifiers)

    # Seed qualified participants based on group performance
    # Group winners get better seeds than group runners-up
    for i, participant in enumerate(qualified):
        participant.seed = i + 1

    db.session.commit()

    return qualified


def generate_knockout_from_groups(category):
    """
    Generate knockout bracket from group stage qualifiers.
    
    Returns:
        List of knockout matches
    """
    from algorithms.single_elimination import generate_single_elimination

    qualified = get_qualified_participants(category)

    # Generate single elimination bracket with qualified participants
    matches = generate_single_elimination(qualified, use_manual_seeding=False)

    # Update matches to belong to this category
    for match in matches:
        match['category_id'] = category.id

    return matches
