
with open('app/routes/category.py', 'r') as f:
    content = f.read()

# Remove the old incremental updates in report_category_match_result
old_incremental = """        # Update group stage stats if applicable
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
                    loser.group_losses += 1"""

content = content.replace(old_incremental, "        # Stats will be recalculated at the end")

# Add recalculate_all_group_stats at the end of report_category_match_result before commit/flash
old_end_report = """        db.session.commit()
        flash('Match result reported successfully!', 'success')"""

new_end_report = """        db.session.commit()
        
        # Recalculate group/round-robin stats
        if category.format in ['group_stage', 'round_robin']:
            from app.leaderboard_logic import recalculate_all_group_stats
            recalculate_all_group_stats(category.id)
            
        flash('Match result reported successfully!', 'success')"""

content = content.replace(old_end_report, new_end_report)

# Add recalculate_all_group_stats to update_grid_scores
old_end_grid = """    # Check if category is finished
    if check_category_auto_completion(category):"""

new_end_grid = """    # Recalculate group/round-robin stats
    from app.leaderboard_logic import recalculate_all_group_stats
    recalculate_all_group_stats(category.id)

    # Check if category is finished
    if check_category_auto_completion(category):"""

content = content.replace(old_end_grid, new_end_grid)

with open('app/routes/category.py', 'w') as f:
    f.write(content)
