from flask import Blueprint, render_template, request, flash, redirect, url_for, make_response
from app.models import db, Player, PlayerTournamentRecord, Participant
from sqlalchemy import desc
from app.routes.auth import login_required, role_required, get_current_user, check_player_ownership
from datetime import datetime
import openpyxl
from io import BytesIO

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
    genders = ['Boys', 'Girls', 'Mens', 'Womens', 'Mix']

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
@login_required
@role_required('admin', 'superadmin')
def add_player():
    name = request.form.get('name')
    gender = request.form.get('gender')
    age_category = request.form.get('age_category')

    if name and gender and age_category:
        player = Player()
        player.user_id = get_current_user().id
        player.name = name
        player.gender = gender
        player.age_category = age_category
        db.session.add(player)
        db.session.commit()
        flash('Player added successfully!', 'success')
    else:
        flash('Missing required fields.', 'error')

    return redirect(url_for('leaderboard.view_leaderboard', category=age_category, gender=gender))

@leaderboard_bp.route('/add_points/<int:player_id>', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def add_points(player_id):
    player = Player.query.get_or_404(player_id)
    check_player_ownership(player)

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

    record = PlayerTournamentRecord()
    record.player_id = player.id
    record.tournament_name = tournament_name
    record.level = level
    record.round_reached = round_reached
    record.points_earned = pts
    record.is_manual = True

    player.total_points += pts
    player.matches_won += matches_won
    player.matches_lost += matches_lost
    player.matches_played += (matches_won + matches_lost)

    db.session.add(record)
    db.session.commit()

    flash(f'Points added for {player.name} successfully!', 'success')
    return redirect(url_for('leaderboard.view_leaderboard', category=player.age_category, gender=player.gender))

@leaderboard_bp.route('/reset', methods=['POST'])
@login_required
@role_required('superadmin')
def reset_leaderboard():
    PlayerTournamentRecord.query.delete()
    Participant.query.update({'player_id': None})
    Player.query.delete()
    db.session.commit()
    flash('Leaderboard has been completely reset.', 'success')
    return redirect(url_for('leaderboard.view_leaderboard'))

@leaderboard_bp.route('/player/<int:player_id>/edit', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    check_player_ownership(player)
    player.name = request.form.get('name')
    player.gender = request.form.get('gender')
    player.age_category = request.form.get('age_category')
    db.session.commit()
    flash(f'Player {player.name} updated successfully.', 'success')
    return redirect(url_for('leaderboard.view_leaderboard', category=player.age_category, gender=player.gender))

@leaderboard_bp.route('/player/<int:player_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    check_player_ownership(player)
    Participant.query.filter_by(player_id=player.id).update({'player_id': None})
    db.session.delete(player)
    db.session.commit()
    flash('Player deleted successfully.', 'success')
    return redirect(url_for('leaderboard.view_leaderboard'))

@leaderboard_bp.route('/export')
@login_required
@role_required('superadmin')
def export_leaderboard():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if not start_date_str or not end_date_str:
        flash('Please select a date range to export.', 'error')
        return redirect(url_for('leaderboard.view_leaderboard'))
        
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        end_date = end_date.replace(hour=23, minute=59, second=59)
    except (ValueError, TypeError):
        flash('Invalid date range provided.', 'error')
        return redirect(url_for('leaderboard.view_leaderboard'))
        
    records = PlayerTournamentRecord.query.filter(
        PlayerTournamentRecord.date_recorded >= start_date,
        PlayerTournamentRecord.date_recorded <= end_date
    ).all()
    
    # Group points by player
    player_stats = {}
    for r in records:
        if r.player_id not in player_stats:
            player = Player.query.get(r.player_id)
            if not player:
                continue
            player_stats[r.player_id] = {
                'name': player.name,
                'gender': player.gender,
                'category': player.age_category,
                'points': 0
            }
        player_stats[r.player_id]['points'] += r.points_earned
        
    # Group by sheet (Category + Gender)
    sheets_data = {}
    for pid, stats in player_stats.items():
        sheet_name = f"{stats['category']} {stats['gender']}"
        if sheet_name not in sheets_data:
            sheets_data[sheet_name] = []
        sheets_data[sheet_name].append(stats)
        
    wb = openpyxl.Workbook()
    
    if not sheets_data:
        ws = wb.active
        ws.title = "No Data"
        ws.append(["No records found in this date range."])
    else:
        # Remove default sheet
        wb.remove(wb.active)
        for sheet_name, p_list in sheets_data.items():
            # openpyxl limits sheet names to 31 characters
            ws = wb.create_sheet(title=sheet_name[:31])
            ws.append(['Rank', 'Player Name', 'Category', 'Gender', 'Points Earned (In Range)'])
            # Sort by points desc
            p_list.sort(key=lambda x: x['points'], reverse=True)
            for i, p in enumerate(p_list, 1):
                ws.append([i, p['name'], p['category'], p['gender'], p['points']])
                
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=Leaderboard_Export_{start_date_str}_to_{end_date_str}.xlsx'
    return response
