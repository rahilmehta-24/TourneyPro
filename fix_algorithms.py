
# Fix group_stage.py
with open('app/algorithms/group_stage.py', 'r') as f:
    gs_content = f.read()

old_gs = """            if winner:
                winner.group_wins += 1
                winner.group_points += 3  # 3 points for a win

            if loser:
                loser.group_losses += 1"""

new_gs = """            if winner:
                winner.group_wins += 1
                try:
                    s1 = int(match.score1) if match.score1 is not None else 0
                    s2 = int(match.score2) if match.score2 is not None else 0
                    winner.group_points += s1 if match.participant1_id == winner.id else s2
                except (ValueError, TypeError):
                    winner.group_points += 3  # 3 points for a win

            if loser:
                loser.group_losses += 1
                try:
                    s1 = int(match.score1) if match.score1 is not None else 0
                    s2 = int(match.score2) if match.score2 is not None else 0
                    loser.group_points += s2 if match.participant1_id == winner.id else s1
                except (ValueError, TypeError):
                    pass"""

gs_content = gs_content.replace(old_gs, new_gs)

with open('app/algorithms/group_stage.py', 'w') as f:
    f.write(gs_content)

# Fix round_robin.py
with open('app/algorithms/round_robin.py', 'r') as f:
    rr_content = f.read()

old_rr = """    for participant in participants:
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
        })"""

new_rr = """    for participant in participants:
        matches = Match.query.filter(
            Match.category_id == category_id,
            Match.match_type == 'round_robin',
            Match.status == 'completed',
            db.or_(
                Match.participant1_id == participant.id,
                Match.participant2_id == participant.id
            )
        ).all()
        
        wins = sum(1 for m in matches if m.winner_id == participant.id)
        losses = sum(1 for m in matches if m.winner_id and m.winner_id != participant.id)
        
        points = 0
        for m in matches:
            if not m.winner_id:
                continue
            is_p1 = m.participant1_id == participant.id
            try:
                s1 = int(m.score1) if m.score1 is not None else 0
                s2 = int(m.score2) if m.score2 is not None else 0
                points += s1 if is_p1 else s2
            except (ValueError, TypeError):
                if m.winner_id == participant.id:
                    points += 3
        
        participant.group_wins = wins
        participant.group_losses = losses
        participant.group_points = points

        standings.append({
            'participant': participant,
            'wins': wins,
            'losses': losses,
            'points': points
        })"""

rr_content = rr_content.replace(old_rr, new_rr)

with open('app/algorithms/round_robin.py', 'w') as f:
    f.write(rr_content)

