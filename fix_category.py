import re
with open('app/routes/category.py', 'r') as f:
    content = f.read()

# Fix create_category to accept num_groups for round_robin
content = content.replace(
    "has_group_stage = (format_type == 'group_stage')",
    "has_group_stage = (format_type in ['group_stage', 'round_robin'])"
)

# Fix start_category to use group stage generator for round robin if groups exist
content = content.replace(
    """                elif category.format == 'round_robin':
                    from app.algorithms.round_robin import generate_round_robin
                    matches_data = generate_round_robin(participants_list)
                    for match_data in matches_data:
                        match = Match(**match_data, tournament_id=tournament.id, category_id=category.id)
                        db.session.add(match)""",
    """                elif category.format == 'round_robin':
                    if category.num_groups:
                        from app.algorithms.group_stage import generate_group_stage
                        matches_data = generate_group_stage(category, participants_list)
                        for match_data in matches_data:
                            match_data['match_type'] = 'round_robin' # Keep it as round_robin so standings work
                            match = Match(**match_data, tournament_id=tournament.id)
                            db.session.add(match)
                    else:
                        from app.algorithms.round_robin import generate_round_robin
                        matches_data = generate_round_robin(participants_list)
                        for match_data in matches_data:
                            match = Match(**match_data, tournament_id=tournament.id, category_id=category.id)
                            db.session.add(match)"""
)

# Fix view_category rendering to show matches
# Let's replace the view_category standings logic.
content = content.replace(
    """    groups_data = []
    if category.format == 'group_stage':""",
    """    groups_data = []
    if category.format == 'group_stage' or (category.format == 'round_robin' and category.num_groups):"""
)

with open('app/routes/category.py', 'w') as f:
    f.write(content)
