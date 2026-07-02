from app.models import db, Player, PlayerTournamentRecord, Match, Participant

def assign_leaderboard_points(category):
    # Find all participants with a player_id
    participants = Participant.query.filter_by(category_id=category.id).filter(Participant.player_id.isnot(None)).all()

    for participant in participants:
        player = Player.query.get(participant.player_id)
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
            points = 500
            round_reached = 'Winner'
        elif rank == 2:
            points = 300
            round_reached = 'Runner-Up'
        elif rank in [3, 4]:
            points = 160
            round_reached = 'Semi-Final'
        elif rank and rank <= 8:
            points = 80
            round_reached = 'Quarter-Final'
        elif rank and rank <= 16:
            points = 40
            round_reached = 'Round 4'
        elif rank and rank <= 32:
            points = 20
            round_reached = 'Round 3'
        elif rank and rank <= 64:
            points = 10
            round_reached = 'Round 2'
        else:
            points = 5
            round_reached = 'Round 1'

        record = PlayerTournamentRecord(
            player_id=player.id,
            tournament_name=category.tournament.name + ' - ' + category.name,
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
        if participant and participant.player_id:
            player = Player.query.get(participant.player_id)
            if player:
                player.matches_played += 1
                if participant.id == match.winner_id:
                    player.matches_won += 1
                    player.total_points += 10  # Live match win points
                else:
                    player.matches_lost += 1
                    
                db.session.add(player)
    
    db.session.commit()
