with open('app/routes/category.py', 'r') as f:
    content = f.read()


# Remove auto-completion from report_category_match_result
old_report_auto_complete = """        # Check if category is completed
        if check_category_auto_completion(category):
            category.status = 'completed'
            category.completed_at = datetime.utcnow()

            # Calculate final rankings and rank participants
            if category.format in ['single_elimination', 'group_stage'] or (category.format == 'round_robin' and category.qualifiers_per_group and category.qualifiers_per_group > 0):
                calculate_final_rankings(category)
            elif category.format == 'double_elimination':
                calculate_double_elimination_rankings(category)
            elif category.format == 'round_robin' and (not category.qualifiers_per_group or category.qualifiers_per_group == 0):
                from app.leaderboard_logic import calculate_combined_round_robin_standings
                calculate_combined_round_robin_standings(category.id)

            db.session.commit()

            from app.leaderboard_logic import assign_leaderboard_points
            assign_leaderboard_points(category)"""

content = content.replace(old_report_auto_complete, "        # Auto-completion removed. Admin must click Finish Tournament.")

# Fix finish_category in manage_category
old_finish_category = """            elif action == 'finish_category':
                category.status = 'completed'
                category.completed_at = datetime.utcnow()

                # Make sure rankings are calculated if not already done
                if category.format == 'single_elimination':
                    calculate_final_rankings(category)
                elif category.format == 'double_elimination':
                    calculate_double_elimination_rankings(category)"""

new_finish_category = """            elif action == 'finish_category':
                category.status = 'completed'
                category.completed_at = datetime.utcnow()

                # Make sure rankings are calculated if not already done
                if category.format in ['single_elimination', 'group_stage'] or (category.format == 'round_robin' and category.qualifiers_per_group and category.qualifiers_per_group > 0):
                    from app.algorithms.single_elimination import calculate_final_rankings
                    calculate_final_rankings(category)
                elif category.format == 'double_elimination':
                    from app.algorithms.double_elimination import calculate_double_elimination_rankings
                    calculate_double_elimination_rankings(category)"""

content = content.replace(old_finish_category, new_finish_category)

with open('app/routes/category.py', 'w') as f:
    f.write(content)
