with open('app/routes/category.py', 'r') as f:
    content = f.read()

old_query = "group_matches = Match.query.filter_by(group_id=group.id, match_type='group_stage').all()"
new_query = "group_matches = Match.query.filter(Match.group_id==group.id, Match.match_type.in_(['group_stage', 'round_robin'])).all()"

content = content.replace(old_query, new_query)

with open('app/routes/category.py', 'w') as f:
    f.write(content)
