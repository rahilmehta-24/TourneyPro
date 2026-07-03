from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, Tournament, Category, Participant, Match, Group
from app.constants import TOURNAMENT_FORMATS
from app.algorithms.single_elimination import generate_single_elimination, calculate_final_rankings
from app.algorithms.double_elimination import calculate_double_elimination_rankings
from app.algorithms.round_robin import calculate_round_robin_standings
from app.algorithms.group_stage import generate_group_stage, generate_knockout_from_groups, calculate_group_standings
from app.routes.auth import login_required, role_required
from app.tennis_logic import validate_and_format_score
from datetime import datetime

category_bp = Blueprint('category', __name__)

@category_bp.route('/tournaments/<slug>/categories/new', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def create_category(slug):
    """Create new category within tournament"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    if request.method == 'POST':
        name = request.form.get('name')
        format_type = request.form.get('format')
        max_participants = request.form.get('max_participants', type=int)
        gender = request.form.get('gender', 'Unspecified')
        age_category = request.form.get('age_category', 'Unspecified')

        # Tennis settings
        num_sets = request.form.get('num_sets', type=int)
        games_per_set = request.form.get('games_per_set', type=int)
        total_games = request.form.get('total_games', type=int)
        points_to_win = request.form.get('points_to_win', type=int)

        # Advanced settings for group stage
        has_group_stage = (format_type == 'group_stage')
        num_groups = request.form.get('num_groups', type=int) if has_group_stage else None
        teams_per_group = request.form.get('teams_per_group', type=int) if has_group_stage else None
        matches_per_team_pair = request.form.get('matches_per_team_pair', type=int, default=1) if has_group_stage else None
        qualifiers_per_group = request.form.get('qualifiers_per_group', type=int, default=2) if has_group_stage else None
        allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on' if has_group_stage else False
        max_players_per_team = request.form.get('max_players_per_team', type=int)

        category = Category(
            tournament_id=tournament.id,
            name=name,
            gender=gender,
            age_category=age_category,
            format=format_type,
            max_participants=max_participants,
            num_sets=num_sets,
            games_per_set=games_per_set,
            total_games=total_games,
            points_to_win=points_to_win,
            has_group_stage=has_group_stage,
            num_groups=num_groups,
            teams_per_group=teams_per_group,
            matches_per_team_pair=matches_per_team_pair,
            qualifiers_per_group=qualifiers_per_group,
            allow_lucky_losers=allow_lucky_losers,
            max_players_per_team=max_players_per_team
        )

        try:
            db.session.add(category)
            tournament.has_categories = True
            db.session.commit()
            flash(f'Category "{name}" created successfully!', 'success')
            return redirect(url_for('category.manage_category', slug=slug, category_id=category.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create category: {str(e)}', 'error')
            return redirect(url_for('tournament.view_tournament', slug=slug))

    return render_template('category/create.html', tournament=tournament, formats=TOURNAMENT_FORMATS)

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>')
def view_category(slug, category_id):
    """View category bracket/standings"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    participants = Participant.query.filter_by(category_id=category_id).order_by(Participant.seed).all()
    matches = Match.query.filter_by(category_id=category_id).order_by(Match.round, Match.match_number).all()

    # If tournament is still in setup, generate preview bracket on the fly
    if category.status == 'setup' and not matches and participants:
        class DummyMatch:
            def __init__(self, **kwargs):
                self.match_type = 'knockout'
                self.bracket_type = 'winners'
                self.round = 1
                self.match_number = 1
                for k, v in kwargs.items():
                    setattr(self, k, v)
                self.status = 'pending'
                self.score1 = None
                self.score2 = None
                self.winner_id = None
                self.id = 0
                
                p1_id = getattr(self, 'participant1_id', None)
                p2_id = getattr(self, 'participant2_id', None)
                self.participant1 = next((p for p in participants if p.id == p1_id), None) if p1_id else None
                self.participant2 = next((p for p in participants if p.id == p2_id), None) if p2_id else None

        dummy_data = []
        if category.format == 'single_elimination':
            dummy_data = generate_single_elimination(participants)
        elif category.format == 'double_elimination':
            from app.algorithms.double_elimination import generate_double_elimination
            dummy_data = generate_double_elimination(participants, use_manual_seeding=False)
        elif category.format == 'round_robin':
            from app.algorithms.round_robin import generate_round_robin
            dummy_data = generate_round_robin(participants)
        elif category.format == 'group_stage':
            from app.algorithms.group_stage import generate_group_stage
            # Preview for group stage matches
            if category.num_groups:
                groups_data, dummy_data = generate_group_stage(participants, category.num_groups)
                


        matches = [DummyMatch(**d) for d in dummy_data]

    # Group matches by round for knockout
    rounds = {}
    winners_rounds = {}
    losers_rounds = {}
    grand_finals = []
    for match in matches:
        if match.match_type == 'knockout':
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

    # Get group stage data if applicable
    groups_data = None
    if category.has_group_stage:
        groups = Group.query.filter_by(category_id=category_id).all()
        groups_data = []
        for group in groups:
            standings = calculate_group_standings(group.id)
            group_matches = Match.query.filter_by(group_id=group.id, match_type='group_stage').all()
            groups_data.append({
                'group': group,
                'standings': standings,
                'matches': group_matches
            })

    # Calculate final rankings if tournament is complete
    rankings = None
    if category.status == 'completed':
        if category.format == 'single_elimination':
            rankings = calculate_final_rankings(category)
        elif category.format == 'double_elimination':
            rankings = calculate_double_elimination_rankings(category)
        elif category.format == 'round_robin':
            standings = calculate_round_robin_standings(category_id)
            if len(standings) >= 2:
                rankings = {
                    'winner': standings[0]['participant'],
                    'runner_up': standings[1]['participant'],
                    'semi_finalists': [s['participant'] for s in standings[2:4]] if len(standings) > 2 else []
                }

    return render_template('category/view.html',
                         tournament=tournament,
                         category=category,
                         participants=participants,
                         matches=matches,
                         rounds=rounds,
                         winners_rounds=winners_rounds,
                         losers_rounds=losers_rounds,
                         grand_finals=grand_finals,
                         groups_data=groups_data,
                         rankings=rankings,
                         formats=TOURNAMENT_FORMATS)

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/manage', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def manage_category(slug, category_id):
    """Manage category participants and settings"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    participants = Participant.query.filter_by(category_id=category_id).order_by(Participant.manual_seed, Participant.seed).all()

    if request.method == 'POST':
        action = request.form.get('action')

        try:
            if action == 'add_participant':
                participant_name = request.form.get('participant_name')
                participant_email = request.form.get('participant_email', '')
                manual_seed = request.form.get('manual_seed', type=int)

                # Handle comma-separated names
                names = [n.strip() for n in participant_name.split(',') if n.strip()]
                
                # Check max participants limit against multiple additions
                if category.max_participants and len(participants) + len(names) > category.max_participants:
                    flash(f'Cannot add participants. Maximum limit of {category.max_participants} would be exceeded.', 'error')
                    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

                from app.models import Player
                
                added_names = []
                for name in names:
                    player_match = Player.query.filter_by(name=name).first()
                    if not player_match:
                        # Auto-create global player so they appear on leaderboard instantly
                        player_match = Player(name=name, gender=category.gender, age_category=category.age_category)
                        db.session.add(player_match)
                        db.session.flush() # flush to get the ID

                    player_id = player_match.id

                    participant = Participant(
                        tournament_id=tournament.id,
                        category_id=category.id,
                        player_id=player_id,
                        name=name,
                        email=participant_email if len(names) == 1 else '', # Only apply email if single participant added
                        manual_seed=manual_seed if len(names) == 1 else None # Only apply seed if single participant
                    )
                    db.session.add(participant)
                    added_names.append(name)
                    
                db.session.commit()

                flash(f'Added participants: {", ".join(added_names)}', 'success')
                return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

            elif action == 'start_category':
                participants_list = Participant.query.filter_by(category_id=category_id).all()

                if category.format == 'single_elimination':
                    matches_data = generate_single_elimination(participants_list)
                    for match_data in matches_data:
                        match = Match(**match_data, tournament_id=tournament.id, category_id=category.id)
                        db.session.add(match)

                elif category.format == 'round_robin':
                    from app.algorithms.round_robin import generate_round_robin
                    matches_data = generate_round_robin(participants_list)
                    for match_data in matches_data:
                        match = Match(**match_data, tournament_id=tournament.id, category_id=category.id)
                        db.session.add(match)

                elif category.format == 'group_stage':
                    matches_data = generate_group_stage(category, participants_list)
                    for match_data in matches_data:
                        match = Match(**match_data, tournament_id=tournament.id)
                        db.session.add(match)

                category.status = 'in_progress'
                category.started_at = datetime.utcnow()
                db.session.commit()

                flash('Category started! Bracket generated.', 'success')
                return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

            elif action == 'update_settings':
                name = request.form.get('name')
                max_participants = request.form.get('max_participants', type=int)
                total_games = request.form.get('total_games', type=int)
                points_to_win = request.form.get('points_to_win', type=int)
                max_players_per_team = request.form.get('max_players_per_team', type=int)
                
                # Group stage settings
                has_group_stage = category.format == 'group_stage'
                if has_group_stage:
                    category.num_groups = request.form.get('num_groups', type=int)
                    category.teams_per_group = request.form.get('teams_per_group', type=int)
                    category.matches_per_team_pair = request.form.get('matches_per_team_pair', type=int, default=1)
                    category.qualifiers_per_group = request.form.get('qualifiers_per_group', type=int, default=2)
                    category.allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on'

                if not name:
                    flash('Category name cannot be empty.', 'error')
                    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

                category.name = name
                category.max_participants = max_participants
                category.total_games = total_games
                category.points_to_win = points_to_win
                category.max_players_per_team = max_players_per_team

                # Settings only editable in setup status
                if category.status == 'setup':
                    format_type = request.form.get('format')
                    num_sets = request.form.get('num_sets', type=int, default=1)
                    games_per_set = request.form.get('games_per_set', type=int, default=6)

                    category.format = format_type
                    category.num_sets = num_sets
                    category.games_per_set = games_per_set

                    category.has_group_stage = (format_type == 'group_stage')
                    if category.has_group_stage:
                        category.num_groups = request.form.get('num_groups', type=int)
                        category.teams_per_group = request.form.get('teams_per_group', type=int)
                        category.matches_per_team_pair = request.form.get('matches_per_team_pair', type=int, default=1)
                        category.qualifiers_per_group = request.form.get('qualifiers_per_group', type=int)
                    else:
                        category.num_groups = None
                        category.teams_per_group = None
                        category.qualifiers_per_group = None

                db.session.commit()
                flash('Category settings updated successfully!', 'success')
                return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

            elif action == 'delete_participant':
                participant_id = request.form.get('participant_id', type=int)
                participant = Participant.query.get(participant_id)
                if participant:
                    db.session.delete(participant)
                    db.session.commit()
                    flash(f'Removed participant: {participant.name}', 'info')
                return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

            elif action == 'reset_category':
                if category.status in ['in_progress', 'completed']:
                    # Delete matches
                    Match.query.filter_by(category_id=category_id).delete()

                    # Delete groups
                    Group.query.filter_by(category_id=category_id).delete()

                    # Reset participants stats and group assignments
                    category_participants = Participant.query.filter_by(category_id=category_id).all()
                    for p in category_participants:
                        p.group_id = None
                        p.group_wins = 0
                        p.group_losses = 0
                        p.group_points = 0
                        p.final_rank = None

                    category.status = 'setup'
                    category.started_at = None
                    category.completed_at = None

                    db.session.commit()
                    flash('Category bracket stopped and reset! You can now edit settings and add/remove players.', 'success')
                    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
                else:
                    flash('Category is already in setup status.', 'warning')
                    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

            elif action == 'finish_category':
                category.status = 'completed'
                category.completed_at = datetime.utcnow()

                # Make sure rankings are calculated if not already done
                if category.format == 'single_elimination':
                    calculate_final_rankings(category)
                elif category.format == 'double_elimination':
                    calculate_double_elimination_rankings(category)

                db.session.commit()

                from app.leaderboard_logic import assign_leaderboard_points
                assign_leaderboard_points(category)

                flash('Tournament completed and points assigned to leaderboard! 🏆', 'success')
                return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to perform action: {str(e)}', 'error')
            return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

    return render_template('category/manage.html',
                         tournament=tournament,
                         category=category,
                         participants=participants,
                         formats=TOURNAMENT_FORMATS)

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/seeding', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def manage_seeding(slug, category_id):
    """Manage manual seeding for participants"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    participants = Participant.query.filter_by(category_id=category_id).all()

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
            return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update seeding: {str(e)}', 'error')
            return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

    return render_template('category/seeding.html',
                         tournament=tournament,
                         category=category,
                         participants=participants)

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/start-knockout', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def start_knockout_stage(slug, category_id):
    """Transition from group stage to knockout"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)

    if not category.has_group_stage:
        flash('This category does not have a group stage.', 'error')
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

    try:
        # Generate knockout bracket from group qualifiers
        matches_data = generate_knockout_from_groups(category)

        for match_data in matches_data:
            match = Match(**match_data, tournament_id=tournament.id)
            db.session.add(match)

        db.session.commit()
        flash('Knockout stage started!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to start knockout stage: {str(e)}', 'error')

    return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/match/<int:match_id>/report', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def report_category_match_result(slug, category_id, match_id):
    """Report match result for category"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    match = Match.query.get_or_404(match_id)

    try:
        winner_id = request.form.get('winner_id', type=int)

        # We need num_sets and games_per_set from category
        num_sets = category.num_sets or 3
        games_per_set = category.games_per_set or 6

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

        # Validate and format score
        score1, score2 = validate_and_format_score(
            winner_id, match.participant1_id, match.participant2_id,
            num_sets, games_per_set, form_data
        )

        match.winner_id = winner_id
        match.score1 = score1
        match.score2 = score2
        match.status = 'completed'
        match.completed_at = datetime.utcnow()
        db.session.commit()

        from app.leaderboard_logic import update_live_player_stats
        update_live_player_stats(match)

        # Update group stage stats if applicable
        if match.match_type == 'group_stage':
            winner = Participant.query.get(winner_id)
            if winner:
                winner.group_wins += 1
                winner.group_points += 3

            # Update loser
            loser_id = match.participant1_id if match.participant1_id != winner_id else match.participant2_id
            if loser_id:
                loser = Participant.query.get(loser_id)
                if loser:
                    loser.group_losses += 1

        # Update next round match for knockout
        elif match.match_type == 'knockout':
            if category.format == 'single_elimination':
                next_round = match.round + 1
                next_match_number = (match.match_number + 1) // 2

                next_match = Match.query.filter_by(
                    category_id=category.id,
                    round=next_round,
                    match_number=next_match_number,
                    bracket_type=match.bracket_type
                ).first()

                if next_match:
                    if match.match_number % 2 == 1:
                        next_match.participant1_id = winner_id
                    else:
                        next_match.participant2_id = winner_id
            elif category.format == 'double_elimination':
                # Double Elimination Progression Logic
                loser_id = match.participant1_id if match.participant1_id != winner_id else match.participant2_id

                # Fetch winners matches to find num_rounds_winners
                winners_matches = Match.query.filter_by(category_id=category.id, bracket_type='winners').all()
                num_rounds_winners = max(m.round for m in winners_matches) if winners_matches else 0

                if match.bracket_type == 'winners':
                    # 1. Winner advances in Winners
                    next_round = match.round + 1
                    next_match_number = (match.match_number + 1) // 2

                    next_match = Match.query.filter_by(
                        category_id=category.id,
                        round=next_round,
                        match_number=next_match_number,
                        bracket_type='winners'
                    ).first()

                    if next_match:
                        if match.match_number % 2 == 1:
                            next_match.participant1_id = winner_id
                        else:
                            next_match.participant2_id = winner_id
                    else:
                        # No next winners round match, so this is Winners Final.
                        # Winner goes to Grand Finals Match 1 as participant1_id
                        gf_match = Match.query.filter_by(
                            category_id=category.id,
                            bracket_type='grand_finals',
                            match_number=1
                        ).first()
                        if gf_match:
                            gf_match.participant1_id = winner_id

                    # 2. Loser drops to corresponding Losers match
                    if match.round == 1:
                        # Winners Rd 1 match M loser goes to Losers Rd 1 match (M - 1) // 2 + 1
                        target_round = 1
                        target_match_number = (match.match_number - 1) // 2 + 1
                        target_match = Match.query.filter_by(
                            category_id=category.id,
                            round=target_round,
                            match_number=target_match_number,
                            bracket_type='losers'
                        ).first()
                        if target_match:
                            if match.match_number % 2 == 1:
                                target_match.participant1_id = loser_id
                            else:
                                target_match.participant2_id = loser_id
                    else:
                        # Winners Rd R > 1 match M loser goes to Losers Rd 2R - 2 match M, as participant1_id
                        target_round = 2 * match.round - 2
                        target_match_number = match.match_number
                        target_match = Match.query.filter_by(
                            category_id=category.id,
                            round=target_round,
                            match_number=target_match_number,
                            bracket_type='losers'
                        ).first()
                        if target_match:
                            target_match.participant1_id = loser_id

                elif match.bracket_type == 'losers':
                    # 1. Winner advances in Losers
                    max_losers_round = 2 * num_rounds_winners - 2 if num_rounds_winners >= 2 else 0

                    if match.round == max_losers_round:
                        # Winners of Losers Final go to Grand Finals Match 1 as participant2_id
                        gf_match = Match.query.filter_by(
                            category_id=category.id,
                            bracket_type='grand_finals',
                            match_number=1
                        ).first()
                        if gf_match:
                            gf_match.participant2_id = winner_id
                    else:
                        # Advancement within losers bracket
                        if match.round % 2 == 1:
                            # Odd round R match M winner goes to round R+1 match M as participant2_id
                            target_round = match.round + 1
                            target_match_number = match.match_number
                            target_match = Match.query.filter_by(
                                category_id=category.id,
                                round=target_round,
                                match_number=target_match_number,
                                bracket_type='losers'
                            ).first()
                            if target_match:
                                target_match.participant2_id = winner_id
                        else:
                            # Even round R match M winner goes to round R+1 match (M+1)//2
                            target_round = match.round + 1
                            target_match_number = (match.match_number + 1) // 2
                            target_match = Match.query.filter_by(
                                category_id=category.id,
                                round=target_round,
                                match_number=target_match_number,
                                bracket_type='losers'
                            ).first()
                            if target_match:
                                if match.match_number % 2 == 1:
                                    target_match.participant1_id = winner_id
                                else:
                                    target_match.participant2_id = winner_id

                elif match.bracket_type == 'grand_finals':
                    if match.match_number == 1:
                        # Grand Finals Match 1
                        if winner_id == match.participant1_id:
                            # Undefeated Winners champion won! Complete GF Match 2 with status completed but empty winner.
                            match2 = Match.query.filter_by(
                                category_id=category.id,
                                bracket_type='grand_finals',
                                match_number=2
                            ).first()
                            if match2:
                                match2.status = 'completed'
                                match2.score1 = 'N/A'
                                match2.score2 = 'N/A'
                                match2.completed_at = datetime.utcnow()
                        else:
                            # Losers champion won. Reset match activated!
                            match2 = Match.query.filter_by(
                                category_id=category.id,
                                bracket_type='grand_finals',
                                match_number=2
                            ).first()
                            if match2:
                                match2.participant1_id = match.participant1_id
                                match2.participant2_id = match.participant2_id
                                match2.status = 'pending'

        # Check if category is completed
        all_matches = Match.query.filter_by(category_id=category_id).all()
        if all(m.status == 'completed' for m in all_matches):
            category.status = 'completed'
            category.completed_at = datetime.utcnow()

            # Calculate final rankings and rank participants
            if category.format == 'single_elimination':
                calculate_final_rankings(category)
            elif category.format == 'double_elimination':
                calculate_double_elimination_rankings(category)

            db.session.commit()

            from app.leaderboard_logic import assign_leaderboard_points
            assign_leaderboard_points(category)

        db.session.commit()
        flash('Match result reported successfully!', 'success')
    except ValueError as ve:
        db.session.rollback()
        flash(f'Invalid Tennis Score: {str(ve)}', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to report match result: {str(e)}', 'error')

    return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
