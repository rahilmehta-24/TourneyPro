with open('app/templates/tournament/view.html', 'r') as f:
    content = f.read()

import re

old_block = """                    {% if finals_match and finals_match.winner %}
                    <div style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <div
                            style="padding: 0.75rem 1rem; background: rgba(255,215,0,0.1); border-left: 3px solid #FFD700;">
                            <div style="font-weight: 700; font-size: 0.875rem; color: #FFD700; margin-bottom: 0.25rem;">
                                🥇 CHAMPION</div>
                            <div style="color: var(--text-primary); font-weight: 600;">{{ finals_match.winner.name }}
                            </div>
                        </div>
                    </div>

                    {% set runner_up = finals_match.participant1 if finals_match.participant1_id !=
                    finals_match.winner_id else finals_match.participant2 %}
                    <div style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <div
                            style="padding: 0.75rem 1rem; background: rgba(192,192,192,0.1); border-left: 3px solid #C0C0C0;">
                            <div style="font-weight: 700; font-size: 0.875rem; color: #C0C0C0; margin-bottom: 0.25rem;">
                                🥈 RUNNER-UP</div>
                            <div style="color: var(--text-primary); font-weight: 600;">{{ runner_up.name }}</div>
                        </div>
                    </div>
                    {% endif %}

                    {% set total_rounds = category.matches|map(attribute='round')|max %}
                    {% if total_rounds >= 2 %}
                    {% set semi_final_round = category.matches|selectattr('round', 'equalto', total_rounds - 1)|list %}
                    <div
                        style="padding: 0.75rem 1rem; background: rgba(205,127,50,0.1); border-left: 3px solid #cd7f32;">
                        <div style="font-weight: 700; font-size: 0.875rem; color: #cd7f32; margin-bottom: 0.5rem;">🥉
                            SEMI-FINALISTS</div>
                        {% for match in semi_final_round %}
                        {% set loser = match.participant1 if match.participant1_id != match.winner_id else
                        match.participant2 %}
                        {% if loser %}
                        <div style="color: var(--text-primary); font-weight: 500; padding: 0.25rem 0;">{{ loser.name }}
                        </div>
                        {% endif %}
                        {% endfor %}
                    </div>
                    {% endif %}"""


new_block = """                    {% set winner = category.participants | selectattr('final_rank', 'equalto', 1) | first %}
                    {% if winner %}
                    <div style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <div style="padding: 0.75rem 1rem; background: rgba(255,215,0,0.1); border-left: 3px solid #FFD700;">
                            <div style="font-weight: 700; font-size: 0.875rem; color: #FFD700; margin-bottom: 0.25rem;">
                                🥇 CHAMPION</div>
                            <div style="color: var(--text-primary); font-weight: 600;">{{ winner.name }}</div>
                        </div>
                    </div>
                    {% endif %}

                    {% set runner_up = category.participants | selectattr('final_rank', 'equalto', 2) | first %}
                    {% if runner_up %}
                    <div style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <div style="padding: 0.75rem 1rem; background: rgba(192,192,192,0.1); border-left: 3px solid #C0C0C0;">
                            <div style="font-weight: 700; font-size: 0.875rem; color: #C0C0C0; margin-bottom: 0.25rem;">
                                🥈 RUNNER-UP</div>
                            <div style="color: var(--text-primary); font-weight: 600;">{{ runner_up.name }}</div>
                        </div>
                    </div>
                    {% endif %}

                    {% set sf1 = category.participants | selectattr('final_rank', 'equalto', 3) | list %}
                    {% set sf2 = category.participants | selectattr('final_rank', 'equalto', 4) | list %}
                    {% set sf_combined = sf1 + sf2 %}
                    {% if sf_combined %}
                    <div style="padding: 0.75rem 1rem; background: rgba(205,127,50,0.1); border-left: 3px solid #cd7f32;">
                        <div style="font-weight: 700; font-size: 0.875rem; color: #cd7f32; margin-bottom: 0.5rem;">
                            🥉 SEMI-FINALISTS</div>
                        {% for sf in sf_combined[:2] %}
                        <div style="color: var(--text-primary); font-weight: 500; padding: 0.25rem 0;">{{ sf.name }}</div>
                        {% endfor %}
                    </div>
                    {% endif %}"""

# We also need to get rid of final_round logic before it
old_final_round = """            {% set final_round = category.matches|selectattr('round', 'equalto',
            category.matches|map(attribute='round')|max)|list %}
            {% set finals_match = final_round[0] if final_round else none %}"""

new_final_round = ""

# Since old_final_round has line breaks, just use regex
content = re.sub(r"{% set final_round.*?{% set finals_match = final_round\[0\] if final_round else none %}", "", content, flags=re.DOTALL)
content = content.replace(old_block, new_block)

with open('app/templates/tournament/view.html', 'w') as f:
    f.write(content)

