from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
from models import db, Tournament, Participant, Match, TournamentSettings, Category, Group
from config import Config
from slugify import slugify
from datetime import datetime
from xhtml2pdf import pisa
from io import BytesIO
from algorithms.single_elimination import generate_single_elimination, calculate_final_rankings
from algorithms.double_elimination import generate_double_elimination, calculate_double_elimination_rankings
from algorithms.round_robin import generate_round_robin, calculate_round_robin_standings
from algorithms.group_stage import generate_group_stage, generate_knockout_from_groups, calculate_group_standings
import os

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create database tables
with app.app_context():
    db.create_all()

# Format definitions
TOURNAMENT_FORMATS = {
    'single_elimination': {
        'name': 'Single Elimination',
        'description': 'Participants are eliminated after one loss',
        'icon': '🏆',
        'min_participants': 2
    },
    'double_elimination': {
        'name': 'Double Elimination',
        'description': 'Participants must lose twice to be eliminated',
        'icon': '🥇',
        'min_participants': 3
    },
    'round_robin': {
        'name': 'Round Robin',
        'description': 'Every participant plays every other participant',
        'icon': '🔄',
        'min_participants': 3
    },
    'swiss': {
        'name': 'Swiss System',
        'description': 'Participants play opponents with similar records',
        'icon': '🎯',
        'min_participants': 4
    },
    'free_for_all': {
        'name': 'Free For All',
        'description': 'All participants compete simultaneously',
        'icon': '⚔️',
        'min_participants': 3
    },
    'leaderboard': {
        'name': 'Leaderboard',
        'description': 'Ranking-based competition',
        'icon': '📊',
        'min_participants': 2
    },
    'time_trial': {
        'name': 'Time Trial',
        'description': 'Individual time-based competition',
        'icon': '⏱️',
        'min_participants': 1
    },
    'single_race': {
        'name': 'Single Race',
        'description': 'One-off race with placement ranking',
        'icon': '🏁',
        'min_participants': 2
    },
    'grand_prix': {
        'name': 'Grand Prix',
        'description': 'Series of races with points system',
        'icon': '🏎️',
        'min_participants': 2
    },
    'group_stage': {
        'name': 'Group Stage + Knockout',
        'description': 'Group round-robin followed by knockout bracket',
        'icon': '🎪',
        'min_participants': 4
    }
}

@app.route('/')
def index():
    """Homepage with tournament list"""
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).limit(10).all()
    return render_template('index.html', tournaments=tournaments, formats=TOURNAMENT_FORMATS)

@app.route('/tournaments')
def tournament_list():
    """List all tournaments"""
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    return render_template('tournament/list.html', tournaments=tournaments, formats=TOURNAMENT_FORMATS)

@app.route('/tournaments/new', methods=['GET', 'POST'])
def create_tournament():
    """Create new tournament"""
    if request.method == 'POST':
        name = request.form.get('name')
        creator_name = request.form.get('creator_name', 'Anonymous')
        description = request.form.get('description', '')
        game_info = request.form.get('game_info', '')
        format_type = request.form.get('format')
        max_participants = request.form.get('max_participants', type=int)
        
        # Generate URL slug
        url_slug = slugify(name)
        
        # Check if slug already exists
        existing = Tournament.query.filter_by(url_slug=url_slug).first()
        if existing:
            url_slug = f"{url_slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create tournament
        tournament = Tournament(
            creator_name=creator_name,
            name=name,
            url_slug=url_slug,
            description=description,
            game_info=game_info,
            format=format_type,
            max_participants=max_participants
        )
        
        db.session.add(tournament)
        db.session.commit()
        
        # Create default settings
        settings = TournamentSettings(tournament_id=tournament.id)
        db.session.add(settings)
        db.session.commit()
        
        flash('Tournament created successfully!', 'success')
        return redirect(url_for('manage_tournament', slug=tournament.url_slug))
    
    return render_template('tournament/create.html', formats=TOURNAMENT_FORMATS)

@app.route('/tournaments/<slug>')
def view_tournament(slug):
    """View tournament bracket"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    participants = Participant.query.filter_by(tournament_id=tournament.id).order_by(Participant.seed).all()
    matches = Match.query.filter_by(tournament_id=tournament.id).order_by(Match.round, Match.match_number).all()
    
    # Group matches by round
    rounds = {}
    for match in matches:
        if match.round not in rounds:
            rounds[match.round] = []
        rounds[match.round].append(match)
    
   # Aggregate player registry data
    player_stats = {}
    if tournament.has_categories:
        for category in tournament.categories:
            for participant in category.participants:
                if participant.name not in player_stats:
                    player_stats[participant.name] = {
                        'name': participant.name,
                        'categories': [],
                        'total_matches': 0,
                        'total_wins': 0,
                        'placements': []
                    }
                
                player_stats[participant.name]['categories'].append(category.name)
                
                # Count matches
                matches_played = Match.query.filter(
                    Match.category_id == category.id,
                    ((Match.participant1_id == participant.id) | (Match.participant2_id == participant.id)),
                    Match.status == 'completed'
                ).count()
                player_stats[participant.name]['total_matches'] += matches_played
                
                # Count wins
                wins = Match.query.filter(
                    Match.category_id == category.id,
                    Match.winner_id == participant.id
                ).count()
                player_stats[participant.name]['total_wins'] += wins
                
                # Determine placement
                if category.status == 'completed':
                    cat_matches = category.matches
                    if cat_matches:
                        max_round = max([m.round for m in cat_matches])
                        finals = [m for m in cat_matches if m.round == max_round]
                        if finals and finals[0].winner_id == participant.id:
                            player_stats[participant.name]['placements'].append(('Champion', category.name))
                        elif finals and participant.id in [finals[0].participant1_id, finals[0].participant2_id]:
                            player_stats[participant.name]['placements'].append(('Runner-Up', category.name))
                        elif max_round >= 2:
                            semis = [m for m in cat_matches if m.round == max_round - 1]
                            for match in semis:
                                if participant.id in [match.participant1_id, match.participant2_id] and match.winner_id != participant.id:
                                    player_stats[participant.name]['placements'].append(('Semi-Finalist', category.name))
                                    break
    
    # Sort registry by wins
    player_registry = sorted(player_stats.values(), key=lambda x: x['total_wins'], reverse=True)
    
    # Sort placements for each player to find the "best" one
    placement_weights = {
        'Champion': 3,
        'Runner-Up': 2,
        'Semi-Finalist': 1
    }
    
    for player in player_registry:
        if player['placements']:
            player['placements'].sort(key=lambda x: placement_weights.get(x[0], 0), reverse=True)
    
    return render_template('tournament/view.html', 
                         tournament=tournament, 
                         participants=participants,
                         matches=matches,
                         rounds=rounds,
                         player_registry=player_registry,
                         formats=TOURNAMENT_FORMATS)

@app.route('/tournaments/<slug>/manage', methods=['GET', 'POST'])
def manage_tournament(slug):
    """Manage tournament (add participants, start tournament)"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    participants = Participant.query.filter_by(tournament_id=tournament.id).order_by(Participant.seed).all()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_participant':
            participant_name = request.form.get('participant_name')
            participant_email = request.form.get('participant_email', '')
            
            participant = Participant(
                tournament_id=tournament.id,
                name=participant_name,
                email=participant_email
            )
            db.session.add(participant)
            db.session.commit()
            
            flash(f'Added participant: {participant_name}', 'success')
            return redirect(url_for('manage_tournament', slug=slug))
        
        elif action == 'start_tournament':
            # Generate bracket based on format
            if tournament.format == 'single_elimination':
                matches_data = generate_single_elimination(participants)
                
                # Create match records
                for match_data in matches_data:
                    match = Match(**match_data, tournament_id=tournament.id)
                    db.session.add(match)
                
                tournament.status = 'in_progress'
                tournament.started_at = datetime.utcnow()
                db.session.commit()
                
                flash('Tournament started! Bracket generated.', 'success')
                return redirect(url_for('view_tournament', slug=slug))
            else:
                flash(f'Format "{tournament.format}" is not yet implemented. Coming soon!', 'warning')
        
        elif action == 'finish_tournament':
            tournament.status = 'completed'
            tournament.completed_at = datetime.utcnow()
            db.session.commit()
            
            flash('Tournament completed! 🏆', 'success')
            return redirect(url_for('view_tournament', slug=slug))
    
    
    # Calculate total unique players
    if tournament.has_categories:
        unique_players = set()
        for category in tournament.categories:
            for participant in category.participants:
                unique_players.add(participant.name)
        total_players = len(unique_players)
    else:
        # For non-category tournaments, participants are directly under the tournament
        total_players = len(participants)
    
    return render_template('tournament/manage.html', 
                         tournament=tournament, 
                         participants=participants,
                         total_players=total_players,
                         formats=TOURNAMENT_FORMATS)

@app.route('/tournaments/<slug>/match/<int:match_id>/report', methods=['POST'])
def report_match_result(slug, match_id):
    """Report match result"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    match = Match.query.get_or_404(match_id)
    
    winner_id = request.form.get('winner_id', type=int)
    score1 = request.form.get('score1', '')
    score2 = request.form.get('score2', '')
    
    match.winner_id = winner_id
    match.score1 = score1
    match.score2 = score2
    match.status = 'completed'
    match.completed_at = datetime.utcnow()
    
    # Update next round match
    if tournament.format == 'single_elimination':
        # Find next round match
        next_round = match.round + 1
        next_match_number = (match.match_number + 1) // 2
        
        next_match = Match.query.filter_by(
            tournament_id=tournament.id,
            round=next_round,
            match_number=next_match_number
        ).first()
        
        if next_match:
            # Determine which slot to fill (participant1 or participant2)
            if match.match_number % 2 == 1:
                next_match.participant1_id = winner_id
            else:
                next_match.participant2_id = winner_id
    
    db.session.commit()
    
    flash('Match result reported!', 'success')
    return redirect(url_for('view_tournament', slug=slug))

@app.route('/tournaments/<slug>/seeding', methods=['GET', 'POST'])
def manage_tournament_seeding(slug):
    """Manage manual seeding for tournament participants"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    participants = Participant.query.filter_by(tournament_id=tournament.id).all()
    
    if request.method == 'POST':
        # Update seeds from form
        for participant in participants:
            seed_key = f'seed_{participant.id}'
            if seed_key in request.form:
                new_seed = request.form.get(seed_key, type=int)
                participant.manual_seed = new_seed
        
        db.session.commit()
        flash('Seeding updated successfully!', 'success')
        return redirect(url_for('manage_tournament', slug=slug))
    
    return render_template('tournament/seeding.html',
                         tournament=tournament,
                         participants=participants)

@app.route('/tournaments/<slug>/delete', methods=['POST'])
def delete_tournament(slug):
    """Delete tournament"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    
    db.session.delete(tournament)
    db.session.commit()
    
    flash('Tournament deleted successfully!', 'info')
    return redirect(url_for('index'))

# ==================== CATEGORY ROUTES ====================

@app.route('/tournaments/<slug>/categories/new', methods=['GET', 'POST'])
def create_category(slug):
    """Create new category within tournament"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    
    if request.method == 'POST':
        name = request.form.get('name')
        format_type = request.form.get('format')
        max_participants = request.form.get('max_participants', type=int)
        
        # Group stage specific fields
        has_group_stage = format_type == 'group_stage'
        num_groups = request.form.get('num_groups', type=int) if has_group_stage else None
        teams_per_group = request.form.get('teams_per_group', type=int) if has_group_stage else None
        matches_per_team_pair = request.form.get('matches_per_team_pair', type=int, default=1) if has_group_stage else 1
        qualifiers_per_group = request.form.get('qualifiers_per_group', type=int) if has_group_stage else None
        
        category = Category(
            tournament_id=tournament.id,
            name=name,
            format=format_type,
            max_participants=max_participants,
            has_group_stage=has_group_stage,
            num_groups=num_groups,
            teams_per_group=teams_per_group,
            matches_per_team_pair=matches_per_team_pair,
            qualifiers_per_group=qualifiers_per_group
        )
        
        db.session.add(category)
        tournament.has_categories = True
        db.session.commit()
        
        flash(f'Category "{name}" created successfully!', 'success')
        return redirect(url_for('manage_category', slug=slug, category_id=category.id))
    
    return render_template('category/create.html', tournament=tournament, formats=TOURNAMENT_FORMATS)

@app.route('/tournaments/<slug>/categories/<int:category_id>')
def view_category(slug, category_id):
    """View category bracket/standings"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    participants = Participant.query.filter_by(category_id=category_id).order_by(Participant.seed).all()
    matches = Match.query.filter_by(category_id=category_id).order_by(Match.round, Match.match_number).all()
    
    # Group matches by round for knockout
    rounds = {}
    for match in matches:
        if match.match_type == 'knockout':
            if match.round not in rounds:
                rounds[match.round] = []
            rounds[match.round].append(match)
    
    # Get group stage data if applicable
    groups_data = None
    if category.has_group_stage:
        groups = Group.query.filter_by(category_id=category_id).all()
        groups_data = []
        for group in groups:
            standings = calculate_group_standings(group.id)
            group_matches = Match.query.filter_by(group_id=group.id, match_type='group_stage').all()
            groups_data.append({
                'group': group,
                'standings': standings,
                'matches': group_matches
            })
    
    # Calculate final rankings if tournament is complete
    rankings = None
    if category.status == 'completed':
        if category.format == 'single_elimination':
            rankings = calculate_final_rankings(category)
        elif category.format == 'double_elimination':
            rankings = calculate_double_elimination_rankings(category)
        elif category.format == 'round_robin':
            standings = calculate_round_robin_standings(category_id)
            if len(standings) >= 2:
                rankings = {
                    'winner': standings[0]['participant'],
                    'runner_up': standings[1]['participant'],
                    'semi_finalists': [s['participant'] for s in standings[2:4]] if len(standings) > 2 else []
                }
    
    return render_template('category/view.html',
                         tournament=tournament,
                         category=category,
                         participants=participants,
                         matches=matches,
                         rounds=rounds,
                         groups_data=groups_data,
                         rankings=rankings,
                         formats=TOURNAMENT_FORMATS)

@app.route('/tournaments/<slug>/categories/<int:category_id>/manage', methods=['GET', 'POST'])
def manage_category(slug, category_id):
    """Manage category participants and settings"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    participants = Participant.query.filter_by(category_id=category_id).order_by(Participant.manual_seed, Participant.seed).all()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_participant':
            participant_name = request.form.get('participant_name')
            participant_email = request.form.get('participant_email', '')
            manual_seed = request.form.get('manual_seed', type=int)
            
            # Check max participants limit
            if category.max_participants and len(participants) >= category.max_participants:
                flash(f'Cannot add participant. Maximum limit of {category.max_participants} reached.', 'error')
                return redirect(url_for('manage_category', slug=slug, category_id=category_id))
            
            participant = Participant(
                tournament_id=tournament.id,
                category_id=category.id,
                name=participant_name,
                email=participant_email,
                manual_seed=manual_seed
            )
            db.session.add(participant)
            db.session.commit()
            
            flash(f'Added participant: {participant_name}', 'success')
            return redirect(url_for('manage_category', slug=slug, category_id=category_id))
        
        elif action == 'start_category':
            participants_list = Participant.query.filter_by(category_id=category_id).all()
            
            if category.format == 'single_elimination':
                matches_data = generate_single_elimination(participants_list)
                for match_data in matches_data:
                    match = Match(**match_data, tournament_id=tournament.id, category_id=category.id)
                    db.session.add(match)
            
            elif category.format == 'double_elimination':
                matches_data = generate_double_elimination(participants_list)
                for match_data in matches_data:
                    match = Match(**match_data, tournament_id=tournament.id, category_id=category.id)
                    db.session.add(match)
            
            elif category.format == 'round_robin':
                matches_data = generate_round_robin(participants_list)
                for match_data in matches_data:
                    match = Match(**match_data, tournament_id=tournament.id, category_id=category.id)
                    db.session.add(match)
            
            elif category.format == 'group_stage':
                matches_data = generate_group_stage(category, participants_list)
                for match_data in matches_data:
                    match = Match(**match_data, tournament_id=tournament.id)
                    db.session.add(match)
            
            category.status = 'in_progress'
            category.started_at = datetime.utcnow()
            db.session.commit()
            
            flash('Category started! Bracket generated.', 'success')
            return redirect(url_for('view_category', slug=slug, category_id=category_id))
        
        elif action == 'finish_category':
            category.status = 'completed'
            category.completed_at = datetime.utcnow()
            db.session.commit()
            
            flash('Tournament completed! 🏆', 'success')
            return redirect(url_for('view_category', slug=slug, category_id=category_id))
    
    return render_template('category/manage.html',
                         tournament=tournament,
                         category=category,
                         participants=participants,
                         formats=TOURNAMENT_FORMATS)

@app.route('/tournaments/<slug>/categories/<int:category_id>/seeding', methods=['GET', 'POST'])
def manage_seeding(slug, category_id):
    """Manage manual seeding for participants"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    participants = Participant.query.filter_by(category_id=category_id).all()
    
    if request.method == 'POST':
        # Update seeds from form
        for participant in participants:
            seed_key = f'seed_{participant.id}'
            if seed_key in request.form:
                new_seed = request.form.get(seed_key, type=int)
                participant.manual_seed = new_seed
        
        db.session.commit()
        flash('Seeding updated successfully!', 'success')
        return redirect(url_for('manage_category', slug=slug, category_id=category_id))
    
    return render_template('category/seeding.html',
                         tournament=tournament,
                         category=category,
                         participants=participants)

@app.route('/tournaments/<slug>/categories/<int:category_id>/start-knockout', methods=['POST'])
def start_knockout_stage(slug, category_id):
    """Transition from group stage to knockout"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    
    if not category.has_group_stage:
        flash('This category does not have a group stage.', 'error')
        return redirect(url_for('view_category', slug=slug, category_id=category_id))
    
    # Generate knockout bracket from group qualifiers
    matches_data = generate_knockout_from_groups(category)
    
    for match_data in matches_data:
        match = Match(**match_data, tournament_id=tournament.id)
        db.session.add(match)
    
    db.session.commit()
    
    flash('Knockout stage started!', 'success')
    return redirect(url_for('view_category', slug=slug, category_id=category_id))

@app.route('/tournaments/<slug>/categories/<int:category_id>/match/<int:match_id>/report', methods=['POST'])
def report_category_match_result(slug, category_id, match_id):
    """Report match result for category"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    match = Match.query.get_or_404(match_id)
    
    winner_id = request.form.get('winner_id', type=int)
    score1 = request.form.get('score1', '')
    score2 = request.form.get('score2', '')
    
    match.winner_id = winner_id
    match.score1 = score1
    match.score2 = score2
    match.status = 'completed'
    match.completed_at = datetime.utcnow()
    
    # Update group stage stats if applicable
    if match.match_type == 'group_stage':
        winner = Participant.query.get(winner_id)
        if winner:
            winner.group_wins += 1
            winner.group_points += 3
        
        # Update loser
        loser_id = match.participant1_id if match.participant1_id != winner_id else match.participant2_id
        if loser_id:
            loser = Participant.query.get(loser_id)
            if loser:
                loser.group_losses += 1
    
    # Update next round match for knockout
    elif match.match_type == 'knockout' and category.format in ['single_elimination', 'double_elimination']:
        next_round = match.round + 1
        next_match_number = (match.match_number + 1) // 2
        
        next_match = Match.query.filter_by(
            category_id=category.id,
            round=next_round,
            match_number=next_match_number,
            bracket_type=match.bracket_type
        ).first()
        
        if next_match:
            if match.match_number % 2 == 1:
                next_match.participant1_id = winner_id
            else:
                next_match.participant2_id = winner_id
    
    # Check if category is completed
    all_matches = Match.query.filter_by(category_id=category_id).all()
    if all(m.status == 'completed' for m in all_matches):
        category.status = 'completed'
        category.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Match result reported!', 'success')
    return redirect(url_for('view_category', slug=slug, category_id=category_id))

@app.route('/tournaments/<slug>/category/<int:category_id>/export_pdf')
def export_category_pdf(slug, category_id):
    slug = slug.strip()  # Clean slug
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    
    # Verify category belongs to tournament
    if category.tournament_id != tournament.id:
        abort(404)
    
    # Group matches by round
    rounds = {}
    for match in category.matches:
        if match.round not in rounds:
            rounds[match.round] = []
        rounds[match.round].append(match)
    
    # Sort matches within rounds
    for r in rounds:
        rounds[r].sort(key=lambda x: x.match_number)
        
    # Render HTML for PDF
    html_out = render_template('export/bracket_pdf.html', 
                             tournament=tournament,
                             category=category,
                             rounds=rounds,
                             now=datetime.now())
    
    # Generate PDF
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html_out, dest=pdf_buffer)
    
    if pisa_status.err:
        return 'PDF generation error', 500
        
    pdf_buffer.seek(0)
    
    # Create response
    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={tournament.name}_{category.name}_Bracket.pdf'
    
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)
