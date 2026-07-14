import re

with open('app/routes/auth.py', 'r') as f:
    content = f.read()

target = "user = User.query.filter_by(username=username).first()"
replace = "user = User.query.filter_by(username=username).first() or User.query.filter_by(email=username).first()"

if target in content:
    content = content.replace(target, replace)
    with open('app/routes/auth.py', 'w') as f:
        f.write(content)
    print("Login patched to accept email.")
else:
    print("Target not found in auth.py")
