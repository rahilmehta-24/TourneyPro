with open('app/templates/category/view.html', 'r') as f:
    content = f.read()

# 1. Remove the View Matches dropdown
import re
# The details block starts with <details> and ends with </details>
details_pattern = re.compile(r'<details>\s*<summary>View Matches</summary>.*?</details>', re.DOTALL)
content = details_pattern.sub('', content)

# 2. Update the buttons
old_buttons = """                {% if current_user and current_user.role in ['admin', 'superadmin'] and category.status == 'in_progress' %}
                <div style="text-align: right; margin-top: 1rem; margin-bottom: 1rem;">
                    <button type="submit" class="btn btn-primary" style="padding: 0.5rem 1rem;">Save All Scores</button>
                </div>
                </form>
                {% endif %}"""

new_buttons = """                {% if current_user and current_user.role in ['admin', 'superadmin'] and category.status == 'in_progress' %}
                <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 1rem; margin-bottom: 1rem;">
                    <button type="submit" class="btn btn-primary" title="Save Entries" style="padding: 0.5rem; display: flex; align-items: center; justify-content: center; border-radius: 4px;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    </button>
                    <button type="reset" class="btn" title="Undo Entries" style="padding: 0.5rem; display: flex; align-items: center; justify-content: center; border-radius: 4px; background: rgba(255,255,255,0.1);">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7v6h6"></path><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"></path></svg>
                    </button>
                </div>
                </form>
                {% endif %}"""

content = content.replace(old_buttons, new_buttons)

with open('app/templates/category/view.html', 'w') as f:
    f.write(content)
