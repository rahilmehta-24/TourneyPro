with open('app/routes/category.py', 'r') as f:
    content = f.read()


helper_func = """def check_category_auto_completion(category):
    from app.models import Match
    has_knockout = category.format in ['single_elimination', 'double_elimination'] or \\
                   category.format == 'group_stage' or \\
                   (category.format == 'round_robin' and category.qualifiers_per_group and category.qualifiers_per_group > 0)

    all_matches = Match.query.filter_by(category_id=category.id).all()
    if not all_matches:
        return False
        
    pending = any(m.status == 'pending' for m in all_matches)
    if pending:
        return False
        
    if has_knockout:
        if category.format in ['group_stage', 'round_robin']:
            knockout_exists = any(m.match_type == 'knockout' or m.bracket_type in ['winners', 'losers', 'grand_finals', 'grand_final', 'third_place'] for m in all_matches)
            if not knockout_exists:
                return False
                
    return True

"""

# Let's insert it before check_bracket_completion which is somewhere there, or just at the top after imports.
# We'll just insert it before `def check_bracket_completion` or before `def check_and_update_knockout`
# Let's search for "def generate_knockout_from_groups" or something. Let's just put it before report_category_match_result.
old_report_func = """def report_category_match_result(slug, category_id, match_id):"""

content = content.replace(old_report_func, helper_func + old_report_func)

# Replace in report_category_match_result:
old_completion_1 = """        # Check if category is completed
        all_matches = Match.query.filter_by(category_id=category_id).all()
        if all(m.status == 'completed' for m in all_matches):
            category.status = 'completed'
            category.completed_at = datetime.utcnow()

            # Calculate final rankings and rank participants
            if category.format == 'single_elimination':
                calculate_final_rankings(category)
            elif category.format == 'double_elimination':
                calculate_double_elimination_rankings(category)

            db.session.commit()

            from app.leaderboard_logic import assign_leaderboard_points
            assign_leaderboard_points(category)"""

new_completion_1 = """        # Check if category is completed
        if check_category_auto_completion(category):
            category.status = 'completed'
            category.completed_at = datetime.utcnow()

            # Calculate final rankings and rank participants
            if category.format == 'single_elimination':
                calculate_final_rankings(category)
            elif category.format == 'double_elimination':
                calculate_double_elimination_rankings(category)
            elif category.format == 'round_robin' and (not category.qualifiers_per_group or category.qualifiers_per_group == 0):
                from app.leaderboard_logic import calculate_combined_round_robin_standings
                calculate_combined_round_robin_standings(category.id)

            db.session.commit()

            from app.leaderboard_logic import assign_leaderboard_points
            assign_leaderboard_points(category)"""

content = content.replace(old_completion_1, new_completion_1)

# Replace in update_grid_scores
old_completion_2 = """    # Check if category is finished
    pending_matches = Match.query.filter_by(category_id=category.id, status='pending').count()
    if pending_matches == 0:
        category.status = 'completed'
        db.session.commit()
        from app.leaderboard_logic import assign_leaderboard_points
        assign_leaderboard_points(category)"""

new_completion_2 = """    # Check if category is finished
    if check_category_auto_completion(category):
        category.status = 'completed'
        category.completed_at = datetime.utcnow()
        if category.format == 'round_robin' and (not category.qualifiers_per_group or category.qualifiers_per_group == 0):
            from app.leaderboard_logic import calculate_combined_round_robin_standings
            calculate_combined_round_robin_standings(category.id)
        db.session.commit()
        from app.leaderboard_logic import assign_leaderboard_points
        assign_leaderboard_points(category)"""

content = content.replace(old_completion_2, new_completion_2)

with open('app/routes/category.py', 'w') as f:
    f.write(content)
