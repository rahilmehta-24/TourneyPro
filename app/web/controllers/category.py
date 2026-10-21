from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.domain.models import db, Tournament, Category, Participant, Match, Group, Player, PlayerCategoryTier, TeamMember, determine_age_category, estimate_dob_from_age
from app.core.constants import TOURNAMENT_FORMATS
from app.services.format_engine import get_format
from app.web.controllers.auth import login_required, role_required, check_tournament_ownership
from app.services.tennis_logic import validate_and_format_score
from datetime import datetime
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
                sub_rubbers = match_data.pop('sub_matches', None)
                match_data['match_type'] = 'round_robin'
                match = Match(**match_data, tournament_id=tournament.id)
                db.session.add(match)
                if sub_rubbers:
                    db.session.flush()
                    for s_data in sub_rubbers:
                        s_data['parent_match_id'] = match.id
                        s_data['category_id'] = category.id
                        s_data['match_type'] = 'round_robin'
                        s_match = Match(**s_data, tournament_id=tournament.id)
                        db.session.add(s_match)
        else:
            matches_data = fmt.generate(category, participants_list)
            for match_data in matches_data:
                sub_rubbers = match_data.pop('sub_matches', None)
                if 'category_id' not in match_data:
                    match_data['category_id'] = category.id
                match = Match(**match_data, tournament_id=tournament.id)
                db.session.add(match)
                if sub_rubbers:
                    db.session.flush()
                    for s_data in sub_rubbers:
                        s_data['parent_match_id'] = match.id
                        s_data['category_id'] = category.id
                        s_match = Match(**s_data, tournament_id=tournament.id)
                        db.session.add(s_match)

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
        gender = request.form.get('gender', 'Unspecified')
        age_category = request.form.get('age_category', 'Unspecified')

        # Tennis settings
        scoring_format = request.form.get('scoring_format', 'games')
        num_sets = request.form.get('num_sets', type=int)
        games_per_set = request.form.get('games_per_set', type=int)
        total_games = request.form.get('total_games', type=int)
        points_to_win = request.form.get('points_to_win', type=int)

        # Advanced settings for group stage
        has_group_stage = (format_type in ['group_stage', 'round_robin', 'doubles_round_robin'])
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
        db.joinedload(Match.winner)
    ).filter_by(category_id=category_id).order_by(Match.round, Match.match_number).all()

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
        from app.services.format_engine.group_stage.logic import GroupStageFormat
        groups = Group.query.filter_by(category_id=category_id).all()
        groups_data = []
        for group in groups:
            standings = GroupStageFormat.calculate_group_standings(group.id)
            group_matches = Match.query.options(
                db.joinedload(Match.participant1),
                db.joinedload(Match.participant2),
                db.joinedload(Match.winner),
                db.joinedload(Match.sub_matches)
            ).filter(
                Match.group_id == group.id,
                Match.parent_match_id.is_(None),
                Match.match_type.in_(['group_stage', 'round_robin', 'doubles_round_robin'])
            ).order_by(Match.round, Match.match_number).all()
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
            if category.format in ['round_robin', 'doubles_round_robin']:
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
    
    if category.status == 'setup' and not rr_matches and category.format in ['round_robin', 'doubles_round_robin'] and not category.num_groups:
        rr_matches = [DummyMatch(**d) for d in dummy_data]
    
    is_export = request.args.get('export') == '1'
    winners = get_category_winners(category) if is_export else []
    team_rosters_map = {}
    if category.has_group_stage or category.format in ['round_robin', 'doubles_round_robin']:
        all_players = Player.query.all()
        for p in participants:
            if hasattr(p, 'team_members') and p.team_members:
                sorted_m = sorted(p.team_members, key=lambda m: m.roster_order or 99)
                team_rosters_map[p.id] = [
                    {
                        'id': m.player_id,
                        'name': m.player.name if m.player else f"Player #{m.player_id}",
                        'role': m.role or 'member',
                        'tier': m.tier or ''
                    }
                    for m in sorted_m
                ]
            else:
                team_rosters_map[p.id] = [
                    {
                        'id': pl.id,
                        'name': pl.name,
                        'role': 'player',
                        'tier': ''
                    }
                    for pl in all_players
                ]

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
                         rankings=rankings,
                         team_rosters_map=team_rosters_map,
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
    participants = Participant.query.filter_by(category_id=category_id).order_by(Participant.manual_seed, Participant.seed).all()

    if request.method == 'POST':
        action = request.form.get('action')

        try:
            if action == 'add_participant':
                participant_name = request.form.get('participant_name', '').strip()
                participant_age_str = request.form.get('participant_age', '').strip()
                participant_mobile = request.form.get('participant_mobile', '').strip()
                participant_email = request.form.get('participant_email', '').strip()
                manual_seed = request.form.get('manual_seed', type=int)

                partner_name = request.form.get('partner_name', '').strip()
                partner_age_str = request.form.get('partner_age', '').strip()
                partner_mobile = request.form.get('partner_mobile', '').strip()
                partner_email = request.form.get('partner_email', '').strip()

                if not participant_name:
                    flash('Participant name is required.', 'error')
                    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

                if manual_seed is not None and manual_seed < 1:
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
                        manual_seed=manual_seed if len(names) == 1 else None
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

                    category.format = format_type
                    category.num_sets = num_sets
                    category.games_per_set = games_per_set

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
    check_tournament_ownership(tournament)
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
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    if not category.has_group_stage:
        flash('This category does not have a group stage.', 'error')
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

    try:
        # Generate knockout bracket from group qualifiers
        from app.services.format_engine.group_stage.logic import GroupStageFormat
        matches_data = GroupStageFormat.generate_knockout_from_groups(category)

        for match_data in matches_data:
            sub_rubbers = match_data.pop('sub_matches', None)
            match = Match(**match_data, tournament_id=tournament.id)
            db.session.add(match)
            if sub_rubbers:
                db.session.flush()
                for s_data in sub_rubbers:
                    s_data['parent_match_id'] = match.id
                    s_data['category_id'] = category.id
                    s_match = Match(**s_data, tournament_id=tournament.id)
                    db.session.add(s_match)

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
            reason = request.form.get('audit_reason') or "Score Entry Mistake"
            explanation = request.form.get('audit_explanation', '')
            if not explanation or len(explanation.strip()) < 20:
                explanation = "Score modification submitted by tournament administrator."
                
            p1_label = match.participant1.name if match.participant1 else (match.p1_player1.name if getattr(match, 'p1_player1', None) else 'TBD')
            p2_label = match.participant2.name if match.participant2 else (match.p2_player1.name if getattr(match, 'p2_player1', None) else 'TBD')
            match_num = match.match_number or match.rubber_number or match.id

            log_audit(
                action_type='modify_match',
                target_id=match.id,
                target_name=f"Match {match_num} ({p1_label} vs {p2_label})",
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
        if match.parent_match_id or getattr(match, 'rubber_type', None) or (category and category.format == 'group_stage' and category.total_games and scoring_format == 'games'):
            from app.services.tennis_logic import validate_team_rubber_score
            p1_games = request.form.get('set1_p1') or request.form.get('points_p1')
            p2_games = request.form.get('set1_p2') or request.form.get('points_p2')
            p1_tb = request.form.get('tb1_p1')
            p2_tb = request.form.get('tb1_p2')

            # Update rubber lineup if provided in the modal
            if request.form.get('p1_player1_id'):
                match.p1_player1_id = request.form.get('p1_player1_id', type=int)
            if request.form.get('p1_player2_id'):
                match.p1_player2_id = request.form.get('p1_player2_id', type=int)
            if request.form.get('p2_player1_id'):
                match.p2_player1_id = request.form.get('p2_player1_id', type=int)
            if request.form.get('p2_player2_id'):
                match.p2_player2_id = request.form.get('p2_player2_id', type=int)

            score1, score2, winner_ind = validate_team_rubber_score(
                p1_games=p1_games,
                p2_games=p2_games,
                p1_tb_pts=p1_tb,
                p2_tb_pts=p2_tb,
                total_games=category.total_games or 7,
                is_live_update=is_live_update
            )
            if not is_live_update and winner_ind:
                actual_winner_id = match.participant1_id if winner_ind == 1 else match.participant2_id
                if winner_id and winner_id != actual_winner_id:
                    raise ValueError("The selected winner does not match the rubber scores.")
                winner_id = actual_winner_id
        elif scoring_format == 'points' or (category and category.format in ['round_robin', 'doubles_round_robin'] and scoring_format != 'games'):
            if scoring_format == 'points':
                p1_score = request.form.get('points_p1', type=int)
                p2_score = request.form.get('points_p2', type=int)
            else:
                p1_score = request.form.get('set1_p1', type=int)
                p2_score = request.form.get('set1_p2', type=int)
            
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
                
                # If extending past points_to_win (e.g. 12-10 in an 11-point game), diff must be exactly 2
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
            flash('Live score updated successfully.', 'success')
            return redirect(url_for('category.view_category', slug=slug, category_id=category.id))
            
        match.winner_id = winner_id
        match.status = 'completed'
        match.completed_at = datetime.utcnow()
        db.session.commit()

        from app.services.leaderboard import update_live_player_stats
        update_live_player_stats(match)

        # Stats will be recalculated at the end

        fmt = get_format(category.format)
        if fmt:
            fmt.advance_match(match, category, winner_id)

        # Auto-completion removed. Admin must click Finish Tournament.

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


@category_bp.route('/t/<slug>/categories/<int:category_id>/fixtures/<int:fixture_id>/lineup', methods=['POST'])
@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/fixtures/<int:fixture_id>/lineup', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def allot_fixture_lineup(slug, category_id, fixture_id):
    """
    Allot official team match lineup based on captains' submitted nomination slips.
    - Rubber 1: Singles (Team 1 Player vs Team 2 Player)
    - Rubber 2: Doubles 1 (Team 1 Pair vs Team 2 Pair)
    - Rubber 3: Doubles 2 (Team 1 Pair vs Team 2 Pair)
    """
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    fixture = Match.query.get_or_404(fixture_id)

    if fixture.tournament_id != tournament.id or fixture.category_id != category.id:
        flash("Invalid fixture or category.", "error")
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

    # Read rubber submissions
    r1_p1 = request.form.get('r1_p1_player1', type=int)
    r1_p2 = request.form.get('r1_p2_player1', type=int)

    r2_p1_1 = request.form.get('r2_p1_player1', type=int)
    r2_p1_2 = request.form.get('r2_p1_player2', type=int)
    r2_p2_1 = request.form.get('r2_p2_player1', type=int)
    r2_p2_2 = request.form.get('r2_p2_player2', type=int)

    r3_p1_1 = request.form.get('r3_p1_player1', type=int)
    r3_p1_2 = request.form.get('r3_p1_player2', type=int)
    r3_p2_1 = request.form.get('r3_p2_player1', type=int)
    r3_p2_2 = request.form.get('r3_p2_player2', type=int)

    sub_matches = sorted(fixture.sub_matches, key=lambda m: m.rubber_number or 1)
    r_singles = next((r for r in sub_matches if r.rubber_type == 'singles' or r.rubber_number == 1), None)
    r_doubles_1 = next((r for r in sub_matches if r.rubber_type == 'doubles_1' or r.rubber_number == 2), None)
    r_doubles_2 = next((r for r in sub_matches if r.rubber_type == 'doubles_2' or r.rubber_number == 3), None)

    if r_singles:
        r_singles.p1_player1_id = r1_p1
        r_singles.p2_player1_id = r1_p2
    if r_doubles_1:
        r_doubles_1.p1_player1_id = r2_p1_1
        r_doubles_1.p1_player2_id = r2_p1_2
        r_doubles_1.p2_player1_id = r2_p2_1
        r_doubles_1.p2_player2_id = r2_p2_2
    if r_doubles_2:
        r_doubles_2.p1_player1_id = r3_p1_1
        r_doubles_2.p1_player2_id = r3_p1_2
        r_doubles_2.p2_player1_id = r3_p2_1
        r_doubles_2.p2_player2_id = r3_p2_2

    try:
        from app.services.utils.audit import log_audit
        db.session.commit()
        log_audit(
            action_type='ALLOT_LINEUP',
            target_id=fixture.id,
            target_name=f"{fixture.participant1.name if fixture.participant1 else 'T1'} vs {fixture.participant2.name if fixture.participant2 else 'T2'}",
            reason="Captains match lineup allotted",
            details={
                'fixture_id': fixture.id,
                'category_id': category.id,
                'r1': {'p1': r1_p1, 'p2': r1_p2},
                'r2': {'p1': [r2_p1_1, r2_p1_2], 'p2': [r2_p2_1, r2_p2_2]},
                'r3': {'p1': [r3_p1_1, r3_p1_2], 'p2': [r3_p2_1, r3_p2_2]}
            }
        )
        flash("Official match lineup allotted successfully based on captains' nominations!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error saving lineup: {str(e)}", "error")

    return redirect(url_for('category.view_category', slug=slug, category_id=category_id) + f"#fixture-{fixture.id}")


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


# =========================================================================
# GROUP STAGE TEAM LEAGUE: TIERS, BALLOT CHIT DRAFT, AND AUTO-TEAMS
# =========================================================================

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/draft', methods=['GET'])
@login_required
@role_required('admin', 'superadmin')
def team_draft_view(slug, category_id):
    """
    Main Draft Board for Team League categories:
    1. Organize registered players into 5 Skill Tiers (Tier A Captains, Tier B VCs, C, D, E).
    2. Mode A: Manual Paper Chit Draw selection.
    3. Mode B: 1-Click Auto-Draft Balanced Teams.
    4. Group Session Start Timings & Courts configuration.
    """
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    # Ensure default group count is set
    num_groups = category.num_groups or 2
    existing_groups = Group.query.filter_by(category_id=category.id).order_by(Group.id).all()
    if not existing_groups:
        for i in range(num_groups):
            g = Group(category_id=category.id, name=f"Group {chr(65 + i)}")
            db.session.add(g)
        db.session.commit()
        existing_groups = Group.query.filter_by(category_id=category.id).order_by(Group.id).all()

    # Discover all registered players for this category
    from app.domain.models import Registration
    tier_records = PlayerCategoryTier.query.filter_by(category_id=category.id).all()
    tiered_player_ids = {t.player_id for t in tier_records}

    # Fetch individual participants (not teams) to populate unassigned pool
    participants = Participant.query.filter_by(category_id=category.id).all()
    unassigned_players = []
    
    for p in participants:
        # If participant is not already a team (has no team_members) and not tiered yet
        if not p.team_members and p.player_id and p.player_id not in tiered_player_ids:
            player_obj = Player.query.get(p.player_id)
            if player_obj and player_obj not in unassigned_players:
                unassigned_players.append(player_obj)

    # Also discover from approved registrations
    registrations = Registration.query.filter_by(category_id=category.id, status='approved').all()
    for reg in registrations:
        if reg.player_id and reg.player_id not in tiered_player_ids:
            player_obj = Player.query.get(reg.player_id)
            if player_obj and player_obj not in unassigned_players:
                unassigned_players.append(player_obj)

    # Group existing tiers into buckets
    tiers_map = {'A': [], 'B': [], 'C': [], 'D': [], 'E': []}
    for tr in tier_records:
        if tr.tier in tiers_map:
            tiers_map[tr.tier].append(tr)

    # Fetch existing formed teams (participants having team_members)
    teams = [p for p in participants if p.team_members]

    k = category.max_players_per_team or 5
    total_players = len(tier_records) + len(unassigned_players)
    calculated_teams = max(2, total_players // k) if total_players >= k else 2
    teams_per_group = max(1, calculated_teams // num_groups)

    return render_template(
        'category/team_draft.html',
        tournament=tournament,
        category=category,
        groups=existing_groups,
        unassigned_players=unassigned_players,
        tiers_map=tiers_map,
        teams=teams,
        total_players=total_players,
        players_per_team=k,
        calculated_teams=calculated_teams,
        teams_per_group=teams_per_group,
        num_groups=num_groups
    )


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/tiers/assign', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def assign_player_tiers(slug, category_id):
    """
    Save or update player skill tier assignments (A, B, C, D, E).
    Accepts JSON payload: [{'player_id': 1, 'tier': 'A', 'role': 'captain'}, ...]
    or form fields: player_tier_<id> = 'A'
    """
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    try:
        assignments = []
        if request.is_json:
            assignments = request.json.get('assignments', [])
        else:
            for key, val in request.form.items():
                if key.startswith('tier_') and val in ['A', 'B', 'C', 'D', 'E']:
                    pid = int(key.replace('tier_', ''))
                    role = 'captain' if val == 'A' else ('vice_captain' if val == 'B' else 'player')
                    assignments.append({'player_id': pid, 'tier': val, 'role': role})

        if not assignments:
            raise ValueError("No tier assignments provided.")

        for item in assignments:
            pid = int(item['player_id'])
            tier = item['tier'].strip().upper()
            role = item.get('role', 'captain' if tier == 'A' else ('vice_captain' if tier == 'B' else 'player'))

            tier_obj = PlayerCategoryTier.query.filter_by(category_id=category.id, player_id=pid).first()
            if not tier_obj:
                tier_obj = PlayerCategoryTier(
                    category_id=category.id,
                    player_id=pid,
                    tier=tier,
                    role=role
                )
                db.session.add(tier_obj)
            else:
                tier_obj.tier = tier
                tier_obj.role = role

        db.session.commit()
        if request.is_json:
            return jsonify({'success': True, 'message': 'Player tiers updated successfully!'})
        flash('Player skill tiers updated successfully!', 'success')
        return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        flash(f'Failed to assign player tiers: {str(e)}', 'error')
        return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/teams/auto-create', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def auto_create_teams_endpoint(slug, category_id):
    """
    Mode B: 🎲 Automatic 1-Click Team Creation.
    Draws 1 player from Tier A (Captain), 1 from Tier B (VC), and 1 from Tiers C, D, E per team.
    """
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    try:
        from app.services.format_engine.group_stage.logic import GroupStageFormat
        created_teams = GroupStageFormat.auto_create_teams(category.id)
        msg = f'Successfully auto-created {len(created_teams)} balanced teams from player tiers!'
        if request.is_json:
            return jsonify({'success': True, 'message': msg, 'team_count': len(created_teams)})
        flash(msg, 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        flash(f'Auto-creation failed: {str(e)}', 'error')

    return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/teams/create-manual', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def create_manual_teams(slug, category_id):
    """
    Mode A: Manual Paper Chit Draw selection.
    Captains & VCs selected, then as paper chits are drawn, players for C, D, E are chosen.
    Prevents duplicate player assignment across teams.
    """
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    try:
        data = request.get_json(silent=True) or request.form
        teams_payload = []
        if isinstance(data, dict) and 'teams' in data:
            teams_payload = data['teams']
        else:
            num_teams = int(request.form.get('num_teams', 0))
            for i in range(1, num_teams + 1):
                t_name = request.form.get(f'team_{i}_name', f'Team {i}').strip() or f'Team {i}'
                c_id = request.form.get(f'team_{i}_captain', type=int)
                vc_id = request.form.get(f'team_{i}_vc', type=int)
                mc_id = request.form.get(f'team_{i}_c', type=int)
                md_id = request.form.get(f'team_{i}_d', type=int)
                me_id = request.form.get(f'team_{i}_e', type=int)
                teams_payload.append({
                    'name': t_name,
                    'captain_id': c_id,
                    'vc_id': vc_id,
                    'member_c_id': mc_id,
                    'member_d_id': md_id,
                    'member_e_id': me_id
                })

        if not teams_payload:
            raise ValueError("No teams data submitted.")

        # Duplicate player validation across all teams
        all_selected_players = []
        for t in teams_payload:
            p_ids = [t.get('captain_id'), t.get('vc_id'), t.get('member_c_id'), t.get('member_d_id'), t.get('member_e_id')]
            p_ids = [pid for pid in p_ids if pid is not None]
            for pid in p_ids:
                if pid in all_selected_players:
                    player_obj = Player.query.get(pid)
                    p_name = player_obj.name if player_obj else f"Player #{pid}"
                    raise ValueError(f"Duplicate player detected: '{p_name}' is assigned to multiple teams.")
                all_selected_players.append(pid)

        # Clear existing team participants in setup mode
        existing_teams = Participant.query.filter_by(category_id=category_id).all()
        for p in existing_teams:
            db.session.delete(p)
        db.session.flush()

        # Reset draft status on tiers
        tiers = PlayerCategoryTier.query.filter_by(category_id=category_id).all()
        for t in tiers:
            t.is_drafted = False
            t.role = 'player'

        created_teams = []
        for idx, t in enumerate(teams_payload, start=1):
            team_name = t.get('name') or f"Team {idx}"
            captain_id = t.get('captain_id')
            vc_id = t.get('vc_id')
            c_id = t.get('member_c_id')
            d_id = t.get('member_d_id')
            e_id = t.get('member_e_id')

            if not captain_id:
                raise ValueError(f"'{team_name}' must have a Captain assigned.")

            team_p = Participant(
                tournament_id=tournament.id,
                category_id=category.id,
                name=team_name,
                player_id=captain_id
            )
            db.session.add(team_p)
            db.session.flush()

            roster = [
                (captain_id, 'captain', 'A', 1),
                (vc_id, 'vice_captain', 'B', 2),
                (c_id, 'member', 'C', 3),
                (d_id, 'member', 'D', 4),
                (e_id, 'member', 'E', 5),
            ]

            for pid, role, tier_let, order in roster:
                if pid:
                    db.session.add(TeamMember(
                        participant_id=team_p.id,
                        player_id=pid,
                        role=role,
                        tier=tier_let,
                        roster_order=order
                    ))
                    p_tier = PlayerCategoryTier.query.filter_by(category_id=category_id, player_id=pid).first()
                    if p_tier:
                        p_tier.is_drafted = True
                        p_tier.role = role

            created_teams.append(team_p)

        db.session.commit()
        msg = f'Successfully formed {len(created_teams)} teams via Ballot Chit Draw!'
        if request.is_json:
            return jsonify({'success': True, 'message': msg})
        flash(msg, 'success')
        return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        flash(f'Failed to create teams: {str(e)}', 'error')
        return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/teams/reset', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def reset_teams(slug, category_id):
    """Reset teams and allow re-drafting before matches start."""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    if category.status != 'setup':
        flash('Cannot reset teams once matches are in progress.', 'error')
        return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))

    try:
        teams = Participant.query.filter_by(category_id=category_id).all()
        for t in teams:
            db.session.delete(t)

        tiers = PlayerCategoryTier.query.filter_by(category_id=category_id).all()
        for tr in tiers:
            tr.is_drafted = False
            tr.role = 'player'

        db.session.commit()
        flash('Teams cleared. You can now re-draft teams manually or auto-create.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to reset teams: {str(e)}', 'error')

    return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/groups/timings', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def update_group_timings(slug, category_id):
    """Update group session start timings and assigned courts."""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    try:
        groups = Group.query.filter_by(category_id=category_id).all()
        for g in groups:
            start_t = request.form.get(f'start_time_{g.id}', '').strip()
            courts_str = request.form.get(f'assigned_courts_{g.id}', '').strip()
            g.start_time = start_t or None
            g.assigned_courts = courts_str or None

        db.session.commit()
        flash('Group session timings and court assignments saved!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to update group timings: {str(e)}', 'error')

    return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))

