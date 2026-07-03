
with open('app/routes/category.py', 'r') as f:
    content = f.read()

delete_route = """@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def delete_category(slug, category_id):
    \"\"\"Delete a category and all its data\"\"\"
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    
    try:
        from app.models import Match, Group, Participant
        # Delete all matches
        Match.query.filter_by(category_id=category.id).delete()
        # Delete all participants
        Participant.query.filter_by(category_id=category.id).delete()
        # Delete all groups
        Group.query.filter_by(category_id=category.id).delete()
        
        db.session.delete(category)
        db.session.commit()
        flash(f"Category '{category.name}' deleted successfully.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete category: {str(e)}", 'error')
        
    return redirect(url_for('tournament.view_tournament', slug=slug))
"""

# Insert delete route before report_category_match_result
if "def delete_category" not in content:
    content = content.replace("@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/match/<int:match_id>/report'", delete_route + "\n@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/match/<int:match_id>/report'")
    
with open('app/routes/category.py', 'w') as f:
    f.write(content)

# Update manage.html to include delete button
with open('app/templates/category/manage.html', 'r') as f:
    manage_content = f.read()

delete_html = """            <!-- Delete Category Card -->
            <div class="card" style="background: var(--bg-card); border-radius: var(--radius-lg); padding: var(--spacing-md); box-shadow: var(--shadow-md); border: 1px solid rgba(239, 68, 68, 0.2); border-left: 4px solid #b91c1c; margin-top: var(--spacing-md);">
                <h3 style="margin-bottom: var(--spacing-xs); font-size: 1.15rem; color: #b91c1c;">⚠️ Delete Category</h3>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: var(--spacing-sm);">Deleting the category is permanent. It will remove all players, matches, and standings associated with it.</p>
                <form method="POST" action="{{ url_for('category.delete_category', slug=tournament.url_slug, category_id=category.id) }}" onsubmit="return confirm('WARNING: Are you absolutely sure you want to permanently delete this category? This action cannot be undone.');">
                    <button type="submit" class="btn btn-danger" style="background: transparent; border: 1px solid #b91c1c; color: #b91c1c; font-weight: 600; padding: 0.65rem 1rem; font-size: 0.9rem; width: 100%; transition: all 0.2s;" onmouseover="this.style.background='#b91c1c'; this.style.color='white';" onmouseout="this.style.background='transparent'; this.style.color='#b91c1c';">
                        Delete Category
                    </button>
                </form>
            </div>
"""

if "Delete Category Card" not in manage_content:
    manage_content = manage_content.replace("        </div>\n\n        <!-- Right Side: Bulk Add -->", delete_html + "        </div>\n\n        <!-- Right Side: Bulk Add -->")
    
with open('app/templates/category/manage.html', 'w') as f:
    f.write(manage_content)
