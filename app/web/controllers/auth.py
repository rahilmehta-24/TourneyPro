import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, abort
from app.domain.models import db, User, Tournament, TournamentStaff, AcademyMember, Player, Participant, AuditLog
from app.services.utils.validation import (
    validate_name, validate_username, validate_email, validate_password,
    validate_dob, validate_mobile
)

auth_bp = Blueprint('auth', __name__)

def get_current_user():
    if 'user_id' in session:
        if not hasattr(g, 'current_user') or g.current_user is None:
            g.current_user = User.query.get(session['user_id'])
        return g.current_user
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            flash('Please log in first to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user or user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_tournament_ownership(tournament):
    user = get_current_user()
    if not user:
        abort(401)
    if user.role != 'superadmin' and tournament.user_id != user.id:
        abort(403)

def check_tournament_access(tournament, min_role="scorer"):
    """
    Verifies if the current user or active PIN session has permission to access/score
    matches in the tournament.
    Role hierarchy:
      - 'manager': Superadmin, Tournament Owner, or TournamentStaff(manager)
      - 'official': Superadmin, Tournament Owner, TournamentStaff(manager/official), or valid court PIN
      - 'scorer': Superadmin, Tournament Owner, TournamentStaff(manager/official/scorer), or valid court PIN
    """
    user = get_current_user()

    # 1. Superadmin has universal access
    if user and user.role == "superadmin":
        return True

    # 2. Tournament Owner has full tournament access
    if user and tournament.user_id == user.id:
        return True

    role_weights = {"manager": 3, "official": 2, "scorer": 1}
    min_weight = role_weights.get(min_role, 1)

    # 3. Check TournamentStaff table for logged-in user
    if user:
        staff = TournamentStaff.query.filter_by(
            tournament_id=tournament.id,
            user_id=user.id
        ).first()
        if staff:
            staff_weight = role_weights.get(staff.role, 0)
            if staff_weight >= min_weight:
                return True

    # 4. Check temporary Court PIN session
    pin_session_key = f"court_pin_staff_{tournament.id}"
    if pin_session_key in session:
        pin_data = session[pin_session_key]
        staff = TournamentStaff.query.get(pin_data.get("staff_id"))
        if staff and staff.tournament_id == tournament.id:
            if not staff.pin_expires_at or staff.pin_expires_at > datetime.utcnow():
                staff_weight = role_weights.get(staff.role, 0)
                if staff_weight >= min_weight:
                    return True
            else:
                session.pop(pin_session_key, None)

    # Deny access
    if not user and pin_session_key not in session:
        abort(401)
    abort(403)

def check_scoring_conflict_of_interest(match, user):
    """
    Verify that the user recording scores does not have an active conflict of interest
    (i.e. is not a playing participant in this match or child rubber).
    """
    if not user:
        return  # Court PIN session umpire is not a player

    player_user_ids = set()

    def add_participant_user_ids(part):
        if not part:
            return
        if getattr(part, 'player', None) and part.player.user_id:
            player_user_ids.add(part.player.user_id)
        if getattr(part, 'player2', None) and part.player2.user_id:
            player_user_ids.add(part.player2.user_id)
        if hasattr(part, 'team_members') and part.team_members:
            for tm in part.team_members:
                if getattr(tm, 'player', None) and tm.player.user_id:
                    player_user_ids.add(tm.player.user_id)

    add_participant_user_ids(match.participant1)
    add_participant_user_ids(match.participant2)

    for pid_attr in ('p1_player1_id', 'p1_player2_id', 'p2_player1_id', 'p2_player2_id'):
        pid = getattr(match, pid_attr, None)
        if pid:
            p = Player.query.get(pid)
            if p and p.user_id:
                player_user_ids.add(p.user_id)

    if user.id in player_user_ids:
        raise PermissionError(
            "Conflict of interest: You are an active participant in this match. "
            "Scores must be entered by an impartial official, court umpire, or tournament organizer."
        )

def check_academy_access(academy, require_admin=False):
    """Enforces multi-tenant authorization isolation for Academy resources."""
    user = get_current_user()
    if not user:
        abort(401)
    if user.role == "superadmin":
        return True
    if academy.owner_id == user.id:
        return True

    membership = AcademyMember.query.filter_by(academy_id=academy.id, user_id=user.id).first()
    if not membership:
        abort(403)
    if require_admin and membership.role not in ("admin", "coach"):
        abort(403)
    return True

def check_fixture_lineup_access(fixture, user):
    """
    Verifies if user is authorized to submit or alter a fixture lineup.
    - Superadmin, Tournament Owner, or Manager/Official: always permitted.
    - Team Captain: permitted for their own team only, subject to 15-min lock window.
    """
    if not user:
        abort(401)
    if user.role == "superadmin" or fixture.tournament.user_id == user.id:
        return True

    staff = TournamentStaff.query.filter_by(tournament_id=fixture.tournament_id, user_id=user.id).first()
    if staff and staff.role in ("manager", "official"):
        return True

    def is_team_captain(team, u):
        if not team or not hasattr(team, 'team_members'):
            return False
        for m in team.team_members:
            if m.player and m.player.user_id == u.id and m.role in ('captain', 'vice_captain'):
                return True
        return False

    is_cap1 = is_team_captain(fixture.participant1, user)
    is_cap2 = is_team_captain(fixture.participant2, user)

    if not (is_cap1 or is_cap2):
        abort(403)

    if fixture.scheduled_time:
        cutoff_time = fixture.scheduled_time - timedelta(minutes=15)
        if datetime.utcnow() > cutoff_time:
            raise PermissionError("Lineup nominations are locked within 15 minutes of match scheduled start time.")

    return True

def check_player_ownership(player):
    user = get_current_user()
    if not user:
        abort(401)
    if user.role != 'superadmin' and player.user_id != user.id:
        abort(403)

def bootstrap_superadmin():
    """Create default superadmin user from environment variables if no users exist"""
    # Check if database has any users
    if User.query.count() == 0:
        username = os.environ.get('SUPERADMIN_USERNAME') or 'superadmin'
        password = os.environ.get('SUPERADMIN_PASSWORD') or 'adminpassword'
        email = 'superadmin@tourneypro.com'

        superadmin = User(
            username=username,
            email=email,
            role='superadmin'
        )
        superadmin.set_password(password)
        db.session.add(superadmin)
        db.session.commit()
        print(f"=== BOOTSTRAP === Created superadmin user: '{username}' with role 'superadmin'")

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if get_current_user():
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')

        user = User.query.filter(db.or_(User.username.ilike(username), User.email.ilike(username))).first()
        
        if user and user.role == 'deleted':
            flash('This account has been deleted.', 'error')
            return redirect(url_for('auth.login'))
            
        if user and user.check_password(password):
            session['user_id'] = user.id
            session.permanent = True
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if get_current_user():
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        name = request.form.get('name', username).strip() or username
        contact_number = request.form.get('contact_number', '').strip()

        ok, u_clean = validate_username(username)
        if not ok:
            flash(u_clean, 'error')
            return render_template('auth/register.html')
        username = u_clean

        ok, e_clean = validate_email(email, required=True)
        if not ok:
            flash(e_clean, 'error')
            return render_template('auth/register.html')
        email = e_clean

        ok, p_clean = validate_password(password, min_len=8)
        if not ok:
            flash(p_clean, 'error')
            return render_template('auth/register.html')

        ok, n_clean = validate_name(name, min_len=2, field_name="Full Name")
        if not ok:
            flash(n_clean, 'error')
            return render_template('auth/register.html')
        name = n_clean

        if contact_number:
            ok, mob_clean = validate_mobile(contact_number, required=False)
            if not ok:
                flash(mob_clean, 'error')
                return render_template('auth/register.html')
            contact_number = mob_clean

        # Check existing
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return render_template('auth/register.html')

        user = User(username=username, email=email, role='user')
        user.set_password(password)

        db.session.add(user)
        db.session.commit()  # commit to get user.id
        
        # Create initial Player profile
        from app.domain.models import Player
        from datetime import date
        
        gender = request.form.get('gender', 'Male')
        if gender not in ['Male', 'Female']:
            gender = 'Male'
            
        dob_str = request.form.get('dob', '').strip()
        dob = None
        age_category = 'Open'
        
        if dob_str:
            ok, dob_res = validate_dob(dob_str, field_name="Date of Birth")
            if not ok:
                flash(dob_res, 'error')
                return render_template('auth/register.html')
            dob = dob_res
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age <= 8:
                age_category = 'U8'
            elif age <= 10:
                age_category = 'U10'
            elif age <= 12:
                age_category = 'U12'
            elif age <= 14:
                age_category = 'U14'
            elif age <= 16:
                age_category = 'U16'
            elif age <= 18:
                age_category = 'U18'
            elif age >= 45:
                age_category = '45+'
            elif age >= 35:
                age_category = '35+'
            else:
                age_category = 'Open'
                
        # Parse new fields
        contact_number = request.form.get('contact_number')
        nationality = request.form.get('nationality')
        height = request.form.get('height')
        weight = request.form.get('weight')
        blood_group = request.form.get('blood_group')
        address = request.form.get('address')
        coach = request.form.get('coach')
        academy = request.form.get('academy')
        
        # System generated fields
        from datetime import date
        from datetime import timedelta
        import random
        
        current_date = date.today()
        # Generate Registration No: TP-YYYY-HEX
        reg_no = f"TP-{current_date.year}-{random.randint(0x1000, 0xFFFF):X}"
        registration_date = current_date
        registration_validity = current_date + timedelta(days=365)
        
        player = Player(
            user_id=user.id,
            name=name,
            gender=gender,
            age_category=age_category,
            dob=dob,
            email=email,
            contact_number=contact_number,
            nationality=nationality,
            height=height,
            weight=weight,
            blood_group=blood_group,
            address=address,
            coach=coach,
            academy=academy,
            registration_no=reg_no,
            registration_date=registration_date,
            registration_validity=registration_validity,
            current_status='Active'
        )
        db.session.add(player)
        db.session.commit()

        flash('Registration successful! Your player profile has been generated. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    g.current_user = None
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/request-admin', methods=['POST'])
@login_required
def request_admin():
    user = get_current_user()
    if user.role == 'user':
        user.admin_requested = not user.admin_requested
        db.session.commit()
        if user.admin_requested:
            flash('Admin access requested. A superadmin will review your request.', 'success')
        else:
            flash('Admin access request cancelled.', 'info')
    return redirect(request.referrer or url_for('main.index'))

@auth_bp.route('/admin/users')
@login_required
@role_required('superadmin')
def user_management():
    users = User.query.order_by(User.role.desc(), User.username).all()
    return render_template('auth/users.html', users=users)

@auth_bp.route('/admin/users/<int:user_id>/grant', methods=['POST'])
@login_required
@role_required('superadmin')
def grant_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'user':
        user.role = 'admin'
        user.admin_requested = False
        db.session.commit()
        flash(f'Granted admin privileges to {user.username}.', 'success')
    return redirect(url_for('auth.user_management'))

@auth_bp.route('/admin/users/<int:user_id>/revoke', methods=['POST'])
@login_required
@role_required('superadmin')
def revoke_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        user.role = 'user'
        db.session.commit()
        flash(f'Revoked admin privileges from {user.username}.', 'info')
    return redirect(url_for('auth.user_management'))

@auth_bp.route('/profile')
@login_required
def profile():
    user = get_current_user()
    users = []
    if user.role == 'superadmin':
        users = User.query.order_by(User.username).all()
    return render_template('auth/profile.html', user=user, users=users)

@auth_bp.route('/profile/clear_database', methods=['POST'])
@login_required
@role_required('superadmin')
def clear_user_database():
    target_user_id = request.form.get('user_id', type=int)
    if not target_user_id:
        flash('No user selected.', 'error')
        return redirect(url_for('auth.profile'))
        
    target_user = User.query.get_or_404(target_user_id)
    
    from app.domain.models import Tournament, Player
    
    try:
        # Delete user's players
        Player.query.filter_by(user_id=target_user.id).delete()
        
        # Get user's tournaments
        tournaments = Tournament.query.filter_by(user_id=target_user.id).all()
        for t in tournaments:
            db.session.delete(t) # Cascade delete will handle related models
            
        db.session.commit()
        flash(f"Successfully cleared all data for user {target_user.username}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error clearing data: {str(e)}", "error")
        
    return redirect(url_for('auth.profile'))


@auth_bp.route('/admin/audit-logs')
@login_required
@role_required('superadmin')
def view_audit_logs():
    page = request.args.get('page', 1, type=int)
    # Paginate descending so newest are first
    pagination = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50, error_out=False)
    return render_template('auth/audit_logs.html', pagination=pagination)


@auth_bp.route('/t/<slug>/score-login', methods=['GET', 'POST'])
@auth_bp.route('/tournaments/<slug>/score-login', methods=['GET', 'POST'])
def court_score_login(slug):
    """Allow court umpires/officials to sign in using a 6-digit court access PIN."""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    if request.method == 'POST':
        pin = request.form.get('pin', '').strip()
        if not pin or len(pin) != 6 or not pin.isdigit():
            flash('Please enter a valid 6-digit PIN.', 'error')
            return render_template('auth/score_login.html', tournament=tournament)

        staff = TournamentStaff.query.filter_by(
            tournament_id=tournament.id,
            access_pin=pin
        ).first()

        if not staff:
            flash('Invalid access PIN for this tournament.', 'error')
            return render_template('auth/score_login.html', tournament=tournament)

        if staff.pin_expires_at and staff.pin_expires_at < datetime.utcnow():
            flash('This court access PIN has expired. Please request a new PIN from the tournament organizer.', 'error')
            return render_template('auth/score_login.html', tournament=tournament)

        session[f"court_pin_staff_{tournament.id}"] = {
            "staff_id": staff.id,
            "court": staff.assigned_court,
            "role": staff.role
        }
        court_label = f" for {staff.assigned_court}" if staff.assigned_court else ""
        flash(f'Court Scoring Mode activated{court_label}.', 'success')
        return redirect(url_for('tournament.order_of_play', slug=tournament.url_slug))

    return render_template('auth/score_login.html', tournament=tournament)


@auth_bp.route('/t/<slug>/score-logout')
@auth_bp.route('/tournaments/<slug>/score-logout')
def court_score_logout(slug):
    """End court scoring session."""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    session.pop(f"court_pin_staff_{tournament.id}", None)
    flash('Exited Court Scoring Mode.', 'info')
    return redirect(url_for('tournament.view_tournament', slug=tournament.url_slug))
