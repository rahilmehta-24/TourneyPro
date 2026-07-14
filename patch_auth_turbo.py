with open('app/templates/auth/login.html', 'r') as f:
    content = f.read()
if 'method="POST"' in content and 'data-turbo="false"' not in content:
    content = content.replace('method="POST"', 'method="POST" data-turbo="false"')
    with open('app/templates/auth/login.html', 'w') as f:
        f.write(content)
        
with open('app/templates/auth/register.html', 'r') as f:
    content = f.read()
if 'method="POST"' in content and 'data-turbo="false"' not in content:
    content = content.replace('method="POST"', 'method="POST" data-turbo="false"')
    with open('app/templates/auth/register.html', 'w') as f:
        f.write(content)

print("Turbo disabled on auth forms.")
