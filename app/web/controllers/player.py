from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from app.web.controllers.auth import login_required, get_current_user, role_required
from app.domain.models import Player, db
from app.services.utils.validation import (
    validate_name, validate_mobile, validate_email, validate_dob
)

player_bp = Blueprint('player', __name__)

@player_bp.route('/player/<int:player_id>')
def view_player(player_id):
    player = Player.query.get_or_404(player_id)
    return render_template('player/view.html', player=player)

@player_bp.route('/player/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    current_user = get_current_user()
    if not current_user.profile_completed and current_user.role not in ['admin', 'superadmin']:
        flash("Please complete your profile to access your player dashboard.", "info")
        return redirect(url_for('auth.complete_profile', next=url_for('player.dashboard')))

    players = Player.query.filter_by(user_id=current_user.id).all()
    if not players:
        # Secure profile recovery / initialization if missing
        from app.services.user_service import ensure_user_profile
        recovered = ensure_user_profile(current_user.id)
        if recovered:
            players = [recovered]

    all_players = []
    if current_user.role == 'superadmin':
        all_players = Player.query.filter(Player.registration_no.isnot(None), Player.registration_no != '').order_by(Player.name).all()
    
    from app.domain.models import Participant, Match, TeamMember
    from datetime import datetime
    
    dashboard_data = []
    for p in players:
        # 1. Direct registrations (individual events or captain participant record)
        direct_participants = Participant.query.filter(
            db.or_(Participant.player_id == p.id, Participant.player2_id == p.id)
        ).all()

        # 2. Squad team memberships (Team League events: Vice-Captains, Tiers B-E, squad members)
        team_memberships = TeamMember.query.filter_by(player_id=p.id).all()
        team_participant_ids = [tm.team_id for tm in team_memberships if tm.team_id]
        team_participants = Participant.query.filter(Participant.id.in_(team_participant_ids)).all() if team_participant_ids else []

        # Unified participants list
        participant_map = {part.id: part for part in (direct_participants + team_participants)}
        participant_ids = list(participant_map.keys())

        # Compile assigned teams for squad visibility
        assigned_teams = []
        for tm in team_memberships:
            team = tm.team
            if team:
                assigned_teams.append({
                    'team': team,
                    'tournament': team.tournament,
                    'category': team.category,
                    'group': team.group,
                    'tier': tm.tier,
                    'role': 'Captain' if team.player_id == p.id else (f"Tier {tm.tier}" if tm.tier else "Player"),
                    'teammates': team.team_members
                })
        
        matches = []
        if participant_ids:
            matches = Match.query.filter(
                db.or_(
                    Match.participant1_id.in_(participant_ids),
                    Match.participant2_id.in_(participant_ids)
                )
            ).order_by(Match.scheduled_time.asc().nulls_last()).all()
            
        upcoming_matches = [m for m in matches if m.status in ['pending', 'in_progress'] and m.participant1_id and m.participant2_id]
        match_history = [m for m in matches if m.status == 'completed']
        match_history.sort(key=lambda m: m.completed_at or m.scheduled_time or datetime.min, reverse=True)
        
        wins = sum(1 for m in match_history if m.winner_id in participant_ids)
        losses = len(match_history) - wins
        win_rate = (wins / len(match_history) * 100) if match_history else 0
        
        dashboard_data.append({
            'player': p,
            'upcoming_matches': upcoming_matches,
            'match_history': match_history,
            'participant_ids': participant_ids,
            'assigned_teams': assigned_teams,
            'stats': {
                'matches_played': len(match_history),
                'wins': wins,
                'losses': losses,
                'win_rate': round(win_rate, 1)
            }
        })
    
    if request.method == 'POST':
        from datetime import datetime
        
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return None
            
        def populate_player_from_request(p):
            raw_name = request.form.get('name', p.name).strip()
            ok, clean_name = validate_name(raw_name, min_len=2, field_name="Player Name")
            if not ok:
                return False, clean_name
            p.name = clean_name

            p.gender = request.form.get('gender', p.gender)

            dob_str = request.form.get('dob', '').strip()
            if dob_str:
                ok, dob_res = validate_dob(dob_str, field_name="Date of Birth")
                if not ok:
                    return False, dob_res
                p.dob = dob_res
                from app.domain.constants import calculate_canonical_age_category
                p.age_category = calculate_canonical_age_category(p.dob)

            raw_email = request.form.get('email', '').strip()
            if raw_email:
                ok, clean_email = validate_email(raw_email, required=False)
                if not ok:
                    return False, clean_email
                p.email = clean_email
            else:
                p.email = None

            raw_mobile = request.form.get('contact_number', '').strip()
            if raw_mobile:
                ok, clean_mob = validate_mobile(raw_mobile, required=False)
                if not ok:
                    return False, clean_mob
                p.contact_number = clean_mob
            else:
                p.contact_number = None

            p.height = request.form.get('height', '').strip() or None
            p.weight = request.form.get('weight', '').strip() or None
            p.blood_group = request.form.get('blood_group', p.blood_group)
            p.nationality = request.form.get('nationality', p.nationality)
            p.address = request.form.get('address', p.address)
            p.coach = request.form.get('coach', p.coach)
            p.academy = request.form.get('academy', p.academy)
            return True, None
            
        action = request.form.get('action')
        
        if action == 'update_profile':
            player_id = request.form.get('player_id', type=int)
            player = Player.query.filter_by(id=player_id, user_id=current_user.id).first_or_404()
            ok, err_msg = populate_player_from_request(player)
            if not ok:
                flash(err_msg, 'error')
                return redirect(url_for('player.dashboard'))
            
            # Handle profile photo (Vercel is read-only, so we accept a URL instead of a file)
            avatar_url = request.form.get('avatar_url')
            if avatar_url:
                player.avatar_url = avatar_url

            # Sync user profile attributes & completion status
            try:
                current_user.full_name = player.name
                if player.contact_number:
                    current_user.phone_number = player.contact_number
                from app.domain.constants import calculate_profile_completion_percentage
                pct_info = calculate_profile_completion_percentage(
                    user_name=player.name,
                    email=player.email or current_user.email,
                    contact_number=player.contact_number,
                    dob=player.dob,
                    gender=player.gender,
                    primary_sport=player.primary_sport,
                    skill_level=player.skill_level,
                    emergency_contact_name=player.emergency_contact_name,
                    emergency_contact_phone=player.emergency_contact_phone,
                    avatar_url=player.avatar_url,
                    bio=player.bio,
                )
                current_user.completion_percentage = pct_info["percentage"]
                current_user.profile_completed = pct_info["is_complete"]
                player.profile_status = "complete" if pct_info["is_complete"] else "incomplete"
                db.session.commit()
                flash('Profile updated successfully!', 'success')
            except Exception as e:
                import logging
                logging.error(f"Error saving player profile: {e}", exc_info=True)
                db.session.rollback()
                flash("An error occurred while saving your profile changes.", "error")

            return redirect(url_for('player.dashboard'))
            
    return render_template('player/dashboard.html', players=players, dashboard_data=dashboard_data, all_players=all_players)


@player_bp.route('/admin/players')
@login_required
@role_required('admin', 'superadmin')
def admin_players():
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        players = Player.query.filter(
            db.or_(
                Player.name.ilike(f'%{search_query}%'),
                Player.registration_no.ilike(f'%{search_query}%')
            )
        ).all()
    else:
        players = Player.query.all()
        
    return render_template('admin/players.html', players=players, search_query=search_query)


@player_bp.route('/player/delete_account', methods=['POST'])
def delete_account():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
        
    player = Player.query.filter_by(user_id=user.id).first()
    
    # Soft delete and free up the email so they can register again
    user.role = 'deleted'
    user.password_hash = '*deleted*'
    # Append a timestamp or ID to the email to prevent Unique Constraint violation if they register again
    import time
    user.email = f"deleted_{int(time.time())}_{user.email}"
    # The original username remains taken so they must pick a new one
    
    if player:
        player.current_status = 'Deleted'
        
    db.session.commit()
    session.clear()
    
    flash('Your account has been successfully deleted. Your history remains for tournament records.', 'success')
    return redirect(url_for('auth.login'))
