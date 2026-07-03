
with open('app/routes/category.py', 'r') as f:
    content = f.read()

old_completion_logic = """    # Check if category is finished
    from app.leaderboard_logic import check_category_completion, assign_leaderboard_points
    check_category_completion(category_id)
    
    # Always try to assign points for group stage if it just finished, or recalculate
    assign_leaderboard_points(category_id)"""

new_completion_logic = """    # Check if category is finished
    pending_matches = Match.query.filter_by(category_id=category.id, status='pending').count()
    if pending_matches == 0:
        category.status = 'completed'
        db.session.commit()
        from app.leaderboard_logic import assign_leaderboard_points
        assign_leaderboard_points(category)"""

content = content.replace(old_completion_logic, new_completion_logic)

with open('app/routes/category.py', 'w') as f:
    f.write(content)
