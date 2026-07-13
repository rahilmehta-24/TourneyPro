from app.utils.audit import log_audit
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import db, Tournament, Participant, Match, TournamentSettings
from app.formats import get_format
from app.constants import TOURNAMENT_FORMATS
from app.routes.auth import login_required, role_required, get_current_user, check_tournament_ownership
from app.tennis_logic import validate_and_format_score
from slugify import slugify
from datetime import datetime

tournament_bp = Blueprint('tournament', __name__)

@tournament_bp.route('/tournaments/new', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def create_tournament():
    """Create new tournament"""
    if request.method == 'POST':
        name = request.form.get('name')
        creator_name = request.form.get('creator_name', 'Anonymous')
        description = request.form.get('description', '')
        game_info = request.form.get('game_info', '')
        # Set legacy values for backwards compatibility, but do not prompt for them
        format_type = None
        max_participants = None
        num_sets = 1
        games_per_set = 6

        # Generate URL slug
        url_slug = slugify(name)

        # Check if slug already exists
        existing = Tournament.query.filter_by(url_slug=url_slug).first()
        if existing:
            url_slug = f"{url_slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create tournament
        tournament = Tournament(
            user_id=get_current_user().id,
            creator_name=creator_name,
            name=name,
            url_slug=url_slug,
            description=description,
            game_info=game_info,
            format=format_type,
            max_participants=max_participants,
            num_sets=num_sets,
            games_per_set=games_per_set,
            has_categories=True  # Force categories for all new tournaments
        )

        try:
            db.session.add(tournament)
            db.session.commit()

            # Create default settings
            settings = TournamentSettings(tournament_id=tournament.id)
            db.session.add(settings)
            db.session.commit()

            flash('Tournament created successfully!', 'success')
            return redirect(url_for('tournament.manage_tournament', slug=tournament.url_slug))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create tournament: {str(e)}', 'error')
            return redirect(url_for('main.index'))

    return render_template('tournament/create.html', formats=TOURNAMENT_FORMATS)

@tournament_bp.route('/tournaments/<slug>')
def view_tournament(slug):
    """View tournament bracket"""
    tournament = Tournament.query.options(db.joinedload(Tournament.categories)).filter_by(url_slug=slug).first_or_404()
    participants = Participant.query.filter_by(tournament_id=tournament.id).order_by(Participant.seed).all()
    matches = Match.query.options(
        db.joinedload(Match.participant1),
        db.joinedload(Match.participant2),
        db.joinedload(Match.winner),
        db.joinedload(Match.category)
    ).filter_by(tournament_id=tournament.id).order_by(Match.round, Match.match_number).all()

    # Group matches by round
    rounds = {}
    winners_rounds = {}
    losers_rounds = {}
    grand_finals = []
    for match in matches:
        if match.round not in rounds:
            rounds[match.round] = []
        rounds[match.round].append(match)

        # Double elimination separation
        if match.bracket_type == 'winners':
            if match.round not in winners_rounds:
                winners_rounds[match.round] = []
            winners_rounds[match.round].append(match)
        elif match.bracket_type == 'losers':
            if match.round not in losers_rounds:
                losers_rounds[match.round] = []
            losers_rounds[match.round].append(match)
        elif match.bracket_type in ['grand_finals', 'grand_final']:
            grand_finals.append(match)

    # Aggregate player registry data efficiently
    player_stats = {}
    if tournament.has_categories:
        # Pre-build stats dictionary from participants
        for category in tournament.categories:
            for participant in category.participants:
                if participant.name not in player_stats:
                    player_stats[participant.name] = {
                        'name': participant.name,
                        'categories': [],
                        'total_matches': 0,
                        'total_wins': 0,
                        'placements': []
                    }
                player_stats[participant.name]['categories'].append(category.name)

        # Iterate over pre-loaded matches once to count matches and wins
        for match in matches:
            if match.status == 'completed' and match.category_id:
                p1_name = match.participant1.name if match.participant1 else None
                p2_name = match.participant2.name if match.participant2 else None
                winner_name = match.winner.name if match.winner else None

                if p1_name and p1_name in player_stats:
                    player_stats[p1_name]['total_matches'] += 1
                if p2_name and p2_name in player_stats:
                    player_stats[p2_name]['total_matches'] += 1
                if winner_name and winner_name in player_stats:
                    player_stats[winner_name]['total_wins'] += 1

        # Calculate placements
        for category in tournament.categories:
            if category.status == 'completed':
                cat_matches = [m for m in matches if m.category_id == category.id and m.match_type != 'round_robin']
                if cat_matches:
                    max_round = max([m.round for m in cat_matches], default=0)
                    finals = [m for m in cat_matches if m.round == max_round]
                    semis = [m for m in cat_matches if m.round == max_round - 1] if max_round >= 2 else []

                    for participant in category.participants:
                        p_name = participant.name
                        if p_name in player_stats:
                            if finals and finals[0].winner_id == participant.id:
                                player_stats[p_name]['placements'].append(('Champion', category.name))
                            elif finals and participant.id in [finals[0].participant1_id, finals[0].participant2_id]:
                                player_stats[p_name]['placements'].append(('Runner-Up', category.name))
                            else:
                                for sm in semis:
                                    if participant.id in [sm.participant1_id, sm.participant2_id] and sm.winner_id != participant.id:
                                        player_stats[p_name]['placements'].append(('Semi-Finalist', category.name))
                                        break

    # Sort registry by wins
    player_registry = sorted(player_stats.values(), key=lambda x: x['total_wins'], reverse=True)

    # Sort placements for each player to find the "best" one
    placement_weights = {
        'Champion': 3,
        'Runner-Up': 2,
        'Semi-Finalist': 1
    }

    for player in player_registry:
        if player['placements']:
            player['placements'].sort(key=lambda x: placement_weights.get(x[0], 0), reverse=True)

    return render_template('tournament/view.html',
                         tournament=tournament,
                         participants=participants,
                         matches=matches,
                         rounds=rounds,
                         winners_rounds=winners_rounds,
                         losers_rounds=losers_rounds,
                         grand_finals=grand_finals,
                         player_registry=player_registry,
                         formats=TOURNAMENT_FORMATS)

@tournament_bp.route('/tournaments/<slug>/manage', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def manage_tournament(slug):
    """Manage tournament (add participants, start tournament)"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    
    participants = Participant.query.filter_by(tournament_id=tournament.id).order_by(Participant.seed).all()

    if request.method == 'POST':
        action = request.form.get('action')

        try:
            if action == 'add_participant':
                participant_name = request.form.get('participant_name')
                participant_email = request.form.get('participant_email', '')
                
                # Handle comma-separated names
                names = [n.strip() for n in participant_name.split(',') if n.strip()]
                
                from app.models import Player
                added_names = []
                
                for name in names:
                    player_match = Player.query.filter_by(name=name).first()
                    player_id = player_match.id if player_match else None
                    
                    participant = Participant(
                        tournament_id=tournament.id,
                        player_id=player_id,
                        name=name,
                        email=participant_email if len(names) == 1 else ''
                    )
                    db.session.add(participant)
                    added_names.append(name)
                    
                db.session.commit()

                flash(f'Added participants: {", ".join(added_names)}', 'success')
                return redirect(url_for('tournament.manage_tournament', slug=slug))

            elif action == 'delete_participant':
                participant_id = request.form.get('participant_id', type=int)
                participant = Participant.query.get(participant_id)
                if participant:
                    reason = request.form.get('audit_reason')
                    explanation = request.form.get('audit_explanation', '')
                    if not reason:
                        flash("Audit validation failed: Reason required to delete a participant.", "error")
                        return redirect(url_for('tournament.manage_tournament', slug=slug))
                        
                    log_audit(
                        action_type='delete_participant',
                        target_id=participant.id,
                        target_name=participant.name,
                        reason=reason,
                        explanation=explanation
                    )
                    db.session.delete(participant)
                    db.session.commit()
                    flash(f'Removed participant: {participant.name}', 'info')
                return redirect(url_for('tournament.manage_tournament', slug=slug))

            elif action == 'start_tournament':
                if tournament.has_categories:
                    tournament.status = 'in_progress'
                    tournament.started_at = datetime.utcnow()
                    db.session.commit()
                    flash('Tournament started! You can now start individual category brackets.', 'success')
                    return redirect(url_for('tournament.view_tournament', slug=slug))
                else:
                    # Legacy tournament without categories
                    if tournament.format == 'single_elimination':
                        fmt = get_format(tournament.format)
                        if fmt:
                            matches_data = fmt.generate(tournament, participants)
                        else:
                            matches_data = []

                        # Create match records
                        for match_data in matches_data:
                            match = Match(**match_data, tournament_id=tournament.id)
                            db.session.add(match)

                        tournament.status = 'in_progress'
                        tournament.started_at = datetime.utcnow()
                        db.session.commit()

                        flash('Tournament started! Bracket generated.', 'success')
                        return redirect(url_for('tournament.view_tournament', slug=slug))
                    else:
                        flash(f'Format "{tournament.format}" is not yet implemented. Coming soon!', 'warning')

            elif action == 'reset_tournament':
                if tournament.status in ['in_progress', 'completed']:
                    reason = request.form.get('audit_reason')
                    explanation = request.form.get('audit_explanation', '')
                    if not reason:
                        flash("Audit validation failed: Reason required to reset a tournament.", "error")
                        return redirect(url_for('tournament.manage_tournament', slug=slug))
                    if len(explanation.strip()) < 20:
                        flash("Audit validation failed: A detailed explanation (minimum 20 characters) is required for high-risk actions.", "error")
                        return redirect(url_for('tournament.manage_tournament', slug=slug))
                        
                    log_audit(
                        action_type='reset_tournament',
                        target_id=tournament.id,
                        target_name=f"Tournament Bracket: {tournament.name}",
                        reason=reason,
                        explanation=explanation
                    )
                    
                    # Delete matches
                    Match.query.filter_by(tournament_id=tournament.id).delete()

                    # Reset participants stats
                    for p in participants:
                        p.final_rank = None

                    tournament.status = 'setup'
                    tournament.started_at = None
                    tournament.completed_at = None

                    db.session.commit()
                    flash('Tournament bracket stopped and reset! You can now edit settings and add/remove players.', 'success')
                    return redirect(url_for('tournament.manage_tournament', slug=slug))
                else:
                    flash('Tournament is already in setup status.', 'warning')
                    return redirect(url_for('tournament.manage_tournament', slug=slug))

            elif action == 'finish_tournament':
                tournament.status = 'completed'
                tournament.completed_at = datetime.utcnow()
                db.session.commit()

                flash('Tournament completed! 🏆', 'success')
                return redirect(url_for('tournament.view_tournament', slug=slug))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to perform action: {str(e)}', 'error')
            return redirect(url_for('tournament.manage_tournament', slug=slug))


    # Calculate total unique players
    if tournament.has_categories:
        unique_players = set()
        for category in tournament.categories:
            for participant in category.participants:
                unique_players.add(participant.name)
        total_players = len(unique_players)
    else:
        # For non-category tournaments, participants are directly under the tournament
        total_players = len(participants)

    return render_template('tournament/manage.html',
                         tournament=tournament,
                         participants=participants,
                         total_players=total_players,
                         formats=TOURNAMENT_FORMATS)

@tournament_bp.route('/tournaments/<slug>/match/<int:match_id>/report', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def report_match_result(slug, match_id):
    """Report match result"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    
    match = Match.query.get_or_404(match_id)

    action = request.form.get('action')
    is_live_update = (action == 'live_score')
    winner_id = request.form.get('winner_id', type=int) if not is_live_update else None

    # Extract set scores from request
    form_data = {
        'set1_p1': request.form.get('set1_p1', ''),
        'set1_p2': request.form.get('set1_p2', ''),
        'tb1_p1': request.form.get('tb1_p1', ''),
        'tb1_p2': request.form.get('tb1_p2', ''),
        'set2_p1': request.form.get('set2_p1', ''),
        'set2_p2': request.form.get('set2_p2', ''),
        'tb2_p1': request.form.get('tb2_p1', ''),
        'tb2_p2': request.form.get('tb2_p2', ''),
        'set3_p1': request.form.get('set3_p1', ''),
        'set3_p2': request.form.get('set3_p2', ''),
        'tb3_p1': request.form.get('tb3_p1', ''),
        'tb3_p2': request.form.get('tb3_p2', ''),
        'set4_p1': request.form.get('set4_p1', ''),
        'set4_p2': request.form.get('set4_p2', ''),
        'tb4_p1': request.form.get('tb4_p1', ''),
        'tb4_p2': request.form.get('tb4_p2', ''),
        'set5_p1': request.form.get('set5_p1', ''),
        'set5_p2': request.form.get('set5_p2', ''),
        'tb5_p1': request.form.get('tb5_p1', ''),
        'tb5_p2': request.form.get('tb5_p2', ''),
    }

    try:
        # Process overrides
        scoring_format_override = request.form.get('scoring_format')
        if scoring_format_override:
            match.scoring_format = scoring_format_override
            
        num_sets_override = request.form.get('num_sets', type=int)
        if num_sets_override:
            match.num_sets = num_sets_override
            
        games_per_set_override = request.form.get('games_per_set', type=int)
        if games_per_set_override:
            match.games_per_set = games_per_set_override
            
        points_to_win_override = request.form.get('points_to_win', type=int)
        if points_to_win_override:
            match.points_to_win = points_to_win_override
            
        if match.category_id:
            category = Category.query.get(match.category_id)
            
            scoring_format = match.scoring_format or (category.scoring_format if category else 'games')
            
            if category and category.format == 'group_stage':
                # New scoring system based on total games
                total_games_target = category.total_games
                g1_val = form_data.get('set1_p1')
                g2_val = form_data.get('set1_p2')
                
                if not g1_val or not g2_val:
                    raise ValueError("Score is required.")
                
                try:
                    g1 = int(g1_val)
                    g2 = int(g2_val)
                except ValueError:
                    raise ValueError("Score must be integers.")
                    
                if not is_live_update:
                    if g1 + g2 != total_games_target:
                        raise ValueError(f"Total games must sum to {total_games_target}. You entered {g1} and {g2} (sum: {g1+g2}).")
                        
                    actual_winner = match.participant1_id if g1 > g2 else match.participant2_id
                    if winner_id != actual_winner:
                        raise ValueError("Selected winner does not match the scores.")
                    
                match.score1 = str(g1)
                match.score2 = str(g2)
                
            elif scoring_format == 'points' or (category and category.format in ['round_robin', 'doubles_round_robin']):
                points_to_win = match.points_to_win or (category.points_to_win if category else 11)
                if scoring_format == 'points':
                    g1_val = request.form.get('points_p1')
                    g2_val = request.form.get('points_p2')
                else:
                    g1_val = form_data.get('set1_p1')
                    g2_val = form_data.get('set1_p2')
                
                if not g1_val or not g2_val:
                    raise ValueError("Score is required.")
                
                try:
                    g1 = int(g1_val)
                    g2 = int(g2_val)
                except ValueError:
                    raise ValueError("Score must be integers.")
                    
                if not is_live_update:
                    winning_score = max(g1, g2)
                    losing_score = min(g1, g2)
                    
                    if winning_score < points_to_win:
                        raise ValueError(f"One player must reach {points_to_win} points to win.")
                        
                    diff = winning_score - losing_score
                    if diff < 2:
                        raise ValueError("A player must win by a difference of at least 2 points.")
                        
                    if winning_score > points_to_win and diff > 2:
                        raise ValueError(f"Invalid score. When extending past {points_to_win} points, the match ends as soon as a 2-point difference is reached.")
                        
                    actual_winner = match.participant1_id if g1 > g2 else match.participant2_id
                    if winner_id != actual_winner:
                        raise ValueError("Selected winner does not match the scores.")
                    
                match.score1 = str(g1)
                match.score2 = str(g2)
                
            else:
                # Legacy set scoring
                num_sets = match.num_sets or (category.num_sets if category and category.num_sets else (tournament.num_sets or 3))
                games_per_set = match.games_per_set or (category.games_per_set if category and category.games_per_set else (tournament.games_per_set or 6))

                score1, score2 = validate_and_format_score(
                    winner_id, match.participant1_id, match.participant2_id,
                    num_sets, games_per_set, form_data, is_live_update=is_live_update
                )

                match.score1 = score1
                match.score2 = score2
        else:
            # Fallback for tournaments without categories
            num_sets = tournament.num_sets or 3
            games_per_set = tournament.games_per_set or 6

            score1, score2 = validate_and_format_score(
                winner_id, match.participant1_id, match.participant2_id,
                num_sets, games_per_set, form_data, is_live_update=is_live_update
            )

            match.score1 = score1
            match.score2 = score2

        if is_live_update:
            match.status = 'in_progress'
            db.session.commit()
            flash('Live score updated successfully.', 'success')
            return redirect(url_for('tournament.view_tournament', slug=slug))

        match.winner_id = winner_id
        match.status = 'completed'
        match.completed_at = datetime.utcnow()
        db.session.commit()

        from app.leaderboard_logic import update_live_player_stats
        update_live_player_stats(match)

        # Update next round match
        if tournament.format == 'single_elimination':
            # Find next round match
            next_round = match.round + 1
            next_match_number = (match.match_number + 1) // 2

            next_match = Match.query.filter_by(
                tournament_id=tournament.id,
                round=next_round,
                match_number=next_match_number
            ).first()

            if next_match:
                # Determine which slot to fill (participant1 or participant2)
                if match.match_number % 2 == 1:
                    next_match.participant1_id = winner_id
                else:
                    next_match.participant2_id = winner_id

        db.session.commit()
        
            
        flash('Match result reported successfully!', 'success')
    except ValueError as ve:
        db.session.rollback()
        flash(f'Invalid Tennis Score: {str(ve)}', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to report match result: {str(e)}', 'error')

    return redirect(url_for('tournament.view_tournament', slug=slug))

@tournament_bp.route('/match/<int:match_id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def toggle_match_status(match_id):
    """Toggle match status between pending and in_progress"""
    match = Match.query.get_or_404(match_id)
    if match.tournament:
        check_tournament_ownership(match.tournament)
    
    if match.status == 'completed':
        return jsonify({'success': False, 'message': 'Cannot toggle a completed match.'}), 400
        
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in ['pending', 'in_progress']:
        return jsonify({'success': False, 'message': 'Invalid status.'}), 400
        
    match.status = new_status
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'status': match.status})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@tournament_bp.route('/match/<int:match_id>/schedule', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def schedule_match(match_id):
    """Set the scheduled time for a match"""
    match = Match.query.get_or_404(match_id)
    if match.tournament:
        check_tournament_ownership(match.tournament)
    
    if match.status == 'completed':
        return jsonify({'success': False, 'message': 'Cannot schedule a completed match.'}), 400
        
    data = request.get_json()
    scheduled_time_str = data.get('scheduled_time')
    
    if scheduled_time_str:
        try:
            # First try parsing the custom format they type in
            match.scheduled_time = datetime.strptime(scheduled_time_str, '%d/%m/%Y %H:%M %p')
        except ValueError:
            try:
                # Fall back to standard ISO string from datetime-local
                match.scheduled_time = datetime.fromisoformat(scheduled_time_str)
            except Exception as e:
                return jsonify({'success': False, 'message': f'Invalid datetime format: {str(e)}'}), 400
    else:
        match.scheduled_time = None
        
    try:
        db.session.commit()
        return jsonify({
            'success': True, 
            'scheduled_time': match.scheduled_time.isoformat() if match.scheduled_time else None
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@tournament_bp.route('/tournaments/<slug>/seeding', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def manage_tournament_seeding(slug):
    """Manage manual seeding for tournament participants"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    
    participants = Participant.query.filter_by(tournament_id=tournament.id).all()

    if request.method == 'POST':
        try:
            # Update seeds from form
            for participant in participants:
                seed_key = f'seed_{participant.id}'
                if seed_key in request.form:
                    new_seed = request.form.get(seed_key, type=int)
                    participant.manual_seed = new_seed

            db.session.commit()
            flash('Seeding updated successfully!', 'success')
            return redirect(url_for('tournament.manage_tournament', slug=slug))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update seeding: {str(e)}', 'error')
            return redirect(url_for('tournament.manage_tournament', slug=slug))

    return render_template('tournament/seeding.html',
                         tournament=tournament,
                         participants=participants)

@tournament_bp.route('/tournaments/<slug>/delete', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def delete_tournament(slug):
    """Delete tournament"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    
    # Audit Validation
    reason = request.form.get('audit_reason')
    explanation = request.form.get('audit_explanation', '')
    if not reason:
        flash("Audit validation failed: Reason required to delete a tournament.", "error")
        return redirect(url_for('tournament.manage_tournament', slug=slug))
    if len(explanation.strip()) < 20:
        flash("Audit validation failed: A detailed explanation (minimum 20 characters) is required for high-risk actions.", "error")
        return redirect(url_for('tournament.manage_tournament', slug=slug))

    try:
        
        log_audit(
            action_type='delete_tournament',
            target_id=tournament.id,
            target_name=tournament.name,
            reason=reason,
            explanation=explanation
        )
        db.session.delete(tournament)
        db.session.commit()
        flash('Tournament deleted successfully!', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete tournament: {str(e)}', 'error')

    return redirect(url_for('main.index'))
