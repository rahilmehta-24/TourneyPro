with open('app/algorithms/group_stage.py', 'r') as f:
    content = f.read()

old_query = "matches = Match.query.filter_by(group_id=group_id, match_type='group_stage').all()"
new_query = "matches = Match.query.filter(Match.group_id==group_id, Match.match_type.in_(['group_stage', 'round_robin'])).all()"

content = content.replace(old_query, new_query)

with open('app/algorithms/group_stage.py', 'w') as f:
    f.write(content)
