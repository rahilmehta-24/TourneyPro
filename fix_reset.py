with open('app/routes/leaderboard.py', 'r') as f:
    content = f.read()

old_code = """def reset_leaderboard():
    PlayerTournamentRecord.query.delete()
    Player.query.delete()
    Participant.query.update({'player_id': None})
    db.session.commit()"""

new_code = """def reset_leaderboard():
    PlayerTournamentRecord.query.delete()
    Participant.query.update({'player_id': None})
    Player.query.delete()
    db.session.commit()"""

content = content.replace(old_code, new_code)

with open('app/routes/leaderboard.py', 'w') as f:
    f.write(content)
