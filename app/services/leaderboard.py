from app.models import db, Player, PlayerTournamentRecord, Match, Participant

def assign_leaderboard_points(category):
    # Find all participants with a player_id
    participants = Participant.query.filter_by(category_id=category.id).filter(Participant.player_id.isnot(None)).all()

    for participant in participants:
        player_ids = [participant.player_id]
        if participant.player2_id:
            player_ids.append(participant.player2_id)
            
        for p_id in player_ids:
            player = Player.query.get(p_id)
            if not player:
                continue

            # Get all matches for this participant in this category
            matches = Match.query.filter(
                (Match.category_id == category.id) &
                ((Match.participant1_id == participant.id) | (Match.participant2_id == participant.id)) &
                (Match.status == 'completed')
            ).all()

            matches_won = sum(1 for m in matches if m.winner_id == participant.id)
            matches_lost = len(matches) - matches_won

            rank = participant.final_rank
            points = 0
            round_reached = 'Participant'

            if rank == 1:
                points = 650
                round_reached = 'Winner'
            elif rank == 2:
                points = 400
                round_reached = 'Runner-Up'
            elif rank in [3, 4]:
                points = 250
                round_reached = 'Semi-Final'
            elif rank and rank <= 8:
                points = 160
                round_reached = 'Quarter-Final'
            elif rank and rank <= 16:
                points = 100
                round_reached = 'Round 4'
            elif rank and rank <= 32:
                points = 60
                round_reached = 'Round 3'
            elif rank and rank <= 64:
                points = 30
                round_reached = 'Round 2'
            else:
                points = 10
                round_reached = 'Round 1'

            tournament_display_name = category.tournament.name + ' - ' + category.name
            
            if category.format == 'doubles_elimination' and participant.player2_id:
                partner_id = participant.player2_id if p_id == participant.player_id else participant.player_id
                partner = Player.query.get(partner_id)
                if partner:
                    tournament_display_name += f" (Partner: {partner.name})"

            record = PlayerTournamentRecord(
                player_id=player.id,
                tournament_name=tournament_display_name,
                level='Regular',
                round_reached=round_reached,
                points_earned=points,
                is_manual=False
            )

            player.total_points += points
            # Live stats now handle matches_won/lost/played dynamically

            db.session.add(record)

    db.session.commit()

def update_live_player_stats(match):
    """
    Called when a match completes to instantly update the global player's 
    matches won/lost stats and award points for the win.
    """
    for participant_id in [match.participant1_id, match.participant2_id]:
        if not participant_id:
            continue
            
        participant = Participant.query.get(participant_id)
        if participant:
            player_ids = []
            if participant.player_id:
                player_ids.append(participant.player_id)
            if participant.player2_id:
                player_ids.append(participant.player2_id)
                
            for p_id in player_ids:
                player = Player.query.get(p_id)
                if player:
                    player.matches_played += 1
                    if participant.id == match.winner_id:
                        player.matches_won += 1
                    else:
                        player.matches_lost += 1
                        
                    db.session.add(player)
    
    db.session.commit()

def calculate_combined_round_robin_standings(category_id):
    """
    For Round Robin categories that do NOT have a knockout stage,
    the final rankings are determined by taking all participants from all groups,
    and sorting them by their total group_points, group_wins, and manual_seed.
    This sets final_rank on the Participant objects.
    """
    participants = Participant.query.filter_by(category_id=category_id).all()
    
    # Sort participants by points (desc), wins (desc), and seed (asc for priority)
    sorted_participants = sorted(
        participants,
        key=lambda p: (
            p.group_points or 0,
            p.group_wins or 0,
            -(p.manual_seed or 9999)
        ),
        reverse=True
    )
    
    for i, p in enumerate(sorted_participants):
        p.final_rank = i + 1
    
    db.session.commit()
    return sorted_participants

def recalculate_all_group_stats(category_id):
    """
    Recalculates group_wins, group_losses, and group_points for all participants in a category
    by tallying up all completed group_stage and round_robin matches.
    If match scores are numeric (e.g. 11, 5), they are added to group_points.
    Otherwise (e.g. tennis sets), winner gets 3 points.
    """
    participants = Participant.query.filter_by(category_id=category_id).all()
    
    # Reset stats
    for p in participants:
        p.group_wins = 0
        p.group_losses = 0
        p.group_points = 0
        
    matches = Match.query.filter(
        Match.category_id == category_id,
        Match.match_type.in_(['group_stage', 'round_robin']),
        Match.status == 'completed'
    ).all()
    
    for match in matches:
        if not match.winner_id:
            continue
            
        p1 = next((p for p in participants if p.id == match.participant1_id), None)
        p2 = next((p for p in participants if p.id == match.participant2_id), None)
        
        if not p1 or not p2:
            continue
            
        winner = p1 if match.winner_id == p1.id else p2
        loser = p2 if match.winner_id == p1.id else p1
        
        winner.group_wins += 1
        loser.group_losses += 1
        
        # Try to parse scores as integers to accumulate points
        try:
            s1 = int(match.score1) if match.score1 is not None else 0
            s2 = int(match.score2) if match.score2 is not None else 0
            
            if winner.id == p1.id:
                winner.group_points += s1
                loser.group_points += s2
            else:
                winner.group_points += s2
                loser.group_points += s1
        except (ValueError, TypeError):
            # Fallback for standard tennis sets: 3 points for win
            winner.group_points += 3

    db.session.commit()
