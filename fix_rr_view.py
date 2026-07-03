with open('app/routes/category.py', 'r') as f:
    content = f.read()

# Make sure we pass rr_matches
content = content.replace(
    "return render_template('category/view.html',",
    """rr_matches = [m for m in matches if m.match_type == 'round_robin']
    
    if category.status == 'setup' and not rr_matches and category.format == 'round_robin' and not category.num_groups:
        rr_matches = [DummyMatch(**d) for d in dummy_data]
    
    return render_template('category/view.html',
                         rr_matches=rr_matches,"""
)
with open('app/routes/category.py', 'w') as f:
    f.write(content)
