import re
with open('app/templates/category/view.html', 'r') as f:
    content = f.read()

# Insert the single pool round robin matches and standings right after groups-section
addition = """
    {% if not groups_data and category.format == 'round_robin' %}
    <div class="groups-section">
        <h2>Round Robin Matches</h2>
        <div class="matches-list">
            {% for match in rr_matches %}
            <div class="match-card {% if match.status == 'completed' %}completed{% endif %}">
                <span>{{ match.participant1.name if match.participant1 else 'TBD' }}</span>
                <span class="vs">vs</span>
                <span>{{ match.participant2.name if match.participant2 else 'TBD' }}</span>
                {% if match.status == 'completed' %}
                <span class="score">{{ match.score1 }} - {{ match.score2 }}</span>
                {% else %}
                {% if current_user and current_user.role in ['admin', 'superadmin'] and category.status == 'in_progress' %}
                <button onclick="openReportModal({{ match.id or 0 }})" class="btn btn-small">Report Result</button>
                {% endif %}
                {% endif %}
            </div>
            {% else %}
            <p style="text-align: center; color: var(--text-secondary); padding: 1rem;">No matches scheduled.</p>
            {% endfor %}
        </div>
    </div>
    {% endif %}
"""

if "<h2>Round Robin Matches</h2>" not in content:
    content = content.replace("{% if rounds %}", addition + "\n    {% if rounds %}")

with open('app/templates/category/view.html', 'w') as f:
    f.write(content)
