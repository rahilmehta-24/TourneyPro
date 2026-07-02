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
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
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
        username = request.form.get('username')
        email = request.form.get('email')
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
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
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
