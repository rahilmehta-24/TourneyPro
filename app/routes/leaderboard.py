from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import db, Player, PlayerTournamentRecord
from sqlalchemy import desc

leaderboard_bp = Blueprint('leaderboard', __name__, url_prefix='/leaderboard')

@leaderboard_bp.route('/')
def view_leaderboard():
    category_filter = request.args.get('category', 'All')
    gender_filter = request.args.get('gender', 'All')

    query = Player.query
    if category_filter != 'All':
        query = query.filter_by(age_category=category_filter)
    if gender_filter != 'All':
        query = query.filter_by(gender=gender_filter)

    players = query.order_by(desc(Player.total_points)).all()

    categories = ['U8', 'U10', 'U12', 'U14', 'U18', 'Open']
    genders = ['Boys', 'Girls', 'Mens', 'Womens']

    # Map rounds for dropdown
    rounds = ['Round 1', 'Round 2', 'Round 3', 'Round 4', 'Quarter-Final', 'Semi-Final', 'Runner-Up', 'Winner']
    levels = ['Regular', 'State', 'National']

    return render_template('leaderboard/index.html',
                           players=players,
                           current_category=category_filter,
                           current_gender=gender_filter,
                           categories=categories,
                           genders=genders,
                           rounds=rounds,
                           levels=levels)

@leaderboard_bp.route('/add_player', methods=['POST'])
def add_player():
    name = request.form.get('name')
    gender = request.form.get('gender')
    age_category = request.form.get('age_category')

    if name and gender and age_category:
        player = Player(name=name, gender=gender, age_category=age_category)
        db.session.add(player)
        db.session.commit()
        flash('Player added successfully!', 'success')
    else:
        flash('Missing required fields.', 'error')

    return redirect(url_for('leaderboard.view_leaderboard', category=age_category, gender=gender))

@leaderboard_bp.route('/add_points/<int:player_id>', methods=['POST'])
def add_points(player_id):
    player = Player.query.get_or_404(player_id)

    tournament_name = request.form.get('tournament_name')
    level = request.form.get('level', 'Regular')
    round_reached = request.form.get('round_reached')
    matches_won = int(request.form.get('matches_won', 0) or 0)
    matches_lost = int(request.form.get('matches_lost', 0) or 0)

    if not tournament_name or not round_reached:
        flash('Tournament name and round reached are required.', 'error')
        return redirect(url_for('leaderboard.view_leaderboard'))

    base_points = {
        'Round 1': 5,
        'Round 2': 10,
        'Round 3': 20,
        'Round 4': 40,
        'Quarter-Final': 80,
        'Semi-Final': 160,
        'Runner-Up': 300,
        'Winner': 500
    }

    multiplier = {
        'Regular': 1.0,
        'State': 1.5,
        'National': 3.0
    }

    pts = base_points.get(round_reached, 0) * multiplier.get(level, 1.0)

    record = PlayerTournamentRecord(
        player_id=player.id,
        tournament_name=tournament_name,
        level=level,
        round_reached=round_reached,
        points_earned=pts,
        is_manual=True
    )

    player.total_points += pts
    player.matches_won += matches_won
    player.matches_lost += matches_lost
    player.matches_played += (matches_won + matches_lost)

    db.session.add(record)
    db.session.commit()

    flash(f'Points added for {player.name} successfully!', 'success')
    return redirect(url_for('leaderboard.view_leaderboard', category=player.age_category, gender=player.gender))
