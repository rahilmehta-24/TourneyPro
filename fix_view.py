
with open('app/templates/category/view.html', 'r') as f:
    content = f.read()

# Fix 1: Hide Start Knockout Stage button if knockout matches exist
old_btn_cond = "{% if category.status == 'in_progress' %}"
new_btn_cond = "{% set knockout_exists = matches | selectattr('match_type', 'equalto', 'knockout') | list | length > 0 %}\n        {% if category.status == 'in_progress' and not knockout_exists %}"
content = content.replace(old_btn_cond, new_btn_cond, 1)

# Fix 2: Render single scores in render_set_scores macro
old_macro_else = """                {% else %}
                    <span class="tennis-set-box empty">-</span>
                {% endif %}"""

new_macro_else = """                {% else %}
                    <span class="tennis-set-box set-winner">{{ score }}</span>
                {% endif %}"""
content = content.replace(old_macro_else, new_macro_else)

with open('app/templates/category/view.html', 'w') as f:
    f.write(content)

