from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, Tournament, Category, Participant, Match, Group
from app.constants import TOURNAMENT_FORMATS
from app.formats import get_format
from app.routes.auth import login_required, role_required
from app.tennis_logic import validate_and_format_score
from datetime import datetime

category_bp = Blueprint('category', __name__)

def check_category_auto_completion(category):
    from app.models import Match
    has_knockout = category.format in ['single_elimination', 'double_elimination'] or \
                   category.format == 'group_stage' or \
                   (category.format == 'round_robin' and category.qualifiers_per_group and category.qualifiers_per_group > 0)

    all_matches = Match.query.filter_by(category_id=category.id).all()
    if not all_matches:
        return False
        
    pending = any(m.status == 'pending' for m in all_matches)
    if pending:
        return False
        
    if has_knockout:
        if category.format in ['group_stage', 'round_robin']:
            knockout_exists = any(m.match_type == 'knockout' or m.bracket_type in ['winners', 'losers', 'grand_finals', 'grand_final', 'third_place'] for m in all_matches)
            if not knockout_exists:
                return False
                
    return True

@category_bp.route('/tournaments/<slug>/categories/new', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def create_category(slug):
    """Create new category within tournament"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    if request.method == 'POST':
        name = request.form.get('name')
        format_type = request.form.get('format')
        if format_type == 'single_elimination':
            sub_format = request.form.get('sub_format')
            if sub_format == 'doubles':
                format_type = 'doubles_elimination'
        max_participants = request.form.get('max_participants', type=int)
        gender = request.form.get('gender', 'Unspecified')
        age_category = request.form.get('age_category', 'Unspecified')

        # Tennis settings
        num_sets = request.form.get('num_sets', type=int)
        games_per_set = request.form.get('games_per_set', type=int)
        total_games = request.form.get('total_games', type=int)
        points_to_win = request.form.get('points_to_win', type=int)

        # Advanced settings for group stage
        has_group_stage = (format_type in ['group_stage', 'round_robin'])
        num_groups = request.form.get('num_groups', type=int) if has_group_stage else None
        teams_per_group = request.form.get('teams_per_group', type=int) if has_group_stage else None
        matches_per_team_pair = request.form.get('matches_per_team_pair', type=int, default=1) if has_group_stage else None
        
        # Determine qualifiers for knockout stage
        if format_type == 'group_stage':
            qualifiers_per_group = request.form.get('qualifiers_per_group', type=int, default=2)
            allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on'
        elif format_type == 'round_robin':
            has_knockout = request.form.get('has_knockout_stage') == 'on'
            if has_knockout:
                qualifiers_per_group = request.form.get('qualifiers_per_group', type=int, default=2)
                allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on'
            else:
                qualifiers_per_group = 0
                allow_lucky_losers = False
        else:
            qualifiers_per_group = None
            allow_lucky_losers = False
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
            return redirect(request.referrer or url_for('tournament.view_tournament', slug=slug))

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
        fmt = get_format(category.format)
        if fmt:
            try:
                dummy_data = fmt.generate(category, participants)
            except Exception:
                pass
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
        from app.formats.group_stage.logic import GroupStageFormat
        groups = Group.query.filter_by(category_id=category_id).all()
        groups_data = []
        for group in groups:
            standings = GroupStageFormat.calculate_group_standings(group.id)
            group_matches = Match.query.filter(Match.group_id==group.id, Match.match_type.in_(['group_stage', 'round_robin'])).all()
            groups_data.append({
                'group': group,
                'standings': standings,
                'matches': group_matches
            })

    # Calculate final rankings if tournament is complete
    rankings = None
    if category.status == 'completed':
        fmt = get_format(category.format)
        if fmt:
            # Rankings are stored on the Participant model (final_rank) by calculate_final_rankings
            # We don't actually need to return them as a dict anymore since view.html can just use participants
            # But to keep backward compatibility:
            if category.format == 'round_robin':
                # Just get the sorted standings
                Participant.query.filter_by(category_id=category_id).all() # Refresh
                winners = Participant.query.filter(Participant.category_id==category_id, Participant.final_rank.isnot(None)).order_by(Participant.final_rank).all()
                if len(winners) >= 2:
                    rankings = {
                        'winner': winners[0],
                        'runner_up': winners[1],
                        'semi_finalists': winners[2:4] if len(winners) > 2 else []
                    }
            else:
                winners = Participant.query.filter(Participant.category_id==category_id, Participant.final_rank.isnot(None)).order_by(Participant.final_rank).all()
                if winners:
                    rankings = {
                        'winner': winners[0] if len(winners) > 0 else None,
                        'runner_up': next((p for p in winners if p.final_rank == 2), None),
                        'semi_finalists': [p for p in winners if p.final_rank == 3]
                    }

    rr_matches = [m for m in matches if m.match_type == 'round_robin']
    
    if category.status == 'setup' and not rr_matches and category.format == 'round_robin' and not category.num_groups:
        rr_matches = [DummyMatch(**d) for d in dummy_data]
    
    return render_template('category/view.html',
                         rr_matches=rr_matches,
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
                    player_id = None
                    player2_id = None
                    
                    if category.format == 'doubles_elimination' and '&' in name:
                        p1_name, p2_name = [n.strip() for n in name.split('&', 1)]
                        
                        # Process P1
                        p1_match = Player.query.filter_by(name=p1_name).first()
                        if not p1_match:
                            p1_match = Player(name=p1_name, gender=category.gender, age_category=category.age_category)
                            db.session.add(p1_match)
                            db.session.flush()
                        player_id = p1_match.id
                        
                        # Process P2
                        p2_match = Player.query.filter_by(name=p2_name).first()
                        if not p2_match:
                            p2_match = Player(name=p2_name, gender=category.gender, age_category=category.age_category)
                            db.session.add(p2_match)
                            db.session.flush()
                        player2_id = p2_match.id
                        
                        # Use standardized format for display name
                        name = f"{p1_name} & {p2_name}"
                        
                    else:
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
                        player2_id=player2_id,
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
                if tournament.status not in ['in_progress', 'completed']:
                    flash('You must start the overall Tournament before you can start individual categories.', 'error')
                    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
                    
                participants_list = Participant.query.filter_by(category_id=category_id).all()

                fmt = get_format(category.format)
                if fmt:
                    if category.format == 'round_robin' and category.teams_per_group and category.teams_per_group >= 3:
                        import math
                        total_players = len(participants_list)
                        category.num_groups = math.ceil(total_players / category.teams_per_group) if total_players > 0 else 1
                        
                        # Generate group stage data but tag as round robin
                        from app.formats.group_stage.logic import GroupStageFormat
                        matches_data = GroupStageFormat.generate(category, participants_list)
                        for match_data in matches_data:
                            match_data['match_type'] = 'round_robin'
                            match = Match(**match_data, tournament_id=tournament.id)
                            db.session.add(match)
                    else:
                        matches_data = fmt.generate(category, participants_list)
                        for match_data in matches_data:
                            if 'category_id' not in match_data:
                                match_data['category_id'] = category.id
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
                # Group stage settings
                if category.format == 'group_stage':
                    category.num_groups = request.form.get('num_groups', type=int)
                    category.teams_per_group = request.form.get('teams_per_group', type=int)
                    category.matches_per_team_pair = request.form.get('matches_per_team_pair', type=int, default=1)
                    category.qualifiers_per_group = request.form.get('qualifiers_per_group', type=int, default=2)
                    category.allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on'
                elif category.format == 'round_robin':
                    category.teams_per_group = request.form.get('teams_per_group', type=int)
                    has_knockout = request.form.get('has_knockout_stage') == 'on'
                    if has_knockout:
                        category.qualifiers_per_group = request.form.get('qualifiers_per_group', type=int, default=2)
                        category.allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on'
                    else:
                        category.qualifiers_per_group = 0
                        category.allow_lucky_losers = False

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
                    if format_type == 'single_elimination':
                        sub_format = request.form.get('sub_format')
                        if sub_format == 'doubles':
                            format_type = 'doubles_elimination'
                    num_sets = request.form.get('num_sets', type=int, default=1)
                    games_per_set = request.form.get('games_per_set', type=int, default=6)

                    category.format = format_type
                    category.num_sets = num_sets
                    category.games_per_set = games_per_set

                    category.has_group_stage = (format_type in ['group_stage', 'round_robin'])
                    if category.has_group_stage:
                        category.num_groups = request.form.get('num_groups', type=int)
                        category.teams_per_group = request.form.get('teams_per_group', type=int)
                        category.matches_per_team_pair = request.form.get('matches_per_team_pair', type=int, default=1)
                        if format_type == 'group_stage':
                            category.qualifiers_per_group = request.form.get('qualifiers_per_group', type=int)
                            category.allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on'
                        elif format_type == 'round_robin':
                            has_knockout = request.form.get('has_knockout_stage') == 'on'
                            if has_knockout:
                                category.qualifiers_per_group = request.form.get('qualifiers_per_group', type=int)
                                category.allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on'
                            else:
                                category.qualifiers_per_group = 0
                                category.allow_lucky_losers = False
                    else:
                        category.num_groups = None
                        category.teams_per_group = None
                        category.qualifiers_per_group = None
                        category.allow_lucky_losers = False

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
                fmt = get_format(category.format)
                if fmt:
                    fmt.calculate_final_rankings(category)

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

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/rename', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def rename_category(slug, category_id):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    new_name = request.form.get('new_name')
    if new_name and new_name.strip():
        category.name = new_name.strip()
        db.session.commit()
        flash(f"Category renamed to '{category.name}'", 'success')
    else:
        flash("Invalid category name.", "error")
    return redirect(request.referrer or url_for('tournament.manage_tournament', slug=slug))

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def delete_category(slug, category_id):
    """Delete a category and all its data"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    
    try:
        from app.models import Match, Group, Participant
        # Delete all matches
        Match.query.filter_by(category_id=category.id).delete()
        # Delete all participants
        Participant.query.filter_by(category_id=category.id).delete()
        # Delete all groups
        Group.query.filter_by(category_id=category.id).delete()
        
        db.session.delete(category)
        db.session.commit()
        flash(f"Category '{category.name}' deleted successfully.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete category: {str(e)}", 'error')
        
    return redirect(request.referrer or url_for('tournament.view_tournament', slug=slug))

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
        if category.format == 'round_robin' or (category.format == 'group_stage' and category.total_games):
            p1_score = request.form.get('set1_p1', type=int)
            p2_score = request.form.get('set1_p2', type=int)
            
            if p1_score is None or p2_score is None:
                raise ValueError("Scores for both players are required.")
                
            if winner_id == match.participant1_id and p1_score <= p2_score:
                raise ValueError("Winner must have a higher score.")
            if winner_id == match.participant2_id and p2_score <= p1_score:
                raise ValueError("Winner must have a higher score.")
                
            score1 = str(p1_score)
            score2 = str(p2_score)
        else:
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

        # Stats will be recalculated at the end

        fmt = get_format(category.format)
        if fmt:
            fmt.advance_match(match, category, winner_id)

        # Auto-completion removed. Admin must click Finish Tournament.

        db.session.commit()
        
        # Recalculate group/round-robin stats
        if category.format in ['group_stage', 'round_robin']:
            from app.leaderboard_logic import recalculate_all_group_stats
            recalculate_all_group_stats(category.id)
            
        flash('Match result reported successfully!', 'success')
    except ValueError as ve:
        db.session.rollback()
        flash(f'Invalid Tennis Score: {str(ve)}', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to report match result: {str(e)}', 'error')

    return redirect(url_for('category.view_category', slug=slug, category_id=category_id))


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/update_grid', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def update_grid_scores(slug, category_id):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    
    if category.status != 'in_progress':
        flash('Cannot update scores unless category is in progress.', 'error')
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
    
    from app.models import Match
    from datetime import datetime
    
    # Process form data
    # Expected format: match_{id}_p1, match_{id}_p2
    match_updates = {}
    for key, value in request.form.items():
        if key.startswith('match_'):
            parts = key.split('_')
            if len(parts) == 3:
                try:
                    match_id = int(parts[1])
                    player_idx = parts[2]
                    
                    if match_id not in match_updates:
                        match_updates[match_id] = {}
                        
                    if value and value.strip() != '':
                        match_updates[match_id][player_idx] = int(value)
                    else:
                        match_updates[match_id][player_idx] = None
                except ValueError:
                    continue
                    
    # Update matches
    updated_count = 0
    for match_id, scores in match_updates.items():
        match = Match.query.get(match_id)
        if not match or match.category_id != category.id:
            continue
            
        score1 = scores.get('p1')
        score2 = scores.get('p2')
        
        # Only update if both scores are provided, or if they were previously completed and now being updated
        if score1 is not None and score2 is not None:
            match.score1 = score1
            match.score2 = score2
            
            # Determine winner based on scores
            if score1 > score2:
                winner_id = match.participant1_id
            elif score2 > score1:
                winner_id = match.participant2_id
            else:
                winner_id = None
                
            if winner_id:
                match.winner_id = winner_id
                if match.status != 'completed':
                    match.status = 'completed'
                    match.completed_at = datetime.utcnow()
                updated_count += 1
        elif score1 is None and score2 is None:
            # If scores are cleared, revert match to pending
            if match.status == 'completed':
                match.status = 'pending'
                match.score1 = None
                match.score2 = None
                match.winner_id = None
                match.completed_at = None
                updated_count += 1

    db.session.commit()
    
    # Recalculate group/round-robin stats
    from app.leaderboard_logic import recalculate_all_group_stats
    recalculate_all_group_stats(category.id)

    # Check if category is finished
    if check_category_auto_completion(category):
        category.status = 'completed'
        category.completed_at = datetime.utcnow()
        if category.format == 'round_robin' and (not category.qualifiers_per_group or category.qualifiers_per_group == 0):
            from app.leaderboard_logic import calculate_combined_round_robin_standings
            calculate_combined_round_robin_standings(category.id)
        db.session.commit()
        from app.leaderboard_logic import assign_leaderboard_points
        assign_leaderboard_points(category)
    
    flash(f'Successfully updated {updated_count} matches.', 'success')
    return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
