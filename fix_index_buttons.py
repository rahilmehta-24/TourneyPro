with open('app/templates/index.html', 'r') as f:
    content = f.read()


old_block = """                    {% if current_user.is_authenticated and current_user.role in ['admin', 'superadmin'] %}
                        <a href="{{ url_for('tournament.manage_tournament', slug=tournament.url_slug) }}"
                            class="btn btn-primary btn-small">Manage</a>
                        <form action="{{ url_for('tournament.delete_tournament', slug=tournament.url_slug) }}" method="POST" style="display:inline;" onsubmit="return confirm('Are you sure you want to delete this tournament? This cannot be undone.');">
                            <button type="submit" class="btn btn-danger btn-small" style="padding: 0.4rem 1rem; background: var(--error); border: none; color: white; border-radius: var(--radius-sm); font-weight: 600; cursor: pointer;">Delete</button>
                        </form>
                    {% else %}
                        <a href="{{ url_for('tournament.view_tournament', slug=tournament.url_slug) }}"
                            class="btn btn-secondary btn-small">View Bracket</a>
                    {% endif %}"""

new_block = """                    <a href="{{ url_for('tournament.manage_tournament', slug=tournament.url_slug) }}"
                        class="btn btn-primary btn-small">Manage</a>
                    <form action="{{ url_for('tournament.delete_tournament', slug=tournament.url_slug) }}" method="POST" style="display:inline;" onsubmit="return confirm('Are you sure you want to delete this tournament? This cannot be undone.');">
                        <button type="submit" class="btn btn-danger btn-small" style="padding: 0.4rem 1rem; background: var(--error); border: none; color: white; border-radius: var(--radius-sm); font-weight: 600; cursor: pointer;">Delete</button>
                    </form>"""

content = content.replace(old_block, new_block)

with open('app/templates/index.html', 'w') as f:
    f.write(content)

