with open('app/routes/category.py', 'r') as f:
    content = f.read()

new_route = """

@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/update_grid', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def update_grid_scores(slug, category_id):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    
    if category.status != 'in_progress':
        flash('Cannot update scores unless category is in progress.', 'error')
        return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
    
    from app.models import Match
    from app.algorithms.scoring import calculate_winner
    from datetime import datetime
    
    # Process form data
    # Expected format: match_{id}_p1, match_{id}_p2
    match_updates = {}
    for key, value in request.form.items():
        if key.startswith('match_'):
            parts = key.split('_')
            if len(parts) == 3:
                try:
                    match_id = int(parts[1])
                    player_idx = parts[2]
                    
                    if match_id not in match_updates:
                        match_updates[match_id] = {}
                        
                    if value and value.strip() != '':
                        match_updates[match_id][player_idx] = int(value)
                    else:
                        match_updates[match_id][player_idx] = None
                except ValueError:
                    continue
                    
    # Update matches
    updated_count = 0
    for match_id, scores in match_updates.items():
        match = Match.query.get(match_id)
        if not match or match.category_id != category.id:
            continue
            
        score1 = scores.get('p1')
        score2 = scores.get('p2')
        
        # Only update if both scores are provided, or if they were previously completed and now being updated
        if score1 is not None and score2 is not None:
            match.score1 = score1
            match.score2 = score2
            
            # Determine winner
            winner_id = calculate_winner(match, category.format)
            if winner_id:
                match.winner_id = winner_id
                if match.status != 'completed':
                    match.status = 'completed'
                    match.completed_at = datetime.utcnow()
                updated_count += 1
        elif score1 is None and score2 is None:
            # If scores are cleared, revert match to pending
            if match.status == 'completed':
                match.status = 'pending'
                match.score1 = None
                match.score2 = None
                match.winner_id = None
                match.completed_at = None
                updated_count += 1

    db.session.commit()
    
    # Check if category is finished
    from app.leaderboard_logic import check_category_completion, assign_leaderboard_points
    check_category_completion(category_id)
    
    # Always try to assign points for group stage if it just finished, or recalculate
    assign_leaderboard_points(category_id)
    
    flash(f'Successfully updated {updated_count} matches.', 'success')
    return redirect(url_for('category.view_category', slug=slug, category_id=category_id))
"""

if "def update_grid_scores" not in content:
    content += new_route

with open('app/routes/category.py', 'w') as f:
    f.write(content)
