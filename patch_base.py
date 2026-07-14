
with open('app/templates/base.html', 'r') as f:
    content = f.read()

target = """                {% if current_user and current_user.role == 'superadmin' %}
                    <a href="{{ url_for('auth.user_management') }}" class="nav-link admin-link">User Management</a>
                {% endif %}"""

replace = """                {% if current_user and current_user.role == 'superadmin' %}
                    <a href="{{ url_for('auth.user_management') }}" class="nav-link admin-link">User Management</a>
                {% endif %}
                {% if current_user and current_user.role in ['admin', 'superadmin'] %}
                    <a href="{{ url_for('player.admin_players') }}" class="nav-link admin-link">Player Directory</a>
                {% endif %}"""

if target in content:
    content = content.replace(target, replace)
    with open('app/templates/base.html', 'w') as f:
        f.write(content)
    print("base.html patched.")
else:
    print("Target not found.")
