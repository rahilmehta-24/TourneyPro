import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, abort
from app.domain.models import db, User, Tournament, TournamentStaff, AcademyMember, Player, AuditLog
from app.services.rbac_service import is_team_captain
from app.services.utils.validation import (
    validate_name, validate_username, validate_email, validate_password,
    validate_dob, validate_mobile
)

auth_bp = Blueprint('auth', __name__)

def get_current_user():
    if 'user_id' in session:
        user_id = session['user_id']
        if not hasattr(g, 'current_user') or g.current_user is None or getattr(g.current_user, 'id', None) != user_id:
            g.current_user = db.session.get(User, user_id)
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
    role_aliases = {
        "tournament_admin": "manager",
        "desk": "official",
        "umpire": "scorer"
    }
    canonical_min = role_aliases.get(min_role, min_role)
    if canonical_min not in role_weights:
        raise ValueError(f"Invalid min_role specified: {min_role}")
    min_weight = role_weights[canonical_min]

    # 3. Check TournamentStaff table for logged-in user
    if user:
        staff = TournamentStaff.query.filter_by(
            tournament_id=tournament.id,
            user_id=user.id
        ).first()
        if staff:
            canonical_staff = role_aliases.get(staff.role, staff.role)
            staff_weight = role_weights.get(canonical_staff, 0)
            if staff_weight >= min_weight:
                return True

    # 4. Check temporary Court PIN session
    pin_session_key = f"court_pin_staff_{tournament.id}"
    if pin_session_key in session:
        pin_data = session[pin_session_key]
        staff = db.session.get(TournamentStaff, pin_data.get("staff_id"))
        if staff and staff.tournament_id == tournament.id:
            if not staff.pin_expires_at or staff.pin_expires_at > datetime.utcnow():
                canonical_staff = role_aliases.get(staff.role, staff.role)
                staff_weight = role_weights.get(canonical_staff, 0)
                if staff_weight >= min_weight:
                    return True
            else:
                session.pop(pin_session_key, None)

    # Deny access
    if not user and pin_session_key not in session:
        abort(401)
    abort(403)


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
    """Create default superadmin user from environment variables if no users exist, or sync email"""
    superadmin_email = os.environ.get('SUPERADMIN_EMAIL') or 'rahilmehta.ict19@gmail.com'
    # Check if database has any users
    if User.query.count() == 0:
        username = os.environ.get('SUPERADMIN_USERNAME') or 'superadmin'
        password = os.environ.get('SUPERADMIN_PASSWORD') or 'adminpassword'

        superadmin = User(
            username=username,
            email=superadmin_email,
            role='superadmin'
        )
        superadmin.set_password(password)
        db.session.add(superadmin)
        db.session.commit()
        print(f"=== BOOTSTRAP === Created superadmin user: '{username}' with role 'superadmin'")
    else:
        # Sync email if default superadmin has legacy tourneypro or placeholder email
        admin = User.query.filter_by(role='superadmin').first()
        if admin and (not admin.email or 'tourneypro.com' in admin.email or admin.email == 'superadmin@baselinesociety.com'):
            admin.email = superadmin_email
            db.session.commit()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if get_current_user():
        return redirect(url_for('player.dashboard'))

    if request.method == 'POST':
        from app.services.utils.rate_limiter import check_rate_limit, get_client_ip, reset_rate_limit
        client_ip = get_client_ip()
        allowed, retry_after = check_rate_limit(f"web_login_{client_ip}", max_requests=10, window_seconds=60)
        if not allowed:
            flash(f"Too many login attempts. Please wait {retry_after} seconds before trying again.", "error")
            return render_template('auth/login.html')

        username = request.form.get('username', '').strip()
        password = request.form.get('password')

        user = User.query.filter(db.or_(User.username.ilike(username), User.email.ilike(username))).first()
        
        if user and (user.role == 'deleted' or user.username == 'anonymous_registrations' or user.email in ('anonymous@tourneypro.com', 'anonymous@thebaselinesociety.com')):
            flash('Invalid username or password.', 'error')
            return redirect(url_for('auth.login'))
            
        if user and user.check_password(password):
            reset_rate_limit(f"web_login_{client_ip}")
            # Session fixation protection: clear existing session first
            session.clear()
            session['user_id'] = user.id
            session.permanent = True
            g.current_user = user

            # Step 1-3: Verify profile exists for authenticated user; initialize if missing
            from app.services.user_service import ensure_user_profile
            ensure_user_profile(user.id)

            flash(f'Welcome back, {user.username}!', 'success')
            next_url = request.args.get('next') or request.form.get('next')
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            # Redirect authenticated user to their own profile dashboard
            return redirect(url_for('player.dashboard'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if get_current_user():
        return redirect(url_for('player.dashboard'))

    next_url = request.args.get('next') or request.form.get('next') or ''

    if request.method == 'POST':
        from app.services.utils.rate_limiter import check_rate_limit, get_client_ip, reset_rate_limit
        client_ip = get_client_ip()
        allowed, retry_after = check_rate_limit(f"web_register_{client_ip}", max_requests=10, window_seconds=60)
        if not allowed:
            flash(f"Too many registration attempts. Please wait {retry_after} seconds before trying again.", "error")
            return render_template('auth/register.html', next_url=next_url)

        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        name = request.form.get('name', username).strip() or username
        contact_number = request.form.get('contact_number', '').strip()
        registration_intent = request.form.get('registration_intent', 'user').strip().lower()
        if registration_intent not in ('user', 'player'):
            registration_intent = 'user'

        ok, u_clean = validate_username(username)
        if not ok:
            flash(u_clean, 'error')
            return render_template('auth/register.html', next_url=next_url)
        username = u_clean

        ok, e_clean = validate_email(email, required=True)
        if not ok:
            flash(e_clean, 'error')
            return render_template('auth/register.html', next_url=next_url)
        email = e_clean

        ok, p_clean = validate_password(password, min_length=8)
        if not ok:
            flash(p_clean, 'error')
            return render_template('auth/register.html', next_url=next_url)

        if password_confirm is not None and password != password_confirm:
            flash('Passwords do not match. Please verify your password.', 'error')
            return render_template('auth/register.html', next_url=next_url)

        ok, n_clean = validate_name(name, min_len=2, field_name="Full Name")
        if not ok:
            flash(n_clean, 'error')
            return render_template('auth/register.html', next_url=next_url)
        name = n_clean

        if contact_number:
            ok, mob_clean = validate_mobile(contact_number, required=False)
            if not ok:
                flash(mob_clean, 'error')
                return render_template('auth/register.html', next_url=next_url)
            contact_number = mob_clean

        dob_str = request.form.get('dob', '').strip()
        dob = None
        if dob_str:
            ok, dob_res = validate_dob(dob_str, field_name="Date of Birth")
            if not ok:
                flash(dob_res, 'error')
                return render_template('auth/register.html', next_url=next_url)
            dob = dob_res

        from app.services.user_service import register_user
        result = register_user(
            username=username,
            email=email,
            password=password,
            password_confirm=password_confirm,
            full_name=name,
            registration_intent=registration_intent,
            gender=request.form.get('gender'),
            dob=dob,
            contact_number=contact_number,
            nationality=request.form.get('nationality'),
            height=request.form.get('height'),
            weight=request.form.get('weight'),
            blood_group=request.form.get('blood_group'),
            address=request.form.get('address'),
            coach=request.form.get('coach'),
            academy=request.form.get('academy')
        )

        if not result.success:
            flash(result.message, 'error')
            return render_template('auth/register.html', next_url=next_url)

        reset_rate_limit(f"web_register_{client_ip}")
        flash(result.message, result.category)
        if next_url and next_url.startswith('/') and not next_url.startswith('//'):
            return redirect(url_for('auth.login', next=next_url))
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', next_url=next_url)

@auth_bp.route('/profile/complete', methods=['GET', 'POST'])
@login_required
def complete_profile():
    """Stage 2 Profile Completion Gateway."""
    user = get_current_user()
    next_url = request.args.get('next') or request.form.get('next') or ''

    player = Player.query.filter_by(user_id=user.id).first()

    from app.domain.constants import COMPETITION_CATEGORIES, AGE_CATEGORIES

    if request.method == 'POST':
        full_name = request.form.get('full_name', user.full_name or user.username).strip()
        gender = request.form.get('gender', '').strip()
        dob_str = request.form.get('dob', '').strip()
        contact_number = request.form.get('contact_number', '').strip()
        primary_sport = request.form.get('primary_sport', 'Tennis').strip()
        skill_level = request.form.get('skill_level', '').strip()
        preferred_competition_category = request.form.get('preferred_competition_category', '').strip()
        emergency_contact_name = request.form.get('emergency_contact_name', '').strip()
        emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip()
        nationality = request.form.get('nationality', '').strip()
        height = request.form.get('height', '').strip()
        weight = request.form.get('weight', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        address = request.form.get('address', '').strip()
        academy = request.form.get('academy', '').strip()
        coach = request.form.get('coach', '').strip()

        ok, n_clean = validate_name(full_name, min_len=2, field_name="Full Name")
        if not ok:
            flash(n_clean, 'error')
            return render_template(
                'auth/complete_profile.html',
                user=user,
                player=player,
                next_url=next_url,
                competition_categories=COMPETITION_CATEGORIES,
                age_categories=AGE_CATEGORIES
            )

        if not gender or gender not in ('Male', 'Female', 'Other'):
            flash('Please select a valid gender.', 'error')
            return render_template(
                'auth/complete_profile.html',
                user=user,
                player=player,
                next_url=next_url,
                competition_categories=COMPETITION_CATEGORIES,
                age_categories=AGE_CATEGORIES
            )

        ok, dob_clean = validate_dob(dob_str, field_name="Date of Birth")
        if not ok:
            flash(dob_clean, 'error')
            return render_template(
                'auth/complete_profile.html',
                user=user,
                player=player,
                next_url=next_url,
                competition_categories=COMPETITION_CATEGORIES,
                age_categories=AGE_CATEGORIES
            )

        ok, mob_clean = validate_mobile(contact_number, required=True, field_name="Mobile Number")
        if not ok:
            flash(mob_clean, 'error')
            return render_template(
                'auth/complete_profile.html',
                user=user,
                player=player,
                next_url=next_url,
                competition_categories=COMPETITION_CATEGORIES,
                age_categories=AGE_CATEGORIES
            )

        from app.services.user_service import complete_player_profile
        res = complete_player_profile(
            user_id=user.id,
            full_name=n_clean,
            gender=gender,
            dob=dob_clean,
            contact_number=mob_clean,
            primary_sport=primary_sport,
            skill_level=skill_level or None,
            preferred_competition_category=preferred_competition_category or None,
            emergency_contact_name=emergency_contact_name or None,
            emergency_contact_phone=emergency_contact_phone or None,
            nationality=nationality or None,
            height=height or None,
            weight=weight or None,
            blood_group=blood_group or None,
            address=address or None,
            academy=academy or None,
            coach=coach or None,
        )

        if not res.get("success"):
            flash(res.get("message", "Profile completion failed."), "error")
            return render_template(
                'auth/complete_profile.html',
                user=user,
                player=player,
                next_url=next_url,
                competition_categories=COMPETITION_CATEGORIES,
                age_categories=AGE_CATEGORIES
            )

        flash(res.get("message"), "success")
        if next_url and next_url.startswith('/') and not next_url.startswith('//'):
            return redirect(next_url)
        return redirect(url_for('player.dashboard'))

    return render_template(
        'auth/complete_profile.html',
        user=user,
        player=player,
        next_url=next_url,
        competition_categories=COMPETITION_CATEGORIES,
        age_categories=AGE_CATEGORIES
    )

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    from app.services.user_service import verify_user_email
    res = verify_user_email(token)
    if res.get("success"):
        flash(res.get("message"), "success")
    else:
        flash(res.get("message"), "error")
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        ok, e_clean = validate_email(email, required=True)
        if not ok:
            flash(e_clean, 'error')
            return render_template('auth/forgot_password.html')

        from app.services.user_service import request_password_reset
        res = request_password_reset(e_clean)
        flash(res.get("message"), "info")
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        from app.services.user_service import reset_password_with_token
        res = reset_password_with_token(token, password, password_confirm)
        if res.get("success"):
            flash(res.get("message"), "success")
            return redirect(url_for('auth.login'))
        else:
            flash(res.get("message"), "error")
            return render_template('auth/reset_password.html', token=token)
    return render_template('auth/reset_password.html', token=token)

@auth_bp.route('/logout')
def logout():
    session.clear()
    g.current_user = None
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/organizer/activate', methods=['POST'])
@login_required
def activate_organizer():
    """Self-service tournament organizer activation with fair play agreement and auditing."""
    user = get_current_user()
    org_name = request.form.get('organization_name', '').strip()
    contact_phone = request.form.get('contact_phone', '').strip()
    agreed_terms = request.form.get('agreed_terms')

    if not org_name or len(org_name) < 3:
        flash('Organization, club, or host name must be at least 3 characters.', 'error')
        return redirect(request.referrer or url_for('player.dashboard'))

    if not agreed_terms:
        flash('You must agree to the Tournament Organizer Fair Play & Security terms.', 'error')
        return redirect(request.referrer or url_for('player.dashboard'))

    # Update role to admin/organizer
    user.role = 'admin'
    user.admin_requested = False

    player = Player.query.filter_by(user_id=user.id).first()
    if player:
        if not player.academy:
            player.academy = org_name
        if contact_phone and not player.contact_number:
            player.contact_number = contact_phone

    from app.services.utils.audit import log_audit
    log_audit(
        action_type="organizer_self_activation",
        target_id=user.id,
        target_name=user.username,
        reason="Self-Service Organizer Activation",
        explanation=f"User activated tournament organizer status for club/org '{org_name}'.",
        user_id=user.id
    )

    db.session.commit()
    flash(f"Organizer status activated! Welcome to the Baseline Society Tournament Host Network, {org_name}.", "success")
    return redirect(url_for('tournament.create_tournament'))

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
@role_required('superadmin', 'support')
def user_management():
    users = User.query.order_by(User.role.desc(), User.username).all()
    return render_template('auth/users.html', users=users)

@auth_bp.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@role_required('superadmin')
def create_user_admin():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        full_name = request.form.get('full_name')

        from app.services.user_service import admin_create_user
        result = admin_create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            full_name=full_name
        )

        flash(result.message, result.category)
        return redirect(url_for('auth.user_management'))

    return redirect(url_for('auth.user_management'))

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

@auth_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('superadmin')
def delete_user(user_id):
    current_user = get_current_user()
    if current_user.id == user_id:
        flash('You cannot delete your own superadmin account.', 'error')
        return redirect(url_for('auth.user_management'))
    
    target_user = User.query.get_or_404(user_id)
    username = target_user.username
    try:
        from app.domain.models import (
            DeviceRegistration, InAppNotification, UserNotificationPreferences,
            TournamentStaff, Player, Tournament
        )
        
        # Scrub device tokens, notifications, and preferences
        DeviceRegistration.query.filter_by(user_id=target_user.id).delete()
        InAppNotification.query.filter_by(user_id=target_user.id).delete()
        UserNotificationPreferences.query.filter_by(user_id=target_user.id).delete()
        TournamentStaff.query.filter_by(user_id=target_user.id).delete()
        
        # Unlink associated player profiles to retain tournament records
        Player.query.filter_by(user_id=target_user.id).update({'user_id': None})
        
        # Reassign owned tournaments to active superadmin to preserve tournament data
        owned_tournaments = Tournament.query.filter_by(user_id=target_user.id).all()
        for t in owned_tournaments:
            t.user_id = current_user.id
            
        db.session.delete(target_user)
        db.session.commit()
        flash(f'User account "{username}" has been permanently deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user "{username}": {str(e)}', 'error')
        
    return redirect(url_for('auth.user_management'))

@auth_bp.route('/admin/users/<int:user_id>/role', methods=['POST'])
@login_required
@role_required('superadmin')
def change_user_role(user_id):
    current_user = get_current_user()
    target_user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', '').strip().lower()
    
    if new_role not in ['user', 'support', 'admin', 'superadmin']:
        flash('Invalid role selected.', 'error')
        return redirect(url_for('auth.user_management'))
        
    if target_user.id == current_user.id and new_role != 'superadmin':
        flash('You cannot demote your own superadmin account.', 'error')
        return redirect(url_for('auth.user_management'))
        
    old_role = target_user.role
    target_user.role = new_role
    if new_role in ['admin', 'superadmin']:
        target_user.admin_requested = False
        
    db.session.commit()
    flash(f'Role for "{target_user.username}" updated from {old_role.upper()} to {new_role.upper()}.', 'success')
    return redirect(url_for('auth.user_management'))

@auth_bp.route('/admin/users/<int:user_id>/reject_admin', methods=['POST'])
@login_required
@role_required('superadmin')
def reject_admin_request(user_id):
    user = User.query.get_or_404(user_id)
    user.admin_requested = False
    db.session.commit()
    flash(f'Admin request for {user.username} has been rejected.', 'info')
    return redirect(url_for('auth.user_management'))

@auth_bp.route('/admin/platform/academies/applications')
@login_required
@role_required('superadmin', 'support')
def platform_academy_applications():
    """Platform Console: View and manage academy verification applications."""
    from app.domain.models import AcademyApplication
    status_filter = request.args.get('status')
    query = AcademyApplication.query
    if status_filter:
        query = query.filter_by(status=status_filter.upper())
    applications = query.order_by(AcademyApplication.created_at.desc()).all()
    current_user = get_current_user()
    return render_template(
        'admin/platform/academy_applications.html',
        applications=applications,
        status_filter=status_filter,
        is_superadmin=(current_user.role == 'superadmin')
    )

@auth_bp.route('/admin/platform/academies/applications/<int:app_id>/review', methods=['POST'])
@login_required
@role_required('superadmin')
def platform_review_academy_application(app_id):
    """Platform Superadmin verifies or rejects an academy application."""
    from app.services.academy_service import review_academy_application
    current_user = get_current_user()
    decision = request.form.get('decision', '').strip().upper()
    rejection_reason = request.form.get('rejection_reason', '').strip()

    try:
        app_record, academy = review_academy_application(
            application_id=app_id,
            reviewer_user=current_user,
            decision=decision,
            rejection_reason=rejection_reason
        )
        if decision == 'APPROVED':
            flash(f"Academy '{academy.name}' successfully verified and activated!", "success")
        else:
            flash(f"Application for '{app_record.name}' was rejected with reason recorded.", "info")
    except (ValueError, PermissionError) as e:
        flash(str(e), "error")

    return redirect(url_for('auth.platform_academy_applications'))

@auth_bp.route('/profile')
@login_required
def profile():
    user = get_current_user()
    if not user.profile_completed and user.role not in ['admin', 'superadmin']:
        flash("Please complete your profile to view your full profile.", "info")
        return redirect(url_for('auth.complete_profile', next=url_for('auth.profile')))
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
