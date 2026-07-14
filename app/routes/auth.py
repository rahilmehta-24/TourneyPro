import os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, abort
from app.models import db, User

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

        # Validation
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
        from app.models import Player
        from datetime import datetime
        
        name = request.form.get('name', username)
        gender = request.form.get('gender', 'Male')
        if gender not in ['Male', 'Female']:
            gender = 'Male'
            
        dob_str = request.form.get('dob')
        dob = None
        age_category = 'Open'
        
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                from datetime import date
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
            except ValueError:
                pass
                
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
    
    from app.models import Tournament, Player
    
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
