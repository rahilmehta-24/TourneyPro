from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, Tournament, Category, Participant, Match, Group
from app.constants import TOURNAMENT_FORMATS
from app.algorithms.single_elimination import generate_single_elimination, calculate_final_rankings
from app.algorithms.double_elimination import generate_double_elimination, calculate_double_elimination_rankings
from app.algorithms.round_robin import generate_round_robin, calculate_round_robin_standings
from app.algorithms.group_stage import generate_group_stage, generate_knockout_from_groups, calculate_group_standings
from datetime import datetime

category_bp = Blueprint('category', __name__)

@category_bp.route('/tournaments/<slug>/categories/new', methods=['GET', 'POST'])
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
        return redirect(url_for('category.manage_category', slug=slug, category_id=category.id))
    
    return render_template('category/create.html', tournament=tournament, formats=TOURNAMENT_FORMATS)

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>')
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

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/manage', methods=['GET', 'POST'])
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
                return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
            
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
            return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
        
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
            return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
        
        elif action == 'finish_category':
            category.status = 'completed'
            category.completed_at = datetime.utcnow()
            db.session.commit()
            
            flash('Tournament completed! 🏆', 'success')
            return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
    
    return render_template('category/manage.html',
                         tournament=tournament,
                         category=category,
                         participants=participants,
                         formats=TOURNAMENT_FORMATS)

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/seeding', methods=['GET', 'POST'])
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
        return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
    
    return render_template('category/seeding.html',
                         tournament=tournament,
                         category=category,
                         participants=participants)

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/start-knockout', methods=['POST'])
def start_knockout_stage(slug, category_id):
    """Transition from group stage to knockout"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    
    if not category.has_group_stage:
        flash('This category does not have a group stage.', 'error')
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
    
    # Generate knockout bracket from group qualifiers
    matches_data = generate_knockout_from_groups(category)
    
    for match_data in matches_data:
        match = Match(**match_data, tournament_id=tournament.id)
        db.session.add(match)
    
    db.session.commit()
    
    flash('Knockout stage started!', 'success')
    return redirect(url_for('category.view_category', slug=slug, category_id=category_id))

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/match/<int:match_id>/report', methods=['POST'])
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
    return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
