from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.routes.auth import login_required, get_current_user, role_required
from app.models import Player, db

player_bp = Blueprint('player', __name__)

@player_bp.route('/player/<int:player_id>')
def view_player(player_id):
    player = Player.query.get_or_404(player_id)
    return render_template('player/view.html', player=player)

@player_bp.route('/player/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    # If the user doesn't have a linked player profile, they can create one or we can manage their multiple profiles
    # For now, let's assume a 1-to-many relationship, and the dashboard lists all players they manage
    current_user = get_current_user()
    players = Player.query.filter_by(user_id=current_user.id).all()
    
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
            p.name = request.form.get('name', p.name)
            p.gender = request.form.get('gender', p.gender)
            p.age_category = request.form.get('age_category', p.age_category)
            p.dob = parse_date(request.form.get('dob'))
            p.email = request.form.get('email', p.email)
            p.contact_number = request.form.get('contact_number', p.contact_number)
            p.height = request.form.get('height', p.height)
            p.weight = request.form.get('weight', p.weight)
            p.blood_group = request.form.get('blood_group', p.blood_group)
            p.nationality = request.form.get('nationality', p.nationality)
            p.address = request.form.get('address', p.address)
            p.coach = request.form.get('coach', p.coach)
            p.academy = request.form.get('academy', p.academy)
            
        action = request.form.get('action')
        
        if action == 'update_profile':
            
            player_id = request.form.get('player_id', type=int)
            player = Player.query.filter_by(id=player_id, user_id=current_user.id).first_or_404()
            populate_player_from_request(player)
            
            # Handle profile photo (Vercel is read-only, so we accept a URL instead of a file)
            avatar_url = request.form.get('avatar_url')
            if avatar_url:
                player.avatar_url = avatar_url
                    
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('player.dashboard'))
            
    return render_template('player/dashboard.html', players=players)


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
