
with open('app/routes/auth.py', 'r') as f:
    content = f.read()

target = "        user = User.query.filter_by(username=username).first() or User.query.filter_by(email=username).first()"
replace = "        user = User.query.filter(db.or_(User.username.ilike(username), User.email.ilike(username))).first()"

if target in content:
    content = content.replace(target, replace)
    with open('app/routes/auth.py', 'w') as f:
        f.write(content)
    print("Auth patched for case insensitivity.")
else:
    print("Target not found.")
