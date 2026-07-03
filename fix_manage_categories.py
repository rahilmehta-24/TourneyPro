
# Update category.py with rename_category route
with open('app/routes/category.py', 'r') as f:
    cat_content = f.read()

rename_route = """
@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/rename', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def rename_category(slug, category_id):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    new_name = request.form.get('new_name')
    if new_name and new_name.strip():
        category.name = new_name.strip()
        db.session.commit()
        flash(f"Category renamed to '{category.name}'", 'success')
    else:
        flash("Invalid category name.", "error")
    return redirect(request.referrer or url_for('tournament.manage_tournament', slug=slug))
"""

if "def rename_category" not in cat_content:
    cat_content = cat_content.replace("def delete_category", rename_route + "\n@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/delete', methods=['POST'])\n@login_required\n@role_required('admin', 'superadmin')\ndef delete_category")
    
# Make delete_category redirect back to referrer
cat_content = cat_content.replace(
    "return redirect(url_for('tournament.view_tournament', slug=slug))",
    "return redirect(request.referrer or url_for('tournament.view_tournament', slug=slug))"
)

with open('app/routes/category.py', 'w') as f:
    f.write(cat_content)


# Update manage.html UI for Categories section
with open('app/templates/tournament/manage.html', 'r') as f:
    manage_content = f.read()

old_categories_ui = """                        <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                            {% for category in tournament.categories %}
                            <a href="{{ url_for('category.manage_category', slug=tournament.url_slug, category_id=category.id) }}"
                                style="padding: 0.5rem 1rem; background: #1e293b; border-radius: 6px; text-decoration: none; color: white; display: flex; justify-content: space-between; align-items: center;">
                                <span>{{ category.name }}</span>
                                <span class="tab-badge status-{{ category.status }}" style="font-size: 0.75rem;">{{
                                    category.status }}</span>
                            </a>
                            {% endfor %}
                        </div>"""

new_categories_ui = """                        <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                            {% for category in tournament.categories %}
                            <div style="padding: 0.5rem 1rem; background: #1e293b; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; gap: 1rem;">
                                <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 0.25rem;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <span style="color: white; font-weight: 500;">{{ category.name }}</span>
                                        <span class="tab-badge status-{{ category.status }}" style="font-size: 0.75rem;">{{ category.status.replace('_', ' ').title() }}</span>
                                    </div>
                                    <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                                        <!-- Manage -->
                                        <a href="{{ url_for('category.manage_category', slug=tournament.url_slug, category_id=category.id) }}" class="btn btn-small btn-primary" style="padding: 0.25rem 0.5rem; font-size: 0.8rem; text-decoration: none;">⚙️ Manage</a>
                                        
                                        <!-- Rename -->
                                        <button type="button" class="btn btn-small" style="padding: 0.25rem 0.5rem; font-size: 0.8rem; background: #334155; color: white; border: none;" onclick="renameCategory({{ category.id }}, '{{ category.name | escape }}')">✏️ Rename</button>
                                        
                                        <!-- Delete -->
                                        <form method="POST" action="{{ url_for('category.delete_category', slug=tournament.url_slug, category_id=category.id) }}" style="display: inline;" onsubmit="return confirm('Are you sure you want to completely delete {{ category.name }}? This is permanent.');">
                                            <button type="submit" class="btn btn-small" style="padding: 0.25rem 0.5rem; font-size: 0.8rem; background: #b91c1c; color: white; border: none;">🗑️ Delete</button>
                                        </form>
                                    </div>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                        
                        <script>
                        function renameCategory(categoryId, currentName) {
                            const newName = prompt("Enter new name for category:", currentName);
                            if (newName !== null && newName.trim() !== "" && newName !== currentName) {
                                // Create and submit a form dynamically
                                const form = document.createElement('form');
                                form.method = 'POST';
                                form.action = `/tournaments/{{ tournament.url_slug }}/categories/${categoryId}/rename`;
                                
                                const input = document.createElement('input');
                                input.type = 'hidden';
                                input.name = 'new_name';
                                input.value = newName;
                                
                                form.appendChild(input);
                                document.body.appendChild(form);
                                form.submit();
                            }
                        }
                        </script>"""

if "function renameCategory" not in manage_content:
    manage_content = manage_content.replace(old_categories_ui, new_categories_ui)

with open('app/templates/tournament/manage.html', 'w') as f:
    f.write(manage_content)
