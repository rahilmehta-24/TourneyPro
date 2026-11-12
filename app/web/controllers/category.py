from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.domain.models import db, Tournament, Category, Participant, Match, Group, Player, PlayerCategoryTier, TeamMember, determine_age_category, estimate_dob_from_age
from app.core.constants import TOURNAMENT_FORMATS
from app.services.format_engine import get_format
from app.web.controllers.auth import (
    login_required,
    role_required,
    check_tournament_ownership,
    check_tournament_access,
    check_scoring_conflict_of_interest,
    check_fixture_lineup_access,
    get_current_user,
)
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


def _extract_category_scoring_config(format_type, form):
    """Extract format-isolated scoring configuration for a category."""
    if format_type == 'group_stage':
        raw_total = form.get('total_games', type=int)
        return {
            'scoring_format': 'games',
            'num_sets': None,
            'games_per_set': None,
            'total_games': raw_total if raw_total is not None else 7,
            'points_to_win': None,
            'max_players_per_team': form.get('max_players_per_team', type=int),
        }

    scoring_format = form.get('scoring_format') or 'games'
    if scoring_format not in ('games', 'points'):
        scoring_format = 'games'

    if scoring_format == 'points':
        raw_points = form.get('points_to_win', type=int)
        return {
            'scoring_format': 'points',
            'num_sets': None,
            'games_per_set': None,
            'total_games': None,
            'points_to_win': raw_points if raw_points is not None else 11,
            'max_players_per_team': None,
        }

    return {
        'scoring_format': 'games',
        'num_sets': form.get('num_sets', type=int) or 3,
        'games_per_set': form.get('games_per_set', type=int) or 6,
        'total_games': None,
        'points_to_win': None,
        'max_players_per_team': None,
    }


def _sync_category_groups(category, target_num_groups, rebalance_participants=False):
    """Ensure Group A..Group N exist for `category` and optionally re-seed participants."""
    from app.services.format_engine.group_stage.logic import GroupStageFormat

    target_num_groups = max(2, min(16, int(target_num_groups or 2)))
    existing_groups = Group.query.filter_by(category_id=category.id).order_by(Group.id).all()
    synced_groups = []

    for i in range(target_num_groups):
        g_name = f"Group {chr(65 + i)}"
        matched = next((g for g in existing_groups if g.name == g_name), None)
        if matched:
            synced_groups.append(matched)
        else:
            new_g = Group(category_id=category.id, name=g_name)
            db.session.add(new_g)
            db.session.flush()
            synced_groups.append(new_g)

    valid_ids = {g.id for g in synced_groups}
    category_participants = Participant.query.filter_by(category_id=category.id).all()

    # Clear participant references to removed groups before deleting excess Group rows
    for eg in existing_groups:
        if eg.id not in valid_ids:
            for p in category_participants:
                if p.group_id == eg.id:
                    p.group_id = None
            db.session.delete(eg)
    db.session.flush()

    if rebalance_participants:
        # In team leagues, only assign formed teams; in singles/doubles assign all participants
        is_team_event = bool(category.max_players_per_team and category.max_players_per_team > 1)
        assignable = [p for p in category_participants if p.team_members] if is_team_event else category_participants
        for p in assignable:
            p.group_id = None
        if assignable:
            GroupStageFormat._assign_groups_snake(assignable, synced_groups, teams_per_group=category.teams_per_group)

    return synced_groups


def _collect_draft_pool(category):
    """Return (tier_records, unassigned_players, teams, total_players) for Team Draft views."""
    from app.domain.models import Registration

    tier_records = PlayerCategoryTier.query.filter_by(category_id=category.id).all()
    tiered_player_ids = {t.player_id for t in tier_records}
    participants = Participant.query.filter_by(category_id=category.id).all()

    unassigned_players = []
    seen_unassigned_ids = set()

    for p in participants:
        if not p.team_members and p.player_id and p.player_id not in tiered_player_ids and p.player_id not in seen_unassigned_ids:
            player_obj = Player.query.get(p.player_id)
            if player_obj:
                unassigned_players.append(player_obj)
                seen_unassigned_ids.add(player_obj.id)

    registrations = Registration.query.filter_by(category_id=category.id, status='approved').all()
    for reg in registrations:
        if reg.player_id and reg.player_id not in tiered_player_ids and reg.player_id not in seen_unassigned_ids:
            player_obj = Player.query.get(reg.player_id)
            if player_obj:
                unassigned_players.append(player_obj)
                seen_unassigned_ids.add(player_obj.id)

    teams = [p for p in participants if p.team_members]
    total_players = len(tier_records) + len(unassigned_players)
    return tier_records, unassigned_players, teams, total_players


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

        # Format-isolated scoring settings
        scoring_cfg = _extract_category_scoring_config(format_type, request.form)
        scoring_format = scoring_cfg['scoring_format']
        num_sets = scoring_cfg['num_sets']
        games_per_set = scoring_cfg['games_per_set']
        total_games = scoring_cfg['total_games']
        points_to_win = scoring_cfg['points_to_win']
        max_players_per_team = scoring_cfg['max_players_per_team']

        # Advanced settings for group stage
        has_group_stage = (format_type in ['group_stage', 'round_robin', 'doubles_round_robin'])
        group_structure_mode = request.form.get('group_structure_mode', 'auto') if format_type == 'group_stage' else 'manual'
        if group_structure_mode not in ('auto', 'manual'):
            group_structure_mode = 'auto'
        num_groups = request.form.get('num_groups', type=int) if has_group_stage else None
        if format_type == 'group_stage' and not num_groups:
            num_groups = 2
        teams_per_group = request.form.get('teams_per_group', type=int) if has_group_stage else None
        matches_per_team_pair = request.form.get('matches_per_team_pair', type=int, default=1) if has_group_stage else None
        
        # Determine qualifiers for knockout stage
        if format_type == 'group_stage':
            qualifiers_per_group = request.form.get('qualifiers_per_group', type=int, default=2)
            allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on'
        elif format_type in ['round_robin', 'doubles_round_robin']:
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

        # Scheduling fields inherited globally from tournament or overridden by category
        import json
        from datetime import datetime, time, timedelta

        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str.strip(), '%Y-%m-%d').date()
            except ValueError:
                pass
        if not start_date and tournament.start_date:
            start_date = tournament.start_date

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str.strip(), '%Y-%m-%d').date()
            except ValueError:
                pass
        if not end_date:
            end_date = tournament.end_date or start_date

        if start_date and end_date and end_date < start_date:
            end_date = start_date

        start_time = request.form.get('start_time', '09:00').strip() or '09:00'
        end_time = request.form.get('end_time', '19:00').strip() or '19:00'

        # Multi-day operating hours for each spanned date
        daily_dict = {}
        if start_date and end_date:
            cur = start_date
            while cur <= end_date:
                d_str = cur.strftime('%Y-%m-%d')
                d_start = request.form.get(f'daily_start_{d_str}') or start_time
                d_end = request.form.get(f'daily_end_{d_str}') or end_time
                daily_dict[d_str] = {"start": d_start.strip(), "end": d_end.strip()}
                cur += timedelta(days=1)
        daily_schedule = json.dumps(daily_dict) if daily_dict else None

        start_date_time = None
        if start_date:
            try:
                st_parts = [int(p) for p in start_time.split(':')]
                start_date_time = datetime.combine(start_date, time(st_parts[0], st_parts[1]))
            except Exception:
                start_date_time = datetime.combine(start_date, time(9, 0))

        num_courts = request.form.get('num_courts', type=int) or tournament.num_courts or 1
        court_names = request.form.get('court_names') or tournament.court_names or ''
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
            group_structure_mode=group_structure_mode,
            max_players_per_team=max_players_per_team,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            daily_schedule=daily_schedule,
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

    # Count pending and total group stage / round robin matches
    group_matches_list = [m for m in matches if getattr(m, 'match_type', None) in ('group_stage', 'round_robin') and getattr(m, 'parent_match_id', None) is None]
    total_group_matches = len(group_matches_list)
    pending_group_count = sum(1 for m in group_matches_list if getattr(m, 'status', None) != 'completed')

    # Group stage structure & knockout qualification preview context
    knockout_preview = None
    structure_options = []
    if category.has_group_stage:
        from app.services.format_engine.group_stage.logic import GroupStageFormat
        if groups_data:
            knockout_preview = GroupStageFormat.get_knockout_qualification_preview(category)
        if category.status == 'setup' and category.format == 'group_stage' and len(participants) >= 4:
            structure_options = GroupStageFormat.compute_group_structure_options(
                len(participants),
                category.qualifiers_per_group or 2
            )

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
                         total_group_matches=total_group_matches,
                         pending_group_count=pending_group_count,
                         knockout_preview=knockout_preview,
                         structure_options=structure_options,
                         formats=TOURNAMENT_FORMATS)


@category_bp.route('/t/<slug>/categories/<int:category_id>/toggle-publish', methods=['POST'])
@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/toggle-publish', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def toggle_publish_draw(slug, category_id):
    """Toggle public visibility for the category draw (draft vs published)."""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)
    if category.tournament_id != tournament.id:
        abort(404)

    category.draw_published = not bool(category.draw_published)
    db.session.commit()

    status_label = "published and is now visible to the public" if category.draw_published else "unpublished (saved as draft)"
    flash(f"Category draw has been {status_label}.", "success")
    return redirect(url_for('category.view_category', slug=slug, category_id=category_id))


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

                if not name:
                    flash('Category name cannot be empty.', 'error')
                    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))

                category.name = name
                category.max_participants = max_participants
                category.entry_fee = request.form.get('entry_fee', type=float, default=0.0)

                # Date and daily operating times for Category
                if 'start_date' in request.form:
                    s_str = request.form.get('start_date', '').strip()
                    if s_str:
                        try:
                            category.start_date = datetime.strptime(s_str, '%Y-%m-%d').date()
                        except ValueError:
                            pass
                if 'end_date' in request.form:
                    e_str = request.form.get('end_date', '').strip()
                    if e_str:
                        try:
                            category.end_date = datetime.strptime(e_str, '%Y-%m-%d').date()
                        except ValueError:
                            pass
                if category.start_date and category.end_date and category.end_date < category.start_date:
                    category.end_date = category.start_date

                if 'start_time' in request.form:
                    category.start_time = request.form.get('start_time', '09:00').strip() or '09:00'
                if 'end_time' in request.form:
                    category.end_time = request.form.get('end_time', '19:00').strip() or '19:00'

                if category.start_date and category.end_date:
                    import json
                    from datetime import timedelta
                    daily_dict = {}
                    cur = category.start_date
                    while cur <= category.end_date:
                        d_str = cur.strftime('%Y-%m-%d')
                        d_start = request.form.get(f'daily_start_{d_str}') or category.start_time or '09:00'
                        d_end = request.form.get(f'daily_end_{d_str}') or category.end_time or '19:00'
                        daily_dict[d_str] = {"start": d_start.strip(), "end": d_end.strip()}
                        cur += timedelta(days=1)
                    category.daily_schedule = json.dumps(daily_dict)

                if category.start_date:
                    try:
                        st_parts = [int(p) for p in (category.start_time or '09:00').split(':')]
                        category.start_date_time = datetime.combine(category.start_date, time(st_parts[0], st_parts[1]))
                    except Exception:
                        pass
                
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
                    format_type = request.form.get('format') or category.format
                    if format_type == 'single_elimination':
                        sub_format = request.form.get('sub_format')
                        if sub_format == 'doubles':
                            format_type = 'doubles_elimination'
                    elif format_type == 'round_robin':
                        sub_format = request.form.get('sub_format')
                        if sub_format == 'doubles':
                            format_type = 'doubles_round_robin'

                    scoring_cfg = _extract_category_scoring_config(format_type, request.form)
                    category.format = format_type
                    category.scoring_format = scoring_cfg['scoring_format']
                    category.num_sets = scoring_cfg['num_sets']
                    category.games_per_set = scoring_cfg['games_per_set']
                    category.total_games = scoring_cfg['total_games']
                    category.points_to_win = scoring_cfg['points_to_win']
                    category.max_players_per_team = scoring_cfg['max_players_per_team']

                    category.has_group_stage = (format_type in ['group_stage', 'round_robin', 'doubles_round_robin'])
                    if category.has_group_stage:
                        if format_type == 'group_stage':
                            mode_val = request.form.get('group_structure_mode')
                            if mode_val in ('auto', 'manual'):
                                category.group_structure_mode = mode_val
                        category.num_groups = request.form.get('num_groups', type=int) or (2 if format_type == 'group_stage' else None)
                        category.teams_per_group = request.form.get('teams_per_group', type=int)
                        category.matches_per_team_pair = request.form.get('matches_per_team_pair', type=int, default=1)
                        if format_type == 'group_stage':
                            category.qualifiers_per_group = request.form.get('qualifiers_per_group', type=int, default=2)
                            category.allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on'
                        elif format_type in ['round_robin', 'doubles_round_robin']:
                            has_knockout = request.form.get('has_knockout_stage') == 'on'
                            if has_knockout:
                                category.qualifiers_per_group = request.form.get('qualifiers_per_group', type=int, default=2)
                                category.allow_lucky_losers = request.form.get('allow_lucky_losers') == 'on'
                            else:
                                category.qualifiers_per_group = 0
                                category.allow_lucky_losers = False
                        if format_type == 'group_stage' and category.num_groups:
                            _sync_category_groups(category, category.num_groups, rebalance_participants=False)
                    else:
                        category.num_groups = None
                        category.teams_per_group = None
                        category.matches_per_team_pair = None
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
                    
                    # Delete child rubbers first to satisfy foreign key integrity
                    Match.query.filter_by(category_id=category_id).filter(Match.parent_match_id.isnot(None)).delete()
                    # Delete parent matches
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

    structure_options = []
    if category.format == 'group_stage' and category.status == 'setup':
        from app.services.format_engine.group_stage.logic import GroupStageFormat
        k = category.max_players_per_team or 1
        if k > 1:
            _, _, teams, total_reg_players = _collect_draft_pool(category)
            n_for_options = len(teams) if len(teams) >= 4 else (total_reg_players // k)
        else:
            n_for_options = len(participants)
        if n_for_options >= 4:
            structure_options = GroupStageFormat.compute_group_structure_options(
                n_for_options,
                category.qualifiers_per_group or 2
            )

    return render_template('category/manage.html',
                         tournament=tournament,
                         category=category,
                         participants=participants,
                         structure_options=structure_options,
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

    # Guard 1: Prevent duplicate knockout bracket generation
    existing_knockout = Match.query.filter_by(
        category_id=category_id,
        match_type='knockout'
    ).first()
    if existing_knockout:
        flash('Knockout stage bracket has already been generated for this category.', 'warning')
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

    # Guard 2: Verify all group matches are completed before starting knockout
    pending_group = Match.query.filter(
        Match.category_id == category_id,
        Match.match_type.in_(['group_stage', 'round_robin']),
        Match.parent_match_id.is_(None),
        Match.status != 'completed'
    ).count()
    if pending_group > 0 and not request.form.get('force_start'):
        flash(f'Cannot start knockout stage: {pending_group} group stage match(es) are still pending or in progress.', 'error')
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

    try:
        # Generate knockout bracket from group qualifiers (honoring manual Lucky Loser selection if submitted)
        from app.services.format_engine.group_stage.logic import GroupStageFormat
        lucky_loser_ids = request.form.getlist('lucky_loser_ids', type=int)
        preview = GroupStageFormat.get_knockout_qualification_preview(category)
        slots_needed = preview['slots_to_fill']

        if category.allow_lucky_losers and slots_needed > 0 and lucky_loser_ids:
            valid_candidate_ids = {p.id for p in preview['lucky_loser_candidates']}
            unique_ll_ids = list(dict.fromkeys([pid for pid in lucky_loser_ids if pid in valid_candidate_ids]))
            if len(unique_ll_ids) != slots_needed:
                flash(
                    f'Please select exactly {slots_needed} Lucky Loser(s) to complete the {preview["target_bracket"]}-team knockout bracket.',
                    'error'
                )
                return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
            matches_data = GroupStageFormat.generate_knockout_from_groups(category, lucky_loser_ids=unique_ll_ids)
        else:
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

        db.session.flush()

        # Propagate child rubbers for any Round 1 matches with byes in team events
        if category.max_players_per_team and category.max_players_per_team > 1:
            bye_matches = Match.query.filter_by(
                category_id=category.id,
                match_type='knockout',
                parent_match_id=None,
                status='completed'
            ).all()
            for b_match in bye_matches:
                GroupStageFormat._propagate_knockout_team_rubbers(b_match, category)

        db.session.commit()
        flash('Knockout stage started successfully!', 'success')
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

@category_bp.route('/t/<slug>/categories/<int:category_id>/match/<int:match_id>/report', methods=['POST'])
@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/match/<int:match_id>/report', methods=['POST'])
def report_category_match_result(slug, category_id, match_id):
    """Report match result for category with RBAC and conflict checking."""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_access(tournament, min_role="scorer")
    category = Category.query.get_or_404(category_id)
    match = Match.query.get_or_404(match_id)

    # 1. Anti-Conflict of Interest Check
    current_u = get_current_user()
    try:
        check_scoring_conflict_of_interest(match, current_u)
    except PermissionError as pe:
        flash(str(pe), "error")
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

    # 2. Optimistic Concurrency Locking Check
    client_lock_version = request.form.get('lock_version', type=int)
    if client_lock_version and match.lock_version and match.lock_version != client_lock_version:
        flash("Conflict detected: This match was recently updated by another official. Please review the updated score.", "warning")
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

    match.lock_version = (match.lock_version or 1) + 1

    if category.status == 'upcoming':
        category.status = 'in_progress'
        category.started_at = datetime.utcnow()

    try:
        action = request.form.get('action')
        is_live_update = (action == 'live_score')
        winner_id = request.form.get('winner_id', type=int) if not is_live_update else None
        
        # Audit Validation if match was already completed
        is_score_correction = (match.status == 'completed')
        old_state = None
        audit_reason = None
        audit_explanation = None

        if is_score_correction:
            audit_reason = request.form.get('audit_reason', '').strip()
            audit_explanation = request.form.get('audit_explanation', '').strip()
            if not audit_reason:
                flash("Audit validation failed: Reason is mandatory when modifying or correcting a completed match score.", "error")
                return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
            if len(audit_explanation) < 10:
                flash("Audit validation failed: An explanation (minimum 10 characters) is required when correcting a completed match score.", "error")
                return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

            old_state = {
                'score1': match.score1,
                'score2': match.score2,
                'winner_id': match.winner_id,
                'status': match.status
            }
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

        outcome_type = request.form.get('outcome_type', 'normal')
        retiring_player = request.form.get('retiring_player', type=int)

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
                is_live_update=is_live_update,
                is_walkover=(outcome_type == 'walkover'),
                is_retired=(outcome_type == 'retired'),
                retiring_player=retiring_player,
            )
            if not is_live_update and winner_ind:
                actual_winner_id = match.participant1_id if winner_ind == 1 else match.participant2_id
                if winner_id and winner_id != actual_winner_id:
                    raise ValueError("The selected winner does not match the rubber scores.")
                winner_id = actual_winner_id
        elif scoring_format == 'points' or (category and category.format in ['round_robin', 'doubles_round_robin'] and scoring_format != 'games'):
            from app.services.tennis_logic import validate_points_score
            if scoring_format == 'points':
                p1_raw = request.form.get('points_p1')
                p2_raw = request.form.get('points_p2')
            else:
                p1_raw = request.form.get('set1_p1')
                p2_raw = request.form.get('set1_p2')

            score1, score2, winner_id = validate_points_score(
                winner_id=winner_id,
                p1_id=match.participant1_id,
                p2_id=match.participant2_id,
                p1_score_raw=p1_raw,
                p2_score_raw=p2_raw,
                points_to_win=points_to_win,
                is_live_update=is_live_update,
                outcome_type=outcome_type,
                retiring_player=retiring_player,
            )
        else:
            if not is_live_update and outcome_type in ('walkover', 'retired') and not winner_id and retiring_player in (1, 2):
                winner_id = match.participant2_id if retiring_player == 1 else match.participant1_id
            score1, score2 = validate_and_format_score(
                winner_id,
                match.participant1_id,
                match.participant2_id,
                num_sets,
                games_per_set,
                form_data,
                is_live_update=is_live_update,
                outcome_type=outcome_type,
                retiring_player=retiring_player,
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

        if is_score_correction:
            from app.services.utils.audit import log_audit
            p1_label = match.participant1.name if match.participant1 else (match.p1_player1.name if getattr(match, 'p1_player1', None) else 'TBD')
            p2_label = match.participant2.name if match.participant2 else (match.p2_player1.name if getattr(match, 'p2_player1', None) else 'TBD')
            match_num = match.match_number or match.rubber_number or match.id
            new_state = {
                'score1': match.score1,
                'score2': match.score2,
                'winner_id': match.winner_id,
                'status': match.status
            }
            log_audit(
                action_type='modify_match_score',
                target_id=match.id,
                target_name=f"Match #{match_num} ({p1_label} vs {p2_label})",
                reason=audit_reason,
                explanation=audit_explanation,
                details={'previous': old_state, 'new': new_state}
            )

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
def allot_fixture_lineup(slug, category_id, fixture_id):
    """
    Allot official team match lineup based on captains' submitted nomination slips.
    - Rubber 1: Singles (Team 1 Player vs Team 2 Player)
    - Rubber 2: Doubles 1 (Team 1 Pair vs Team 2 Pair)
    - Rubber 3: Doubles 2 (Team 1 Pair vs Team 2 Pair)
    Accessible by Tournament Organizer, Superadmin, Staff, or Team Captains.
    """
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    fixture = Match.query.get_or_404(fixture_id)

    if fixture.tournament_id != tournament.id or fixture.category_id != category.id:
        flash("Invalid fixture or category.", "error")
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

    user = get_current_user()
    try:
        check_fixture_lineup_access(fixture, user)
    except PermissionError as pe:
        flash(str(pe), "error")
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id) + f"#fixture-{fixture.id}")

    # Determine which team the user can edit
    is_admin = (user.role == 'superadmin' or tournament.user_id == user.id)
    if not is_admin:
        from app.domain.models import TournamentStaff
        staff = TournamentStaff.query.filter_by(tournament_id=tournament.id, user_id=user.id).first()
        if staff and staff.role in ('manager', 'official'):
            is_admin = True

    def is_team_captain(team, u):
        if not team or not hasattr(team, 'team_members'):
            return False
        for m in team.team_members:
            if m.player and m.player.user_id == u.id and m.role in ('captain', 'vice_captain'):
                return True
        return False

    can_edit_p1 = is_admin or is_team_captain(fixture.participant1, user)
    can_edit_p2 = is_admin or is_team_captain(fixture.participant2, user)

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
        if can_edit_p1 and r1_p1 is not None:
            r_singles.p1_player1_id = r1_p1
        if can_edit_p2 and r1_p2 is not None:
            r_singles.p2_player1_id = r1_p2
    if r_doubles_1:
        if can_edit_p1 and (r2_p1_1 is not None or r2_p1_2 is not None):
            r_doubles_1.p1_player1_id = r2_p1_1
            r_doubles_1.p1_player2_id = r2_p1_2
        if can_edit_p2 and (r2_p2_1 is not None or r2_p2_2 is not None):
            r_doubles_1.p2_player1_id = r2_p2_1
            r_doubles_1.p2_player2_id = r2_p2_2
    if r_doubles_2:
        if can_edit_p1 and (r3_p1_1 is not None or r3_p1_2 is not None):
            r_doubles_2.p1_player1_id = r3_p1_1
            r_doubles_2.p1_player2_id = r3_p1_2
        if can_edit_p2 and (r3_p2_1 is not None or r3_p2_2 is not None):
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
    1. Review registered player count, handle any leftover slots (Late Entry / Dummy),
       and pick Group Stage + Knockout structure (e.g., 2 uneven groups vs 3 groups + Lucky Losers).
    2. Organize registered players into Skill Tiers (Tier A Captains, Tier B VCs, C..E).
    3. Mode A: Manual Paper Chit Draw selection / Mode B: 1-Click Auto-Draft.
    4. Group allocation review & Group Session Start Timings / Courts configuration.
    """
    from app.services.format_engine.group_stage.logic import GroupStageFormat

    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    num_groups = category.num_groups or 2
    existing_groups = Group.query.filter_by(category_id=category.id).order_by(Group.id).all()
    if not existing_groups:
        existing_groups = _sync_category_groups(category, num_groups, rebalance_participants=False)
        db.session.commit()

    tier_records, unassigned_players, teams, total_players = _collect_draft_pool(category)

    # Group existing tiers into buckets (dynamic up to k)
    k = category.max_players_per_team or 5
    active_tier_letters = list('ABCDEFGH'[:k])
    tiers_map = {letter: [] for letter in active_tier_letters}
    for tr in tier_records:
        if tr.tier in tiers_map:
            tiers_map[tr.tier].append(tr)

    full_teams = total_players // k if total_players >= k else 0
    leftover_players = total_players % k if total_players > 0 else 0
    players_needed_for_next = (k - leftover_players) if leftover_players > 0 else 0
    calculated_teams = max(2, full_teams) if total_players >= k else 2
    teams_per_group = max(1, calculated_teams // num_groups)

    qualifiers_per_group = category.qualifiers_per_group or 2
    team_count_for_struct = len(teams) if len(teams) >= 2 else calculated_teams
    structure_options = GroupStageFormat.compute_group_structure_options(
        team_count_for_struct,
        qualifiers_per_group=qualifiers_per_group,
    )
    next_team_options = (
        GroupStageFormat.compute_group_structure_options(full_teams + 1, qualifiers_per_group=qualifiers_per_group)
        if leftover_players > 0 and full_teams + 1 >= 2 else []
    )

    # Identify Dummy / TBD placeholder players so organizer can replace them with late entries
    dummy_players = []
    seen_dummy_ids = set()
    for p in unassigned_players:
        if p.name and p.name.startswith('TBD / Dummy') and p.id not in seen_dummy_ids:
            dummy_players.append(p)
            seen_dummy_ids.add(p.id)
    for tr in tier_records:
        if tr.player and tr.player.name and tr.player.name.startswith('TBD / Dummy') and tr.player.id not in seen_dummy_ids:
            dummy_players.append(tr.player)
            seen_dummy_ids.add(tr.player.id)

    teams_by_group = {g.id: [] for g in existing_groups}
    unassigned_teams = []
    for team in teams:
        if team.group_id in teams_by_group:
            teams_by_group[team.group_id].append(team)
        else:
            unassigned_teams.append(team)

    return render_template(
        'category/team_draft.html',
        tournament=tournament,
        category=category,
        groups=existing_groups,
        unassigned_players=unassigned_players,
        tiers_map=tiers_map,
        active_tier_letters=active_tier_letters,
        teams=teams,
        teams_by_group=teams_by_group,
        unassigned_teams=unassigned_teams,
        total_players=total_players,
        players_per_team=k,
        full_teams=full_teams,
        leftover_players=leftover_players,
        players_needed_for_next=players_needed_for_next,
        dummy_players=dummy_players,
        calculated_teams=calculated_teams,
        teams_per_group=teams_per_group,
        num_groups=num_groups,
        structure_options=structure_options,
        next_team_options=next_team_options,
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

        if category.status != 'setup':
            raise ValueError("Cannot modify teams once matches are in progress.")

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

        cat_groups = Group.query.filter_by(category_id=category_id).order_by(Group.id).all()

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

            grp_id = cat_groups[(idx - 1) % len(cat_groups)].id if cat_groups else None

            team_p = Participant(
                tournament_id=tournament.id,
                category_id=category.id,
                name=team_name,
                player_id=captain_id,
                group_id=grp_id
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

        if cat_groups and created_teams:
            from app.services.format_engine.group_stage.logic import GroupStageFormat
            GroupStageFormat._assign_groups_snake(created_teams, cat_groups, teams_per_group=category.teams_per_group)

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


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/configure-structure', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def configure_group_structure(slug, category_id):
    """Apply an organizer-selected Group Stage + Knockout structure option (G groups, Lucky Losers)."""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    next_target = request.form.get('next_target', 'draft')

    def _redirect_back():
        if next_target == 'manage':
            return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
        if next_target == 'view':
            return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
        return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))

    if category.status != 'setup':
        flash('Cannot change group structure once matches are in progress.', 'error')
        return _redirect_back()

    num_groups = request.form.get('num_groups', type=int)
    if not num_groups or num_groups < 2 or num_groups > 16:
        flash('Number of groups must be between 2 and 16.', 'error')
        return _redirect_back()

    raw_ll = str(request.form.get('allow_lucky_losers', '')).strip().lower()
    allow_lucky_losers = raw_ll in ('1', 'true', 'on', 'yes')
    qualifiers_per_group = request.form.get('qualifiers_per_group', type=int)

    try:
        category.num_groups = num_groups
        category.allow_lucky_losers = allow_lucky_losers
        category.group_structure_mode = 'manual'
        if qualifiers_per_group and qualifiers_per_group >= 1:
            category.qualifiers_per_group = qualifiers_per_group

        _sync_category_groups(category, num_groups, rebalance_participants=True)
        db.session.commit()

        ll_msg = 'with Lucky Losers enabled' if allow_lucky_losers else 'without Lucky Losers'
        flash(f'Group structure updated: {num_groups} groups configured ({ll_msg}).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to update group structure: {str(e)}', 'error')

    return _redirect_back()


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/assign-team-group', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def assign_team_group(slug, category_id):
    """Move a drafted team between Group A / B / C... while category is in setup."""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    if category.status != 'setup':
        if request.is_json:
            return jsonify({'success': False, 'error': 'Cannot move teams once matches have started.'}), 400
        flash('Cannot move teams once matches have started.', 'error')
        return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))

    payload = request.get_json(silent=True) or request.form
    participant_id = payload.get('participant_id')
    group_id = payload.get('group_id')
    try:
        participant_id = int(participant_id)
        group_id = int(group_id)
    except (TypeError, ValueError):
        if request.is_json:
            return jsonify({'success': False, 'error': 'Invalid team or group selection.'}), 400
        flash('Invalid team or group selection.', 'error')
        return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))

    team = Participant.query.filter_by(id=participant_id, category_id=category.id).first_or_404()
    grp = Group.query.filter_by(id=group_id, category_id=category.id).first_or_404()

    team.group_id = grp.id
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'message': f'Moved {team.name} to {grp.name}.'})
    flash(f'Moved {team.name} to {grp.name}.', 'success')
    return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id) + '#teams')


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/quick-late-entry', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def quick_late_entry_player(slug, category_id):
    """
    Add a late-entry player directly from Team Draft (either as a new player or
    replacing an existing 'TBD / Dummy' placeholder slot in place).
    """
    from app.domain.models import Registration

    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    if category.status != 'setup':
        flash('Cannot add players once matches are in progress.', 'error')
        return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))

    raw_name = request.form.get('player_name', '').strip()
    ok, clean_name = validate_name(raw_name, min_len=2, max_len=100, field_name="Player Name")
    if not ok:
        flash(clean_name, 'error')
        return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))

    mobile = request.form.get('player_mobile', '').strip()
    if mobile:
        ok_m, clean_m = validate_mobile(mobile, field_name="Mobile")
        if not ok_m:
            flash(clean_m, 'error')
            return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))
        mobile = clean_m

    gender = request.form.get('player_gender') or (
        category.gender if category.gender in ('Male', 'Female', 'Boys', 'Girls') else 'Male'
    )
    age_val = request.form.get('player_age', type=int) or 25
    dob = estimate_dob_from_age(age_val)
    age_cat = determine_age_category(age=age_val, dob=dob)
    replace_dummy_id = request.form.get('replace_dummy_id', type=int)

    try:
        if replace_dummy_id:
            dummy_player = Player.query.get_or_404(replace_dummy_id)
            old_name = dummy_player.name
            dummy_player.name = clean_name
            if mobile:
                dummy_player.contact_number = mobile
            dummy_player.gender = gender
            dummy_player.dob = dob
            dummy_player.age_category = age_cat
            db.session.commit()
            flash(f'Replaced placeholder "{old_name}" with late-entry player {clean_name}!', 'success')
            return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))

        current_u = get_current_user()
        player_obj = Player(
            name=clean_name,
            contact_number=mobile or None,
            gender=gender,
            dob=dob,
            age_category=age_cat,
        )
        db.session.add(player_obj)
        db.session.flush()

        reg = Registration(
            tournament_id=tournament.id,
            category_id=category.id,
            user_id=current_u.id,
            player_id=player_obj.id,
            status='approved',
            payment_status='paid',
            payment_method='cash',
        )
        db.session.add(reg)
        db.session.commit()
        flash(f'Added late-entry player {clean_name} to draft pool!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to add late-entry player: {str(e)}', 'error')

    return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))


@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/add-dummy-players', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def add_dummy_players(slug, category_id):
    """
    Create placeholder 'TBD / Dummy Player' slots to complete a partial team
    before final groups are formed; can later be replaced via Late Entry.
    """
    from app.domain.models import Registration

    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    category = Category.query.get_or_404(category_id)

    if category.status != 'setup':
        flash('Cannot modify players once matches are in progress.', 'error')
        return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))

    k = category.max_players_per_team or 5
    _, _, _, total_players = _collect_draft_pool(category)
    leftover = total_players % k
    default_needed = (k - leftover) if leftover > 0 else 1

    count = request.form.get('count', type=int) or default_needed
    count = max(1, min(k, count))

    try:
        current_u = get_current_user()
        existing_dummies = Player.query.filter(Player.name.like('TBD / Dummy Player #%')).count()
        created_names = []
        default_gender = category.gender if category.gender in ('Male', 'Female', 'Boys', 'Girls') else 'Male'

        for i in range(1, count + 1):
            label = f"TBD / Dummy Player #{existing_dummies + i}"
            dummy = Player(
                name=label,
                gender=default_gender,
                age_category=category.age_category or 'Open',
            )
            db.session.add(dummy)
            db.session.flush()

            reg = Registration(
                tournament_id=tournament.id,
                category_id=category.id,
                user_id=current_u.id,
                player_id=dummy.id,
                status='approved',
                payment_status='pending',
                payment_method='cash',
            )
            db.session.add(reg)
            created_names.append(label)

        db.session.commit()
        flash(f'Added {len(created_names)} Dummy/TBD slot(s) to complete full team(s). You can replace them anytime via Late Entry!', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to add dummy slots: {str(e)}', 'error')

    return redirect(url_for('category.team_draft_view', slug=slug, category_id=category_id))

