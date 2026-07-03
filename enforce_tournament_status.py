with open('app/routes/category.py', 'r') as f:
    content = f.read()


old_code = """            elif action == 'start_category':
                participants_list = Participant.query.filter_by(category_id=category_id).all()"""

new_code = """            elif action == 'start_category':
                if tournament.status not in ['in_progress', 'completed']:
                    flash('You must start the overall Tournament before you can start individual categories.', 'error')
                    return redirect(url_for('category.manage_category', slug=slug, category_id=category_id))
                    
                participants_list = Participant.query.filter_by(category_id=category_id).all()"""

content = content.replace(old_code, new_code)

with open('app/routes/category.py', 'w') as f:
    f.write(content)

