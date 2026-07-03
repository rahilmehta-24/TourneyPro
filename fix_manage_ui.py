with open('app/templates/category/manage.html', 'r') as f:
    content = f.read()

old_code = """<button type="submit" class="btn btn-primary" style="background: var(--gradient-success); border: none; font-weight: 700; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3); padding: 0.65rem 1.5rem;" {% if participants|length < 2 %}disabled{% endif %}>"""
new_code = """<button type="submit" class="btn btn-primary" style="background: var(--gradient-success); border: none; font-weight: 700; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3); padding: 0.65rem 1.5rem;" {% if participants|length < 2 or tournament.status not in ['in_progress', 'completed'] %}disabled title="{% if tournament.status not in ['in_progress', 'completed'] %}Start the overall tournament first!{% else %}Need at least 2 participants.{% endif %}"{% endif %}>"""

content = content.replace(old_code, new_code)

with open('app/templates/category/manage.html', 'w') as f:
    f.write(content)

