from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.domain.models import db, Tournament, Category, Participant, Match, Group, Player, determine_age_category, estimate_dob_from_age
from app.core.constants import TOURNAMENT_FORMATS
from app.services.format_engine import get_format
from app.web.controllers.auth import login_required, role_required, check_tournament_ownership
from app.services.tennis_logic import validate_and_format_score, validate_total_7_games_score
from datetime import datetime
import random
from app.services.utils.validation import (
    validate_name, validate_mobile, validate_email, validate_age
)
from app.web.controllers.export import get_category_winners

category_bp = Blueprint('category', __name__)

def check_category_auto_completion(category):
    from app.domain.models import Match
    has_knockout = category.format in ['single_elimination', 'double_elimination'] or \
                   category.format == 'group_stage' or \
                   (category.format in ['round_robin', 'doubles_round_robin'] and category.qualifiers_per_group and category.qualifiers_per_group > 0)

    all_matches = Match.query.filter_by(category_id=category.id).all()
    if not all_matches:
        return False
        
    pending = any(m.status == 'pending' for m in all_matches)
    if pending:
        return False
        
    if has_knockout:
        if category.format in ['group_stage', 'round_robin', 'doubles_round_robin']:
            knockout_exists = any(m.match_type == 'knockout' or m.bracket_type in ['winners', 'losers', 'grand_finals', 'grand_final', 'third_place'] for m in all_matches)
            if not knockout_exists:
                return False
                
    return True

def start_single_category(category, tournament):
    """Helper to start a single category and generate brackets."""
    from app.domain.models import Participant, Match, db
    from app.services.format_engine import get_format
    from datetime import datetime

    participants_list = Participant.query.filter_by(category_id=category.id).all()
    fmt = get_format(category.format)
    if fmt:
        if category.format in ['round_robin', 'doubles_round_robin'] and category.teams_per_group and category.teams_per_group >= 3:
            import math
            total_players = len(participants_list)
            if not category.num_groups:
                category.num_groups = math.ceil(total_players / category.teams_per_group) if total_players > 0 else 1
            
            from app.services.format_engine.group_stage.logic import GroupStageFormat
            matches_data = GroupStageFormat.generate(category, participants_list)
            for match_data in matches_data:
                child_rubbers = match_data.pop('child_rubbers', None)
                match_data['match_type'] = 'round_robin'
                if 'category_id' not in match_data:
                    match_data['category_id'] = category.id
                match = Match(**match_data, tournament_id=tournament.id)
                db.session.add(match)
                db.session.flush()
                if child_rubbers:
                    for r_data in child_rubbers:
                        r_data['parent_match_id'] = match.id
                        r_data['tournament_id'] = tournament.id
                        r_data['category_id'] = category.id
                        r_data['group_id'] = match.group_id
                        r_data['round'] = match.round
                        r_data['match_type'] = 'round_robin'
                        r_data['bracket_type'] = match.bracket_type
                        child_match = Match(**r_data)
                        db.session.add(child_match)
        else:
            matches_data = fmt.generate(category, participants_list)
            for match_data in matches_data:
                child_rubbers = match_data.pop('child_rubbers', None)
                if 'category_id' not in match_data:
                    match_data['category_id'] = category.id
                match = Match(**match_data, tournament_id=tournament.id)
                db.session.add(match)
                db.session.flush()
                if child_rubbers:
                    for r_data in child_rubbers:
                        r_data['parent_match_id'] = match.id
                        r_data['tournament_id'] = tournament.id
                        r_data['category_id'] = category.id
                        r_data['group_id'] = match.group_id
                        r_data['round'] = match.round
                        r_data['match_type'] = match.match_type
                        r_data['bracket_type'] = match.bracket_type
                        child_match = Match(**r_data)
                        db.session.add(child_match)

    category.status = 'in_progress'
    category.started_at = datetime.utcnow()
    db.session.commit()

    try:
        from app.services.utils.scheduler import auto_schedule_tournament
        auto_schedule_tournament(tournament.id)
    except Exception:
        pass



@category_bp.route('/t/<slug>/categories/new', methods=['GET', 'POST'])
@category_bp.route('/tournaments/<slug>/categories/new', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def create_category(slug):
    """Create new category within tournament"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)

    if request.method == 'POST':
        name = request.form.get('name')
        format_type = request.form.get('format')
        if format_type == 'single_elimination':
            sub_format = request.form.get('sub_format')
            if sub_format == 'doubles':
                format_type = 'doubles_elimination'
        elif format_type == 'round_robin':
            sub_format = request.form.get('sub_format')
            if sub_format == 'doubles':
                format_type = 'doubles_round_robin'
        max_participants = request.form.get('max_participants', type=int)
        gender = request.form.get('gender')
        age_category = request.form.get('age_category')

        # Tennis settings
        scoring_format = request.form.get('scoring_format', 'games')
        num_sets = request.form.get('num_sets', type=int)
        games_per_set = request.form.get('games_per_set', type=int)
        total_games = request.form.get('total_games', type=int)
        points_to_win = request.form.get('points_to_win', type=int)
        team_size = request.form.get('team_size', type=int) or 5
        rubbers_per_tie = request.form.get('rubbers_per_tie', type=int) or 3
        max_players_per_team = request.form.get('max_players_per_team', type=int)

        # Advanced settings for group stage
        has_group_stage = (format_type in ['group_stage', 'round_robin', 'doubles_round_robin'])
        num_groups = request.form.get('num_groups', type=int) if has_group_stage else None
        teams_per_group = request.form.get('teams_per_group', type=int) if has_group_stage else None
        matches_per_team_pair = request.form.get('matches_per_team_pair', type=int, default=1) if has_group_stage else None
        
        # Determine qualifiers for knockout stage
        if format_type == 'group_stage':
            # Group Stage is a team event: Gender & Age Category default to Open
            if not gender or gender in ('', 'Unspecified'):
                gender = 'Open'
            if not age_category or age_category in ('', 'Unspecified'):
                age_category = 'Open'
            scoring_format = 'games'
            total_games = total_games or 7
            team_size = team_size or 5
            max_players_per_team = max_players_per_team or team_size
            rubbers_per_tie = rubbers_per_tie or 3
            num_groups = num_groups or 3
            teams_per_group = teams_per_group or 4
            matches_per_team_pair = matches_per_team_pair or 1
            qualifiers_per_group = request.form.get('qualifiers_per_group', type=int, default=2) or 2
            allow_lucky_losers = request.form.get('allow_lucky_losers') in ['on', 'true', '1'] or ('allow_lucky_losers' in request.form)
            if not max_participants:
                max_participants = num_groups * teams_per_group
            num_sets = 1
            games_per_set = total_games
        elif format_type == 'round_robin':
            gender = gender or 'Unspecified'
            age_category = age_category or 'Unspecified'
            has_knockout = request.form.get('has_knockout_stage') == 'on'
            if has_knockout:
                qualifiers_per_group = request.form.get('qualifiers_per_group', type=int, default=2)
                allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on'
            else:
                qualifiers_per_group = 0
                allow_lucky_losers = False
        else:
            gender = gender or 'Unspecified'
            age_category = age_category or 'Unspecified'
            qualifiers_per_group = None
            allow_lucky_losers = False

        # Scheduling fields inherited globally from tournament
        num_courts = request.form.get('num_courts', type=int) or tournament.num_courts or 1
        court_names = request.form.get('court_names') or tournament.court_names or ''
        start_date_time = None
        avg_match_duration = request.form.get('avg_match_duration', type=int) or tournament.avg_match_duration or 60
        preferred_start_day = request.form.get('preferred_start_day', type=int, default=1)
        pin_finals_to_last_day = request.form.get('pin_finals_to_last_day') == 'on'
        entry_fee = request.form.get('entry_fee', type=float, default=0.0)

        ok, clean_name = validate_name(name, min_len=2, max_len=80, field_name="Category Name")
        if not ok:
            flash(clean_name, 'error')
            return render_template('category/create.html', tournament=tournament, formats=TOURNAMENT_FORMATS)
        name = clean_name

        if entry_fee is not None and entry_fee < 0:
            flash("Entry fee cannot be negative.", 'error')
            return render_template('category/create.html', tournament=tournament, formats=TOURNAMENT_FORMATS)
        entry_fee = max(0.0, float(entry_fee or 0.0))

        if max_participants is not None and max_participants < 2:
            flash("Max participants must be at least 2.", 'error')
            return render_template('category/create.html', tournament=tournament, formats=TOURNAMENT_FORMATS)

        if total_games is not None and total_games < 1:
            flash("Total games must be a positive integer.", 'error')
            return render_template('category/create.html', tournament=tournament, formats=TOURNAMENT_FORMATS)

        if points_to_win is not None and points_to_win < 1:
            flash("Points to win must be a positive integer.", 'error')
            return render_template('category/create.html', tournament=tournament, formats=TOURNAMENT_FORMATS)

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
            scoring_format=scoring_format,
            points_to_win=points_to_win,
            team_size=team_size,
            rubbers_per_tie=rubbers_per_tie,
            has_group_stage=has_group_stage,
            num_groups=num_groups,
            teams_per_group=teams_per_group,
            matches_per_team_pair=matches_per_team_pair,
            qualifiers_per_group=qualifiers_per_group,
            allow_lucky_losers=allow_lucky_losers,
            max_players_per_team=max_players_per_team,
            num_courts=num_courts,
            court_names=court_names,
            start_date_time=start_date_time,
            avg_match_duration=avg_match_duration,
            preferred_start_day=preferred_start_day,
            pin_finals_to_last_day=pin_finals_to_last_day,
            entry_fee=entry_fee
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

@category_bp.route('/t/<slug>/categories/<int:category_id>')
@category_bp.route('/tournaments/<slug>/categories/<int:category_id>')
def view_category(slug, category_id):
    """View category bracket/standings"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    category = Category.query.get_or_404(category_id)
    participants = Participant.query.filter_by(category_id=category_id).order_by(Participant.seed).all()
    matches = Match.query.options(
        db.joinedload(Match.participant1),
        db.joinedload(Match.participant2),
        db.joinedload(Match.winner),
        db.joinedload(Match.sub_matches)
    ).filter(Match.category_id==category_id, Match.parent_match_id.is_(None)).order_by(Match.round, Match.match_number).all()

    # If tournament is still in setup, generate preview bracket on the fly
    if category.status == 'setup' and not matches and participants:
        class DummyMatch:
            def __init__(self, **kwargs):
                self.match_type = 'knockout'
                self.bracket_type = 'winners'
                self.round = 1
                self.match_number = 1
                self.sub_matches = []
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
    third_placed_teams = []
    group_stage_completed = False
    has_knockout_started = any(m.match_type == 'knockout' for m in matches)
    if category.has_group_stage:
        from app.services.format_engine.group_stage.logic import GroupStageFormat
        groups = Group.query.filter_by(category_id=category_id).all()
        groups_data = []
        qualifiers_per_group = category.qualifiers_per_group or 2
        for group in groups:
            standings = GroupStageFormat.calculate_group_standings(group.id)
            group_matches = Match.query.options(
                db.joinedload(Match.participant1),
                db.joinedload(Match.participant2),
                db.joinedload(Match.winner),
                db.joinedload(Match.sub_matches)
            ).filter(Match.group_id==group.id, Match.parent_match_id.is_(None), Match.match_type.in_(['group_stage', 'round_robin', 'doubles_round_robin'])).all()
            groups_data.append({
                'group': group,
                'standings': standings,
                'matches': group_matches
            })
            if len(standings) > qualifiers_per_group:
                third_placed_teams.append(standings[qualifiers_per_group])

        if groups_data and any(g['matches'] for g in groups_data):
            group_stage_completed = all(
                m.status == 'completed' for g in groups_data for m in g['matches']
            )

    # Calculate final rankings if tournament is complete
    rankings = None
    if category.status == 'completed':
        fmt = get_format(category.format)
        if fmt:
            if category.format in ['round_robin', 'doubles_round_robin']:
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
    
    if category.status == 'setup' and not rr_matches and category.format in ['round_robin', 'doubles_round_robin'] and not category.num_groups:
        rr_matches = [DummyMatch(**d) for d in dummy_data]
    
    is_export = request.args.get('export') == '1'
    winners = get_category_winners(category) if is_export else []
    
    return render_template('category/view.html',
                         is_export=is_export,
                         winners=winners,
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
                         third_placed_teams=third_placed_teams,
                         group_stage_completed=group_stage_completed,
                         has_knockout_started=has_knockout_started,
                         rankings=rankings,
                         formats=TOURNAMENT_FORMATS)

@category_bp.route('/t/<slug>/categories/<int:category_id>/manage', methods=['GET', 'POST'])
@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/manage', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def manage_category(slug, category_id):
    """Manage category participants and settings"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)
    if category.format == 'group_stage':
        participants = Participant.query.filter_by(category_id=category_id).order_by(Participant.id).all()
    else:
        participants = Participant.query.filter_by(category_id=category_id).order_by(Participant.manual_seed, Participant.seed).all()

    if request.method == 'POST':
        action = request.form.get('action')

        try:
            if action == 'add_participant':
                participant_name = request.form.get('participant_name', '').strip()
                participant_age_str = request.form.get('participant_age', '').strip()
                participant_mobile = request.form.get('participant_mobile', '').strip()
                participant_email = request.form.get('participant_email', '').strip()
                manual_seed = request.form.get('manual_seed', type=int) if category.format != 'group_stage' else None
                skill_tier = request.form.get('skill_tier', '').strip() or None
                if skill_tier not in ['A', 'B', 'C', 'D', 'E']:
                    skill_tier = None

                partner_name = request.form.get('partner_name', '').strip()
                partner_age_str = request.form.get('partner_age', '').strip()
                partner_mobile = request.form.get('partner_mobile', '').strip()
                partner_email = request.form.get('partner_email', '').strip()

                if not participant_name:
                    flash('Participant name is required.', 'error')
                    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

                if category.format != 'group_stage' and manual_seed is not None and manual_seed < 1:
                    flash('Seed must be a positive integer (1 or greater).', 'error')
                    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

                if participant_mobile:
                    ok, clean_mob = validate_mobile(participant_mobile, required=False)
                    if not ok:
                        flash(clean_mob, 'error')
                        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
                    participant_mobile = clean_mob

                if participant_email:
                    ok, clean_em = validate_email(participant_email, required=False)
                    if not ok:
                        flash(clean_em, 'error')
                        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
                    participant_email = clean_em

                if participant_age_str:
                    ok, clean_age = validate_age(participant_age_str, required=False)
                    if not ok:
                        flash(clean_age, 'error')
                        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

                if partner_name:
                    ok, clean_pname = validate_name(partner_name, field_name="Partner Name")
                    if not ok:
                        flash(clean_pname, 'error')
                        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
                    partner_name = clean_pname

                    if partner_mobile:
                        ok, clean_pmob = validate_mobile(partner_mobile, required=False, field_name="Partner Mobile")
                        if not ok:
                            flash(clean_pmob, 'error')
                            return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
                        partner_mobile = clean_pmob

                    if partner_email:
                        ok, clean_pem = validate_email(partner_email, required=False, field_name="Partner Email")
                        if not ok:
                            flash(clean_pem, 'error')
                            return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
                        partner_email = clean_pem

                    if partner_age_str:
                        ok, clean_page = validate_age(partner_age_str, required=False, field_name="Partner Age")
                        if not ok:
                            flash(clean_page, 'error')
                            return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

                # Handle comma-separated names
                names = [n.strip() for n in participant_name.split(',') if n.strip()]
                for n in names:
                    ok, clean_n = validate_name(n, field_name="Participant Name")
                    if not ok:
                        flash(clean_n, 'error')
                        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

                # Check max participants limit against multiple additions
                if category.max_participants and len(participants) + len(names) > category.max_participants:
                    flash(f'Cannot add participants. Maximum limit of {category.max_participants} would be exceeded.', 'error')
                    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

                added_names = []
                for name in names:
                    p1_name = name
                    p2_name = partner_name
                    p1_age_str = participant_age_str
                    p2_age_str = partner_age_str
                    p1_mobile = participant_mobile
                    p2_mobile = partner_mobile

                    is_doubles = category.format in ['doubles_elimination', 'doubles_round_robin'] or 'Doubles' in category.name
                    if '/' in name and not p2_name:
                        parts = [n.strip() for n in name.split('/', 1)]
                        p1_name = parts[0]
                        p2_name = parts[1]

                    # Process P1
                    p1_age = int(p1_age_str) if p1_age_str and p1_age_str.isdigit() else None
                    p1_dob = estimate_dob_from_age(p1_age)
                    p1_cat = determine_age_category(age=p1_age, dob=p1_dob) if p1_age else category.age_category

                    p1_match = None
                    if p1_mobile:
                        p1_match = Player.query.filter(Player.contact_number == p1_mobile).first()
                    if not p1_match:
                        p1_match = Player.query.filter_by(name=p1_name).first()

                    if not p1_match:
                        p1_match = Player(
                            name=p1_name,
                            gender=category.gender or 'Male',
                            age_category=p1_cat or 'Open',
                            contact_number=p1_mobile or None,
                            email=participant_email if len(names) == 1 else None,
                            dob=p1_dob
                        )
                        db.session.add(p1_match)
                        db.session.flush()
                    else:
                        if p1_mobile and not p1_match.contact_number:
                            p1_match.contact_number = p1_mobile
                        if participant_email and len(names) == 1 and not p1_match.email:
                            p1_match.email = participant_email

                    player_id = p1_match.id
                    player2_id = None

                    # Process P2 if doubles
                    if is_doubles and p2_name:
                        p2_age = int(p2_age_str) if p2_age_str and p2_age_str.isdigit() else None
                        p2_dob = estimate_dob_from_age(p2_age)
                        p2_cat = determine_age_category(age=p2_age, dob=p2_dob) if p2_age else category.age_category

                        p2_match = None
                        if p2_mobile:
                            p2_match = Player.query.filter(Player.contact_number == p2_mobile).first()
                        if not p2_match:
                            p2_match = Player.query.filter_by(name=p2_name).first()

                        if not p2_match:
                            p2_match = Player(
                                name=p2_name,
                                gender=category.gender or 'Male',
                                age_category=p2_cat or 'Open',
                                contact_number=p2_mobile or None,
                                email=partner_email or None,
                                dob=p2_dob
                            )
                            db.session.add(p2_match)
                            db.session.flush()
                        else:
                            if p2_mobile and not p2_match.contact_number:
                                p2_match.contact_number = p2_mobile
                            if partner_email and not p2_match.email:
                                p2_match.email = partner_email

                        player2_id = p2_match.id
                        display_name = f"{p1_name} / {p2_name}"
                    else:
                        display_name = p1_name

                    team_role = None
                    if skill_tier == 'A':
                        team_role = 'captain'
                    elif skill_tier == 'B':
                        team_role = 'vice_captain'

                    participant = Participant(
                        tournament_id=tournament.id,
                        category_id=category.id,
                        player_id=player_id,
                        player2_id=player2_id,
                        name=display_name,
                        email=participant_email if len(names) == 1 else '',
                        mobile=p1_mobile if len(names) == 1 else '',
                        gender=category.gender,
                        dob=p1_dob,
                        partner_name=p2_name if player2_id else None,
                        partner_mobile=p2_mobile if player2_id else None,
                        manual_seed=manual_seed if (len(names) == 1 and category.format != 'group_stage') else None,
                        skill_tier=skill_tier if len(names) == 1 else None,
                        team_role=team_role if len(names) == 1 else None
                    )
                    db.session.add(participant)
                    added_names.append(display_name)

                db.session.commit()

                flash(f'Added participant(s): {", ".join(added_names)}', 'success')
                return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

            elif action == 'start_category':
                if tournament.status not in ['in_progress', 'completed']:
                    tournament.status = 'in_progress'
                    tournament.started_at = datetime.utcnow()
                    db.session.commit()
                
                start_single_category(category, tournament)
                flash('Category started! Bracket generated and matches automatically scheduled in Order of Play.', 'success')
                return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

            elif action == 'update_settings':
                name = request.form.get('name')
                max_participants = request.form.get('max_participants', type=int)
                total_games = request.form.get('total_games', type=int)
                points_to_win = request.form.get('points_to_win', type=int)
                scoring_format = request.form.get('scoring_format', 'games')
                max_players_per_team = request.form.get('max_players_per_team', type=int)
                
                # Group stage settings
                if category.format == 'group_stage':
                    category.num_groups = request.form.get('num_groups', type=int)
                    category.teams_per_group = request.form.get('teams_per_group', type=int)
                    category.matches_per_team_pair = request.form.get('matches_per_team_pair', type=int, default=1)
                    category.qualifiers_per_group = request.form.get('qualifiers_per_group', type=int, default=2)
                    category.allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on'
                elif category.format in ['round_robin', 'doubles_round_robin']:
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
                category.scoring_format = scoring_format
                category.points_to_win = points_to_win
                category.max_players_per_team = max_players_per_team
                category.entry_fee = request.form.get('entry_fee', type=float, default=0.0)
                
                # Scheduling fields (inherited globally from tournament if not specified)
                if request.form.get('num_courts'):
                    category.num_courts = request.form.get('num_courts', type=int)
                elif not category.num_courts:
                    category.num_courts = tournament.num_courts or 1

                if request.form.get('court_names'):
                    category.court_names = request.form.get('court_names')
                elif not category.court_names:
                    category.court_names = tournament.court_names or ''

                if request.form.get('avg_match_duration'):
                    category.avg_match_duration = request.form.get('avg_match_duration', type=int)
                elif not category.avg_match_duration:
                    category.avg_match_duration = tournament.avg_match_duration or 60

                if 'preferred_start_day' in request.form:
                    category.preferred_start_day = request.form.get('preferred_start_day', type=int, default=1)
                if 'pin_finals_to_last_day' in request.form:
                    category.pin_finals_to_last_day = request.form.get('pin_finals_to_last_day') == 'on'

                # Settings only editable in setup status
                if category.status == 'setup':
                    format_type = request.form.get('format')
                    if format_type == 'single_elimination':
                        sub_format = request.form.get('sub_format')
                        if sub_format == 'doubles':
                            format_type = 'doubles_elimination'
                    elif format_type == 'round_robin':
                        sub_format = request.form.get('sub_format')
                        if sub_format == 'doubles':
                            format_type = 'doubles_round_robin'
                    num_sets = request.form.get('num_sets', type=int, default=1)
                    games_per_set = request.form.get('games_per_set', type=int, default=6)
                    scoring_format = request.form.get('scoring_format', 'games')
                    total_games = request.form.get('total_games', type=int)
                    points_to_win = request.form.get('points_to_win', type=int)

                    category.format = format_type
                    category.num_sets = num_sets
                    category.games_per_set = games_per_set
                    category.scoring_format = scoring_format
                    if total_games is not None:
                        category.total_games = total_games
                    if points_to_win is not None:
                        category.points_to_win = points_to_win

                    category.has_group_stage = (format_type in ['group_stage', 'round_robin', 'doubles_round_robin'])
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
                    from app.services.utils.audit import log_audit
                    reason = request.form.get('audit_reason')
                    explanation = request.form.get('audit_explanation', '')
                    if not reason:
                        flash("Audit validation failed: Reason required to delete a participant.", "error")
                        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
                        
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
                return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

            elif action == 'reset_category':
                if category.status in ['in_progress', 'completed']:
                    from app.services.utils.audit import log_audit
                    reason = request.form.get('audit_reason')
                    explanation = request.form.get('audit_explanation', '')
                    if not reason:
                        flash("Audit validation failed: Reason required to reset a category.", "error")
                        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
                    if len(explanation.strip()) < 20:
                        flash("Audit validation failed: A detailed explanation (minimum 20 characters) is required for high-risk actions.", "error")
                        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
                        
                    log_audit(
                        action_type='reset_category',
                        target_id=category.id,
                        target_name=f"Category Bracket: {category.name}",
                        reason=reason,
                        explanation=explanation
                    )
                    
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

                from app.services.leaderboard import assign_leaderboard_points
                assign_leaderboard_points(category)

                flash('Tournament completed and points assigned to leaderboard! 🏆', 'success')
                return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to perform action: {str(e)}', 'error')
            return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

    solo_players = [p for p in participants if not p.is_team]
    teams = [p for p in participants if p.is_team]
    
    tiers_data = {'A': [], 'B': [], 'C': [], 'D': [], 'E': [], 'Unassigned': []}
    for p in solo_players:
        if p.skill_tier in tiers_data:
            tiers_data[p.skill_tier].append(p)
        else:
            tiers_data['Unassigned'].append(p)

    return render_template('category/manage.html',
                         tournament=tournament,
                         category=category,
                         participants=participants,
                         solo_players=solo_players,
                         teams=teams,
                         tiers_data=tiers_data,
                         formats=TOURNAMENT_FORMATS)

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/seeding', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def manage_seeding(slug, category_id):
    """Manage manual seeding for participants"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)
    if category.format == 'group_stage':
        flash('Individual player seeding is not required for team events.', 'info')
        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
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
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    if not category.has_group_stage:
        flash('This category does not have a group stage.', 'error')
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

    try:
        from app.services.format_engine.group_stage.logic import GroupStageFormat
        lucky_loser_ids = [int(x) for x in request.form.getlist('lucky_loser_ids') if str(x).isdigit()]
        matches_data = GroupStageFormat.generate_knockout_from_groups(
            category,
            selected_lucky_loser_ids=lucky_loser_ids if lucky_loser_ids else None
        )

        for match_data in matches_data:
            child_rubbers = match_data.pop('child_rubbers', None)
            if 'category_id' not in match_data:
                match_data['category_id'] = category.id
            match = Match(**match_data, tournament_id=tournament.id)
            db.session.add(match)
            db.session.flush()
            if child_rubbers:
                for r_data in child_rubbers:
                    r_data['parent_match_id'] = match.id
                    r_data['tournament_id'] = tournament.id
                    r_data['category_id'] = category.id
                    r_data['round'] = match.round
                    r_data['match_type'] = match.match_type
                    r_data['bracket_type'] = match.bracket_type
                    child_match = Match(**r_data)
                    db.session.add(child_match)

        db.session.commit()
        flash('Knockout stage started successfully with seeded 8-team draw!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to start knockout stage: {str(e)}', 'error')

    return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/rename', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def rename_category(slug, category_id):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)
    new_name = request.form.get('new_name')
    ok, clean_name = validate_name(new_name, min_len=2, max_len=80, field_name="Category Name")
    if not ok:
        flash(clean_name, "error")
    else:
        category.name = clean_name
        db.session.commit()
        flash(f"Category renamed to '{category.name}'", 'success')
    return redirect(request.referrer or url_for('tournament.manage_tournament', slug=slug))

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def delete_category(slug, category_id):
    """Delete a category and all its data"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)
    
    # Audit Validation
    from app.services.utils.audit import log_audit
    reason = request.form.get('audit_reason')
    explanation = request.form.get('audit_explanation', '')
    if not reason:
        flash("Audit validation failed: Reason required to delete a category.", "error")
        return redirect(request.referrer or url_for('tournament.view_tournament', slug=slug))
    if len(explanation.strip()) < 20:
        flash("Audit validation failed: A detailed explanation (minimum 20 characters) is required for high-risk actions.", "error")
        return redirect(request.referrer or url_for('tournament.view_tournament', slug=slug))
    
    try:
        from app.domain.models import Match, Group, Participant
        # Log Audit
        log_audit(
            action_type='delete_category',
            target_id=category.id,
            target_name=category.name,
            reason=reason,
            explanation=explanation
        )

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
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)
    match = Match.query.get_or_404(match_id)

    if category.status == 'upcoming':
        category.status = 'in_progress'
        category.started_at = datetime.utcnow()

    try:
        action = request.form.get('action')
        is_live_update = (action == 'live_score')
        winner_id = request.form.get('winner_id', type=int) if not is_live_update else None
        
        # Audit Validation if match was already completed
        if match.status == 'completed':
            from app.services.utils.audit import log_audit
            reason = request.form.get('audit_reason')
            explanation = request.form.get('audit_explanation', '')
            if not reason:
                flash("Audit validation failed: Reason required to modify a completed match.", "error")
                return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
            if len(explanation.strip()) < 20:
                flash("Audit validation failed: A detailed explanation (minimum 20 characters) is required for high-risk actions.", "error")
                return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
                
            log_audit(
                action_type='modify_match',
                target_id=match.id,
                target_name=f"Match {match.match_number} ({match.participant1.name if match.participant1 else 'TBD'} vs {match.participant2.name if match.participant2 else 'TBD'})",
                reason=reason,
                explanation=explanation
            )
        else:
            # Check Day-to-Day and Bracket progression
            from app.services.utils.scheduler import check_match_progression_allowed
            allowed, reason = check_match_progression_allowed(match)
            if not allowed:
                flash(f"Progression locked: {reason}", "error")
                return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

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
            
        # We need scoring configuration from match or category
        scoring_format = match.scoring_format or category.scoring_format or 'games'
        num_sets = match.num_sets or category.num_sets or 3
        games_per_set = match.games_per_set or category.games_per_set or 6
        points_to_win = match.points_to_win or category.points_to_win or 11

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
        is_7_games = (match.total_games == 7 or category.total_games == 7 or match.rubber_number is not None)
        if is_7_games:
            g1 = request.form.get('set1_p1', type=int)
            g2 = request.form.get('set1_p2', type=int)
            tb1 = request.form.get('tb1_p1', '')
            tb2 = request.form.get('tb1_p2', '')
            if g1 is None or g2 is None:
                if is_live_update:
                    g1 = g1 or 0
                    g2 = g2 or 0
                else:
                    raise ValueError("Scores for both players are required.")
            score1, score2, _, _, winner_idx = validate_total_7_games_score(
                g1, g2, tb1, tb2, is_live_update=is_live_update
            )
            if not is_live_update and winner_idx:
                winner_id = match.participant1_id if winner_idx == 1 else match.participant2_id
        elif scoring_format == 'points':
            p1_score = request.form.get('points_p1', type=int)
            p2_score = request.form.get('points_p2', type=int)
            
            if p1_score is None or p2_score is None:
                if is_live_update:
                    p1_score = p1_score or 0
                    p2_score = p2_score or 0
                else:
                    raise ValueError("Scores for both players are required.")

            if p1_score < 0 or p2_score < 0:
                raise ValueError("Scores cannot be negative.")

            if not is_live_update:
                if winner_id == match.participant1_id and p1_score <= p2_score:
                    raise ValueError("Winner must have a higher score.")
                if winner_id == match.participant2_id and p2_score <= p1_score:
                    raise ValueError("Winner must have a higher score.")
                    
                winning_score = max(p1_score, p2_score)
                losing_score = min(p1_score, p2_score)
                
                if winning_score < points_to_win:
                    raise ValueError(f"One player must reach {points_to_win} points to win.")
                    
                diff = winning_score - losing_score
                if diff < 2:
                    raise ValueError("A player must win by a difference of at least 2 points.")
                
                if winning_score > points_to_win and diff > 2:
                    raise ValueError(f"Invalid score. When extending past {points_to_win} points, the match ends as soon as a 2-point difference is reached.")
                
            score1 = str(p1_score)
            score2 = str(p2_score)
        else:
            score1, score2 = validate_and_format_score(
                winner_id, match.participant1_id, match.participant2_id,
                num_sets, games_per_set, form_data, is_live_update=is_live_update
            )

        match.score1 = score1
        match.score2 = score2
        
        if is_live_update:
            match.status = 'in_progress'
            db.session.commit()
            if match.parent_match_id:
                parent_tie = Match.query.get(match.parent_match_id)
                if parent_tie and parent_tie.status == 'pending':
                    parent_tie.status = 'in_progress'
                    db.session.commit()
            flash('Live score updated successfully.', 'success')
            return redirect(url_for('category.view_category', slug=slug, category_id=category.id))
            
        match.winner_id = winner_id
        match.status = 'completed'
        match.completed_at = datetime.utcnow()
        db.session.commit()

        # Update parent tie if this is a child rubber
        if match.parent_match_id:
            parent_tie = Match.query.get(match.parent_match_id)
            if parent_tie:
                rubbers = Match.query.filter_by(parent_match_id=parent_tie.id).all()
                p1_rubbers_won = sum(1 for r in rubbers if r.winner_id == parent_tie.participant1_id)
                p2_rubbers_won = sum(1 for r in rubbers if r.winner_id == parent_tie.participant2_id)
                parent_tie.score1 = str(p1_rubbers_won)
                parent_tie.score2 = str(p2_rubbers_won)
                
                all_completed = all(r.status == 'completed' for r in rubbers)
                if all_completed:
                    parent_tie.status = 'completed'
                    parent_tie.completed_at = datetime.utcnow()
                    parent_tie.winner_id = parent_tie.participant1_id if p1_rubbers_won > p2_rubbers_won else parent_tie.participant2_id
                    fmt = get_format(category.format)
                    if fmt and parent_tie.match_type == 'knockout':
                        fmt.advance_match(parent_tie, category, parent_tie.winner_id)
                elif any(r.status in ['in_progress', 'completed'] for r in rubbers):
                    parent_tie.status = 'in_progress'
                db.session.commit()

        from app.services.leaderboard import update_live_player_stats
        update_live_player_stats(match)

        fmt = get_format(category.format)
        if fmt and not match.parent_match_id:
            fmt.advance_match(match, category, winner_id)

        db.session.commit()
        
        # Recalculate group/round-robin stats
        if category.format in ['group_stage', 'round_robin', 'doubles_round_robin']:
            from app.services.leaderboard import recalculate_all_group_stats
            recalculate_all_group_stats(category.id)
            
        flash('Match result reported successfully!', 'success')
    except ValueError as ve:
        db.session.rollback()
        flash(f'Invalid Tennis Score: {str(ve)}', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to report match result: {str(e)}', 'error')

    return redirect(url_for('category.view_category', slug=slug, category_id=category_id))


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/grade-player', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def grade_player(slug, category_id):
    """Admin assigns skill tier (A, B, C, D, E) to participant(s)"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    Category.query.get_or_404(category_id)

    is_json = request.is_json
    data = request.get_json(silent=True) if is_json else request.form

    bulk_tiers = data.get('tiers') if isinstance(data, dict) else None
    if bulk_tiers and isinstance(bulk_tiers, dict):
        for p_id_str, t in bulk_tiers.items():
            t_clean = str(t).upper().strip()
            if t_clean in ['A', 'B', 'C', 'D', 'E']:
                p = Participant.query.filter_by(id=int(p_id_str), category_id=category_id).first()
                if p:
                    p.skill_tier = t_clean
        db.session.commit()
        if is_json:
            return jsonify({'success': True})
        flash('Player tiers updated successfully.', 'success')
        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

    participant_id = int(data.get('participant_id', 0))
    tier = (data.get('skill_tier') or '').upper().strip()
    if tier not in ['A', 'B', 'C', 'D', 'E']:
        msg = f"Invalid tier '{tier}'. Must be A, B, C, D, or E."
        if is_json:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

    p = Participant.query.filter_by(id=participant_id, category_id=category_id).first_or_404()
    p.skill_tier = tier
    db.session.commit()

    if is_json:
        return jsonify({'success': True, 'participant_id': p.id, 'skill_tier': p.skill_tier})
    flash(f'Player {p.name} assigned to Tier {tier}.', 'success')
    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/draft/setup-teams', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def draft_setup_teams(slug, category_id):
    """
    Sets up teams with appointed Captains (Tier A) and Vice-Captains (Tier B).
    """
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    num_teams = request.form.get('num_teams', type=int) or 4
    team_size = request.form.get('team_size', type=int) or category.team_size or 5
    category.team_size = team_size

    try:
        for i in range(1, num_teams + 1):
            t_name = request.form.get(f'team_{i}_name', f'Team {i}').strip() or f'Team {i}'
            captain_id = request.form.get(f'team_{i}_captain_id', type=int)
            vice_captain_id = request.form.get(f'team_{i}_vice_captain_id', type=int)

            team = Participant.query.filter_by(category_id=category_id, name=t_name, is_team=True).first()
            if not team:
                team = Participant(
                    category_id=category_id,
                    name=t_name,
                    is_team=True,
                    gender=category.gender
                )
                db.session.add(team)
                db.session.flush()

            if captain_id:
                cap = Participant.query.filter_by(id=captain_id, category_id=category_id).first()
                if cap:
                    cap.team_id = team.id
                    cap.team_role = 'captain'

            if vice_captain_id:
                vc = Participant.query.filter_by(id=vice_captain_id, category_id=category_id).first()
                if vc:
                    vc.team_id = team.id
                    vc.team_role = 'vice_captain'

        db.session.commit()
        flash('Teams with Captains and Vice-Captains configured successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to set up teams: {str(e)}', 'error')

    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/draft/assign-member', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def draft_assign_member(slug, category_id):
    """Assigns an unassigned player to a team squad (Drag & Drop or API)"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    data = request.get_json(silent=True) or request.form
    participant_id = int(data.get('participant_id', 0))
    team_id = int(data.get('team_id', 0))
    role = data.get('team_role', 'member')

    p = Participant.query.filter_by(id=participant_id, category_id=category_id).first_or_404()
    team = Participant.query.filter_by(id=team_id, category_id=category_id, is_team=True).first_or_404()

    current_count = Participant.query.filter_by(team_id=team.id).count()
    max_team_size = category.team_size or 5
    if current_count >= max_team_size and p.team_id != team.id:
        return jsonify({'success': False, 'error': f'{team.name} already has {max_team_size} players.'}), 400

    p.team_id = team.id
    p.team_role = role
    db.session.commit()

    return jsonify({
        'success': True,
        'participant_id': p.id,
        'participant_name': p.name,
        'team_id': team.id,
        'team_name': team.name,
        'team_role': p.team_role,
        'skill_tier': p.skill_tier
    })


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/draft/unassign-member', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def draft_unassign_member(slug, category_id):
    """Removes a player from team squad back to pool"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)

    data = request.get_json(silent=True) or request.form
    participant_id = int(data.get('participant_id', 0))

    p = Participant.query.filter_by(id=participant_id, category_id=category_id).first_or_404()
    p.team_id = None
    p.team_role = None
    db.session.commit()

    return jsonify({
        'success': True,
        'participant_id': p.id,
        'participant_name': p.name,
        'skill_tier': p.skill_tier
    })


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/draft/auto-ballot', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def draft_auto_ballot(slug, category_id):
    """
    Automates physical ballot draw by distributing unassigned players
    from Tier C, Tier D, Tier E equally across teams.
    """
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    teams = Participant.query.filter_by(category_id=category_id, is_team=True).order_by(Participant.id).all()
    if not teams:
        flash('Please setup teams first before running the draft ballot.', 'error')
        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

    for tier in ['C', 'D', 'E', None]:
        if tier:
            pool = Participant.query.filter_by(
                category_id=category_id, is_team=False, team_id=None, skill_tier=tier
            ).all()
        else:
            pool = Participant.query.filter_by(
                category_id=category_id, is_team=False, team_id=None
            ).all()
        
        random.shuffle(pool)
        for idx, player in enumerate(pool):
            target_team = teams[idx % len(teams)]
            current_count = Participant.query.filter_by(team_id=target_team.id).count()
            if current_count < (category.team_size or 5):
                player.team_id = target_team.id
                player.team_role = 'member'

    db.session.commit()
    flash('Ballot draw completed! Squads have been balanced across teams.', 'success')
    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/tie/<int:tie_id>/report', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def report_team_tie_result(slug, category_id, tie_id):
    """Report scores and lineups for all rubbers of a team tie"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)
    tie = Match.query.get_or_404(tie_id)

    is_json = request.is_json
    data = request.get_json(silent=True) if is_json else request.form

    action = data.get('action', 'complete')
    is_live = (action == 'live_score')

    try:
        rubbers = Match.query.filter_by(parent_match_id=tie.id).order_by(Match.rubber_number).all()
        if not rubbers:
            raise ValueError("No child rubbers found for this tie.")

        for r in rubbers:
            r_num = r.rubber_number or 1
            # Lineups
            p1_p1 = data.get(f'rubber_{r_num}_p1_p1', type=int) if hasattr(data, 'get') else None
            p1_p2 = data.get(f'rubber_{r_num}_p1_p2', type=int) if hasattr(data, 'get') else None
            p2_p1 = data.get(f'rubber_{r_num}_p2_p1', type=int) if hasattr(data, 'get') else None
            p2_p2 = data.get(f'rubber_{r_num}_p2_p2', type=int) if hasattr(data, 'get') else None

            def _resolve_pid(raw_val):
                if not raw_val:
                    return None
                try:
                    val_int = int(raw_val)
                except (ValueError, TypeError):
                    return None
                part = Participant.query.get(val_int)
                if part and part.player_id:
                    return part.player_id
                pl = Player.query.get(val_int)
                if pl:
                    return pl.id
                return None

            if p1_p1:
                r.lineup_p1_player_id = _resolve_pid(p1_p1)
            if p1_p2:
                r.lineup_p1_player2_id = _resolve_pid(p1_p2)
            if p2_p1:
                r.lineup_p2_player_id = _resolve_pid(p2_p1)
            if p2_p2:
                r.lineup_p2_player2_id = _resolve_pid(p2_p2)

            # Scores
            g1_val = data.get(f'rubber_{r_num}_g1')
            g2_val = data.get(f'rubber_{r_num}_g2')
            tb1_val = data.get(f'rubber_{r_num}_tb1', '')
            tb2_val = data.get(f'rubber_{r_num}_tb2', '')

            if g1_val is not None and str(g1_val).strip() != '' and g2_val is not None and str(g2_val).strip() != '':
                g1 = int(g1_val)
                g2 = int(g2_val)
                s1_str, s2_str, _, _, winner_idx = validate_total_7_games_score(
                    g1, g2, tb1_val, tb2_val, is_live_update=is_live
                )
                r.score1 = s1_str
                r.score2 = s2_str
                if is_live:
                    r.status = 'in_progress'
                else:
                    r.status = 'completed'
                    r.completed_at = datetime.utcnow()
                    if winner_idx == 1:
                        r.winner_id = tie.participant1_id
                    elif winner_idx == 2:
                        r.winner_id = tie.participant2_id

        # Tally rubbers won
        p1_won = sum(1 for r in rubbers if r.winner_id == tie.participant1_id)
        p2_won = sum(1 for r in rubbers if r.winner_id == tie.participant2_id)
        tie.score1 = str(p1_won)
        tie.score2 = str(p2_won)

        all_done = all(r.status == 'completed' for r in rubbers)
        if all_done:
            tie.status = 'completed'
            tie.completed_at = datetime.utcnow()
            tie.winner_id = tie.participant1_id if p1_won > p2_won else tie.participant2_id
            fmt = get_format(category.format)
            if fmt and tie.match_type == 'knockout':
                fmt.advance_match(tie, category, tie.winner_id)
        elif any(r.status in ['in_progress', 'completed'] for r in rubbers):
            tie.status = 'in_progress'

        db.session.commit()

        if category.format in ['group_stage', 'round_robin', 'doubles_round_robin']:
            from app.services.leaderboard import recalculate_all_group_stats
            recalculate_all_group_stats(category.id)

        if is_json:
            return jsonify({'success': True, 'tie_id': tie.id, 'score1': tie.score1, 'score2': tie.score2})
        flash('Team tie scores updated successfully!', 'success')
    except ValueError as ve:
        db.session.rollback()
        if is_json:
            return jsonify({'success': False, 'error': str(ve)}), 400
        flash(f'Invalid score: {str(ve)}', 'error')
    except Exception as e:
        db.session.rollback()
        if is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Error updating tie: {str(e)}', 'error')

    return redirect(url_for('category.view_category', slug=slug, category_id=category_id))


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/scoreboard')
def category_scoreboard(slug, category_id):
    """Fullscreen TV / Jumbotron Arena Scoreboard"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)

    from app.services.format_engine.group_stage.logic import GroupStageFormat
    groups = Group.query.filter_by(category_id=category_id).all()
    groups_data = []
    for g in groups:
        standings = GroupStageFormat.calculate_group_standings(g.id)
        ties = Match.query.options(
            db.joinedload(Match.participant1),
            db.joinedload(Match.participant2),
            db.joinedload(Match.sub_matches)
        ).filter(Match.group_id == g.id, Match.parent_match_id.is_(None)).order_by(Match.round, Match.match_number).all()
        groups_data.append({
            'group': g,
            'standings': standings,
            'ties': ties
        })

    # Knockout ties
    knockout_ties = Match.query.options(
        db.joinedload(Match.participant1),
        db.joinedload(Match.participant2),
        db.joinedload(Match.sub_matches)
    ).filter(
        Match.category_id == category_id,
        Match.match_type == 'knockout',
        Match.parent_match_id.is_(None)
    ).order_by(Match.round, Match.match_number).all()

    all_ties = [t for g in groups_data for t in g['ties']] + knockout_ties
    active_tie = next((t for t in all_ties if t.status == 'in_progress'), None)
    if not active_tie:
        active_tie = next((t for t in all_ties if t.status == 'pending'), None)
    if not active_tie and all_ties:
        active_tie = all_ties[-1]

    return render_template('category/scoreboard.html',
                         tournament=tournament,
                         category=category,
                         groups_data=groups_data,
                         knockout_ties=knockout_ties,
                         active_tie=active_tie)


@category_bp.route('/api/categories/<int:category_id>/live-scoreboard')
def category_live_scoreboard_api(category_id):
    """Live JSON endpoint for real-time scoreboard client polling"""
    category = Category.query.get_or_404(category_id)

    from app.services.format_engine.group_stage.logic import GroupStageFormat
    groups = Group.query.filter_by(category_id=category_id).all()
    groups_payload = []
    qualifiers_per_group = category.qualifiers_per_group or 2

    for g in groups:
        standings = GroupStageFormat.calculate_group_standings(g.id)
        ties = Match.query.options(
            db.joinedload(Match.participant1),
            db.joinedload(Match.participant2),
            db.joinedload(Match.sub_matches)
        ).filter(Match.group_id == g.id, Match.parent_match_id.is_(None)).order_by(Match.round, Match.match_number).all()

        ties_payload = []
        for t in ties:
            rubbers_payload = []
            for r in (t.sub_matches or []):
                p1_members = []
                if r.lineup_p1_player:
                    p1_members.append(r.lineup_p1_player.name)
                if r.lineup_p1_player2:
                    p1_members.append(r.lineup_p1_player2.name)
                p2_members = []
                if r.lineup_p2_player:
                    p2_members.append(r.lineup_p2_player.name)
                if r.lineup_p2_player2:
                    p2_members.append(r.lineup_p2_player2.name)

                rubbers_payload.append({
                    'id': r.id,
                    'rubber_number': r.rubber_number,
                    'rubber_type': r.rubber_type,
                    'status': r.status,
                    'score1': r.score1 or '-',
                    'score2': r.score2 or '-',
                    'winner_id': r.winner_id,
                    'court': r.court_number or '',
                    'p1_lineup': " / ".join(p1_members) if p1_members else (t.participant1.name if t.participant1 else 'TBD'),
                    'p2_lineup': " / ".join(p2_members) if p2_members else (t.participant2.name if t.participant2 else 'TBD')
                })

            ties_payload.append({
                'id': t.id,
                'round': t.round,
                'match_number': t.match_number,
                'status': t.status,
                'court': t.court_number or '',
                'team1': {'id': t.participant1_id, 'name': t.participant1.name if t.participant1 else 'TBD'},
                'team2': {'id': t.participant2_id, 'name': t.participant2.name if t.participant2 else 'TBD'},
                'score1': t.score1 or '0',
                'score2': t.score2 or '0',
                'winner_id': t.winner_id,
                'rubbers': rubbers_payload
            })

        standings_payload = []
        for idx, p in enumerate(standings):
            standings_payload.append({
                'rank': idx + 1,
                'id': p.id,
                'name': p.name,
                'group_wins': getattr(p, 'group_wins', 0),
                'group_losses': getattr(p, 'group_losses', 0),
                'group_points': getattr(p, 'group_points', 0),
                'rubbers_won': getattr(p, 'rubbers_won', 0),
                'rubbers_lost': getattr(p, 'rubbers_lost', 0),
                'is_qualified': idx < qualifiers_per_group
            })

        groups_payload.append({
            'id': g.id,
            'name': g.name,
            'standings': standings_payload,
            'ties': ties_payload
        })

    return jsonify({
        'category': {
            'id': category.id,
            'name': category.name,
            'status': category.status,
            'format': category.format
        },
        'groups': groups_payload,
        'timestamp': datetime.utcnow().isoformat()
    })


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/update_grid', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def update_grid_scores(slug, category_id):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)
    
    if category.status == 'upcoming':
        category.status = 'in_progress'
        category.started_at = datetime.utcnow()
        # Will commit at the end
    
    from app.domain.models import Match
    
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
                        v_int = int(value)
                        if v_int >= 0:
                            match_updates[match_id][player_idx] = v_int
                        else:
                            continue
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
            match.score1 = str(score1)
            match.score2 = str(score2)
            
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
    from app.services.leaderboard import recalculate_all_group_stats
    recalculate_all_group_stats(category.id)

    # Check if category is finished
    if check_category_auto_completion(category):
        category.status = 'completed'
        category.completed_at = datetime.utcnow()
        if category.format in ['round_robin', 'doubles_round_robin'] and (not category.qualifiers_per_group or category.qualifiers_per_group == 0):
            from app.services.leaderboard import calculate_combined_round_robin_standings
            calculate_combined_round_robin_standings(category.id)
        db.session.commit()
        from app.services.leaderboard import assign_leaderboard_points
        assign_leaderboard_points(category)
    
    flash(f'Successfully updated {updated_count} matches.', 'success')
    return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
