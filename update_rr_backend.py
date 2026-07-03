
with open('app/routes/category.py', 'r') as f:
    content = f.read()

# We need to find the start_category logic:
# elif category.format == 'round_robin':
#     if category.num_groups:

old_rr_start = """                elif category.format == 'round_robin':
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

new_rr_start = """                elif category.format == 'round_robin':
                    if category.teams_per_group and category.teams_per_group >= 3:
                        import math
                        total_players = len(participants_list)
                        if total_players > 0:
                            category.num_groups = math.ceil(total_players / category.teams_per_group)
                        else:
                            category.num_groups = 1
                            
                        from app.algorithms.group_stage import generate_group_stage
                        matches_data = generate_group_stage(category, participants_list)
                        for match_data in matches_data:
                            match_data['match_type'] = 'round_robin'
                            match = Match(**match_data, tournament_id=tournament.id)
                            db.session.add(match)
                    else:
                        # Fallback for pure round robin if no teams_per_group
                        from app.algorithms.round_robin import generate_round_robin
                        matches_data = generate_round_robin(participants_list)
                        for match_data in matches_data:
                            match = Match(**match_data, tournament_id=tournament.id, category_id=category.id)
                            db.session.add(match)"""

if "category.teams_per_group >= 3" not in content:
    content = content.replace(old_rr_start, new_rr_start)

# Also update the preview logic in `view_category` (which uses DummyMatch to render unstarted bracket)
old_rr_preview = """            elif category.format == 'round_robin':
                if category.num_groups:
                    from app.algorithms.group_stage import generate_group_stage
                    preview_matches = generate_group_stage(category, participants)
                    
                    class DummyMatch:
                        def __init__(self, **kwargs):
                            for k, v in kwargs.items():
                                setattr(self, k, v)
                            self.participant1 = next((p for p in participants if p.id == kwargs.get('participant1_id')), None)
                            self.participant2 = next((p for p in participants if p.id == kwargs.get('participant2_id')), None)
                            self.status = 'pending'
                            self.score1 = None
                            self.score2 = None
                            self.winner_id = None
                            
                    dummy_matches = [DummyMatch(**m) for m in preview_matches]
                    from app.algorithms.group_stage import calculate_group_standings
                    groups_data = calculate_group_standings(category.id, dummy_matches, participants)
                else:
                    from app.algorithms.round_robin import generate_round_robin
                    preview_matches = generate_round_robin(participants)
                    class DummyMatch:
                        def __init__(self, **kwargs):
                            for k, v in kwargs.items():
                                setattr(self, k, v)
                            self.participant1 = next((p for p in participants if p.id == kwargs.get('participant1_id')), None)
                            self.participant2 = next((p for p in participants if p.id == kwargs.get('participant2_id')), None)
                            self.status = 'pending'
                            self.score1 = None
                            self.score2 = None
                            self.winner_id = None
                    rr_matches = [DummyMatch(**m) for m in preview_matches]
                    from app.algorithms.round_robin import calculate_round_robin_standings
                    standings = calculate_round_robin_standings(participants, rr_matches)"""

new_rr_preview = """            elif category.format == 'round_robin':
                if category.teams_per_group and category.teams_per_group >= 3:
                    import math
                    total_players = len(participants)
                    if total_players > 0:
                        category.num_groups = math.ceil(total_players / category.teams_per_group)
                    else:
                        category.num_groups = 1
                        
                    from app.algorithms.group_stage import generate_group_stage
                    preview_matches = generate_group_stage(category, participants)
                    
                    class DummyMatch:
                        def __init__(self, **kwargs):
                            for k, v in kwargs.items():
                                setattr(self, k, v)
                            self.participant1 = next((p for p in participants if p.id == kwargs.get('participant1_id')), None)
                            self.participant2 = next((p for p in participants if p.id == kwargs.get('participant2_id')), None)
                            self.status = 'pending'
                            self.score1 = None
                            self.score2 = None
                            self.winner_id = None
                            
                    dummy_matches = [DummyMatch(**m) for m in preview_matches]
                    from app.algorithms.group_stage import calculate_group_standings
                    groups_data = calculate_group_standings(category.id, dummy_matches, participants)
                else:
                    from app.algorithms.round_robin import generate_round_robin
                    preview_matches = generate_round_robin(participants)
                    class DummyMatch:
                        def __init__(self, **kwargs):
                            for k, v in kwargs.items():
                                setattr(self, k, v)
                            self.participant1 = next((p for p in participants if p.id == kwargs.get('participant1_id')), None)
                            self.participant2 = next((p for p in participants if p.id == kwargs.get('participant2_id')), None)
                            self.status = 'pending'
                            self.score1 = None
                            self.score2 = None
                            self.winner_id = None
                    rr_matches = [DummyMatch(**m) for m in preview_matches]
                    from app.algorithms.round_robin import calculate_round_robin_standings
                    standings = calculate_round_robin_standings(participants, rr_matches)"""

if "category.teams_per_group and category.teams_per_group >= 3" not in old_rr_preview and "category.num_groups = math.ceil" not in content:
    content = content.replace(old_rr_preview, new_rr_preview)

with open('app/routes/category.py', 'w') as f:
    f.write(content)
