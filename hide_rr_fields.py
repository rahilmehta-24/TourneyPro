with open('app/templates/category/create.html', 'r') as f:
    content = f.read()

old_js = """                // Show qualifiers and lucky losers just like group stage
                document.getElementById('qualifiers_per_group').closest('.form-group').style.display = 'block';
                document.getElementById('allow_lucky_losers').closest('.form-group').style.display = 'block';"""

new_js = """                // Hide qualifiers and lucky losers for pure round robin
                document.getElementById('qualifiers_per_group').closest('.form-group').style.display = 'none';
                document.getElementById('allow_lucky_losers').closest('.form-group').style.display = 'none';"""

content = content.replace(old_js, new_js)

with open('app/templates/category/create.html', 'w') as f:
    f.write(content)
