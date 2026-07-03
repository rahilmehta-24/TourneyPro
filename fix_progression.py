with open('app/routes/category.py', 'r') as f:
    content = f.read()


# Fix 1: Match Progression
old_progression = """        # Update next round match for knockout
        elif match.match_type == 'knockout':
            if category.format == 'single_elimination':"""

new_progression = """        # Update next round match for knockout
        elif match.match_type == 'knockout':
            if category.format in ['single_elimination', 'group_stage', 'round_robin']:"""

content = content.replace(old_progression, new_progression)

# Fix 2: Final Rankings
old_rankings = """            # Calculate final rankings and rank participants
            if category.format == 'single_elimination':
                calculate_final_rankings(category)"""

new_rankings = """            # Calculate final rankings and rank participants
            if category.format in ['single_elimination', 'group_stage'] or (category.format == 'round_robin' and category.qualifiers_per_group and category.qualifiers_per_group > 0):
                calculate_final_rankings(category)"""

content = content.replace(old_rankings, new_rankings)

with open('app/routes/category.py', 'w') as f:
    f.write(content)
