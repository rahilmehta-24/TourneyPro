with open('app/routes/category.py', 'r') as f:
    content = f.read()


old_logic = """        # Validate and format score
        score1, score2 = validate_and_format_score(
            winner_id, match.participant1_id, match.participant2_id,
            num_sets, games_per_set, form_data
        )"""

new_logic = """        # Validate and format score
        if category.format == 'round_robin' or (category.format == 'group_stage' and category.total_games):
            p1_score = request.form.get('set1_p1', type=int)
            p2_score = request.form.get('set1_p2', type=int)
            
            if p1_score is None or p2_score is None:
                raise ValueError("Scores for both players are required.")
                
            if winner_id == match.participant1_id and p1_score <= p2_score:
                raise ValueError("Winner must have a higher score.")
            if winner_id == match.participant2_id and p2_score <= p1_score:
                raise ValueError("Winner must have a higher score.")
                
            score1 = str(p1_score)
            score2 = str(p2_score)
        else:
            score1, score2 = validate_and_format_score(
                winner_id, match.participant1_id, match.participant2_id,
                num_sets, games_per_set, form_data
            )"""

content = content.replace(old_logic, new_logic)

with open('app/routes/category.py', 'w') as f:
    f.write(content)
