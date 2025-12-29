from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, Tournament, Participant, Match, TournamentSettings
from app.algorithms.single_elimination import generate_single_elimination
from app.constants import TOURNAMENT_FORMATS
from slugify import slugify
from datetime import datetime

tournament_bp = Blueprint('tournament', __name__)

@tournament_bp.route('/tournaments/new', methods=['GET', 'POST'])
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
        return redirect(url_for('tournament.manage_tournament', slug=tournament.url_slug))
    
    return render_template('tournament/create.html', formats=TOURNAMENT_FORMATS)

@tournament_bp.route('/tournaments/<slug>')
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

@tournament_bp.route('/tournaments/<slug>/manage', methods=['GET', 'POST'])
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
            return redirect(url_for('tournament.manage_tournament', slug=slug))
        
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
                return redirect(url_for('tournament.view_tournament', slug=slug))
            else:
                flash(f'Format "{tournament.format}" is not yet implemented. Coming soon!', 'warning')
        
        elif action == 'finish_tournament':
            tournament.status = 'completed'
            tournament.completed_at = datetime.utcnow()
            db.session.commit()
            
            flash('Tournament completed! 🏆', 'success')
            return redirect(url_for('tournament.view_tournament', slug=slug))
    
    
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

@tournament_bp.route('/tournaments/<slug>/match/<int:match_id>/report', methods=['POST'])
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
    return redirect(url_for('tournament.view_tournament', slug=slug))

@tournament_bp.route('/tournaments/<slug>/seeding', methods=['GET', 'POST'])
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
        return redirect(url_for('tournament.manage_tournament', slug=slug))
    
    return render_template('tournament/seeding.html',
                         tournament=tournament,
                         participants=participants)

@tournament_bp.route('/tournaments/<slug>/delete', methods=['POST'])
def delete_tournament(slug):
    """Delete tournament"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    
    db.session.delete(tournament)
    db.session.commit()
    
    flash('Tournament deleted successfully!', 'info')
    return redirect(url_for('main.index'))
