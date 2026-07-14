with open('app/routes/auth.py', 'r') as f:
    content = f.read()

# patch login
target_login = "        username = request.form.get('username')\n        password = request.form.get('password')"
replace_login = "        username = request.form.get('username', '').strip()\n        password = request.form.get('password')"
content = content.replace(target_login, replace_login)

# patch register
target_register = "        username = request.form.get('username')\n        email = request.form.get('email')\n        password = request.form.get('password')"
replace_register = "        username = request.form.get('username', '').strip()\n        email = request.form.get('email', '').strip()\n        password = request.form.get('password')"
content = content.replace(target_register, replace_register)

with open('app/routes/auth.py', 'w') as f:
    f.write(content)
print("Auth patched to strip whitespace.")
