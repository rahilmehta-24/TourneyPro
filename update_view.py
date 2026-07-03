with open('app/templates/category/view.html', 'r') as f:
    content = f.read()

old_table_start = """            <h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem;">Group Matrix</h4>
            <div style="overflow-x: auto;">
                <table class="standings-table round-robin-grid" style="text-align: center;">"""

new_table_start = """            <h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem;">Group Matrix</h4>
            <div style="overflow-x: auto;">
                {% if current_user and current_user.role in ['admin', 'superadmin'] and category.status == 'in_progress' %}
                <form method="POST" action="{{ url_for('category.update_grid_scores', slug=tournament.url_slug, category_id=category.id) }}">
                {% endif %}
                <table class="standings-table round-robin-grid" style="text-align: center;">"""

content = content.replace(old_table_start, new_table_start)

old_table_end = """                            {% endfor %}
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endfor %}"""

new_table_end = """                            {% endfor %}
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% if current_user and current_user.role in ['admin', 'superadmin'] and category.status == 'in_progress' %}
                <div style="text-align: right; margin-top: 1rem; margin-bottom: 1rem;">
                    <button type="submit" class="btn btn-primary" style="padding: 0.5rem 1rem;">Save All Scores</button>
                </div>
                </form>
                {% endif %}
            </div>
        </div>
        {% endfor %}"""

content = content.replace(old_table_end, new_table_end)

old_cell = """                                <td style="cursor: pointer; padding: 4px;">
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
                                </td>"""

new_cell = """                                <td style="padding: 4px;">
                                {% if ns.found %}
                                    {% if current_user and current_user.role in ['admin', 'superadmin'] and category.status == 'in_progress' and ns.match.id %}
                                        <div style="display: flex; justify-content: center; align-items: center; gap: 4px;">
                                            <input type="number" name="match_{{ ns.match.id }}_p{% if ns.is_p1 %}1{% else %}2{% endif %}" 
                                                   value="{{ ns.match.score1 if (ns.is_p1 and ns.match.score1 is not none) else (ns.match.score2 if not ns.is_p1 and ns.match.score2 is not none else '') }}" 
                                                   style="width: 45px; text-align: center; padding: 2px; border: 1px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.3); color: white; border-radius: 4px;" min="0">
                                            <span>-</span>
                                            <input type="number" name="match_{{ ns.match.id }}_p{% if ns.is_p1 %}2{% else %}1{% endif %}" 
                                                   value="{{ ns.match.score2 if (ns.is_p1 and ns.match.score2 is not none) else (ns.match.score1 if not ns.is_p1 and ns.match.score1 is not none else '') }}" 
                                                   style="width: 45px; text-align: center; padding: 2px; border: 1px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.3); color: white; border-radius: 4px;" min="0">
                                        </div>
                                    {% else %}
                                        {% if ns.match.status == 'completed' %}
                                            {% if ns.is_p1 %}
                                                <span style="{% if ns.match.winner_id == row_p.id %}color: var(--primary); font-weight: bold;{% endif %}">{{ ns.match.score1 }} - {{ ns.match.score2 }}</span>
                                            {% else %}
                                                <span style="{% if ns.match.winner_id == row_p.id %}color: var(--primary); font-weight: bold;{% endif %}">{{ ns.match.score2 }} - {{ ns.match.score1 }}</span>
                                            {% endif %}
                                        {% else %}
                                            <span style="color: var(--text-muted); font-size: 0.85rem;">Pending</span>
                                        {% endif %}
                                    {% endif %}
                                {% else %}
                                    -
                                {% endif %}
                                </td>"""

content = content.replace(old_cell, new_cell)

with open('app/templates/category/view.html', 'w') as f:
    f.write(content)
