
with open('app/routes/category.py', 'r') as f:
    content = f.read()

# Remove the import line
content = content.replace("    from app.algorithms.scoring import calculate_winner\n", "")

# Replace the calculate_winner logic
old_winner_logic = """            # Determine winner
            winner_id = calculate_winner(match, category.format)
            if winner_id:
                match.winner_id = winner_id
                if match.status != 'completed':
                    match.status = 'completed'
                    match.completed_at = datetime.utcnow()
                updated_count += 1"""

new_winner_logic = """            # Determine winner based on scores
            if score1 > score2:
                winner_id = match.participant1_id
            elif score2 > score1:
                winner_id = match.participant2_id
            else:
                winner_id = None
                
            if winner_id:
                match.winner_id = winner_id
                if match.status != 'completed':
                    match.status = 'completed'
                    match.completed_at = datetime.utcnow()
                updated_count += 1"""

content = content.replace(old_winner_logic, new_winner_logic)

with open('app/routes/category.py', 'w') as f:
    f.write(content)
