from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.routes.auth import login_required, get_current_user
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
        action = request.form.get('action')
        if action == 'update_profile':
            player_id = request.form.get('player_id', type=int)
            player = Player.query.filter_by(id=player_id, user_id=current_user.id).first_or_404()
            player.avatar_url = request.form.get('avatar_url')
            player.bio = request.form.get('bio')
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('player.dashboard'))
            
    return render_template('player/dashboard.html', players=players)
