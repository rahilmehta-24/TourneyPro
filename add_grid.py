
with open('app/templates/category/view.html', 'r') as f:
    content = f.read()

# Define the grid HTML snippet
grid_html = """
            <h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem;">Group Matrix</h4>
            <div style="overflow-x: auto;">
                <table class="standings-table round-robin-grid" style="text-align: center;">
                    <thead>
                        <tr>
                            <th>vs</th>
                            {% for p in group_info.standings %}
                            <th style="min-width: 80px;" title="{{ p.name }}">{{ p.name[:3] | upper }}</th>
                            {% endfor %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for row_p in group_info.standings %}
                        <tr>
                            <td style="font-weight: 600; text-align: left;">{{ row_p.name }}</td>
                            {% for col_p in group_info.standings %}
                            {% if row_p.id == col_p.id %}
                                <td style="background: rgba(255,255,255,0.05);">-</td>
                            {% else %}
                                {% set ns = namespace(found=false, match=none, is_p1=true) %}
                                {% for m in group_info.matches %}
                                    {% if m.participant1_id == row_p.id and m.participant2_id == col_p.id %}
                                        {% set ns.found = true %}
                                        {% set ns.match = m %}
                                        {% set ns.is_p1 = true %}
                                    {% elif m.participant1_id == col_p.id and m.participant2_id == row_p.id %}
                                        {% set ns.found = true %}
                                        {% set ns.match = m %}
                                        {% set ns.is_p1 = false %}
                                    {% endif %}
                                {% endfor %}
                                
                                <td style="cursor: pointer; padding: 4px;">
                                {% if ns.found %}
                                    {% if ns.match.status == 'completed' %}
                                        {% if ns.is_p1 %}
                                            <span style="{% if ns.match.winner_id == row_p.id %}color: var(--primary); font-weight: bold;{% endif %}">{{ ns.match.score1 }} - {{ ns.match.score2 }}</span>
                                        {% else %}
                                            <span style="{% if ns.match.winner_id == row_p.id %}color: var(--primary); font-weight: bold;{% endif %}">{{ ns.match.score2 }} - {{ ns.match.score1 }}</span>
                                        {% endif %}
                                    {% else %}
                                        {% if current_user and current_user.role in ['admin', 'superadmin'] and category.status == 'in_progress' %}
                                            <button onclick="openReportModal({{ ns.match.id or 0 }})" class="btn btn-small" style="padding: 2px 6px; font-size: 0.8rem;">Play</button>
                                        {% else %}
                                            <span style="color: var(--text-muted); font-size: 0.85rem;">Pending</span>
                                        {% endif %}
                                    {% endif %}
                                {% else %}
                                    -
                                {% endif %}
                                </td>
                            {% endif %}
                            {% endfor %}
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
"""

# Find where to insert it (after the standings table in groups_data)
if 'Group Matrix' not in content:
    content = content.replace("</table>\n\n            <details>", "</table>\n" + grid_html + "\n            <details>")

# Same for the pure round robin matches if there's no groups_data
rr_grid_html = """
        <h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem;">Round Robin Matrix</h4>
        <div style="overflow-x: auto;">
            <table class="standings-table round-robin-grid" style="text-align: center;">
                <thead>
                    <tr>
                        <th>vs</th>
                        {% for item in standings %}
                        <th style="min-width: 80px;" title="{{ item.participant.name }}">{{ item.participant.name[:3] | upper }}</th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    {% for row_item in standings %}
                    <tr>
                        <td style="font-weight: 600; text-align: left;">{{ row_item.participant.name }}</td>
                        {% for col_item in standings %}
                        {% if row_item.participant.id == col_item.participant.id %}
                            <td style="background: rgba(255,255,255,0.05);">-</td>
                        {% else %}
                            {% set ns = namespace(found=false, match=none, is_p1=true) %}
                            {% for m in rr_matches %}
                                {% if m.participant1_id == row_item.participant.id and m.participant2_id == col_item.participant.id %}
                                    {% set ns.found = true %}
                                    {% set ns.match = m %}
                                    {% set ns.is_p1 = true %}
                                {% elif m.participant1_id == col_item.participant.id and m.participant2_id == row_item.participant.id %}
                                    {% set ns.found = true %}
                                    {% set ns.match = m %}
                                    {% set ns.is_p1 = false %}
                                {% endif %}
                            {% endfor %}
                            
                            <td style="cursor: pointer; padding: 4px;">
                            {% if ns.found %}
                                {% if ns.match.status == 'completed' %}
                                    {% if ns.is_p1 %}
                                        <span style="{% if ns.match.winner_id == row_item.participant.id %}color: var(--primary); font-weight: bold;{% endif %}">{{ ns.match.score1 }} - {{ ns.match.score2 }}</span>
                                    {% else %}
                                        <span style="{% if ns.match.winner_id == row_item.participant.id %}color: var(--primary); font-weight: bold;{% endif %}">{{ ns.match.score2 }} - {{ ns.match.score1 }}</span>
                                    {% endif %}
                                {% else %}
                                    {% if current_user and current_user.role in ['admin', 'superadmin'] and category.status == 'in_progress' %}
                                        <button onclick="openReportModal({{ ns.match.id or 0 }})" class="btn btn-small" style="padding: 2px 6px; font-size: 0.8rem;">Play</button>
                                    {% else %}
                                        <span style="color: var(--text-muted); font-size: 0.85rem;">Pending</span>
                                    {% endif %}
                                {% endif %}
                            {% else %}
                                -
                            {% endif %}
                            </td>
                        {% endif %}
                        {% endfor %}
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
"""

if 'Round Robin Matrix' not in content:
    content = content.replace("</table>\n        \n        <details open style=\"margin-top: 2rem;\">", "</table>\n" + rr_grid_html + "\n        <details style=\"margin-top: 2rem;\">")

with open('app/templates/category/view.html', 'w') as f:
    f.write(content)
