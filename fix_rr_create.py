with open('app/templates/category/create.html', 'r') as f:
    content = f.read()

content = content.replace("if (format === 'round_robin') {", """if (format === 'round_robin') {
            if (groupFields) {
                groupFields.style.display = 'block';
                // Hide qualifiers and lucky losers for pure round robin
                document.getElementById('qualifiers_per_group').closest('.form-group').style.display = 'none';
                document.getElementById('allow_lucky_losers').closest('.form-group').style.display = 'none';
                document.getElementById('num_groups').required = true;
                document.getElementById('teams_per_group').required = true;
            }""")
            
content = content.replace("if (groupFields) groupFields.style.display = 'block';", """if (groupFields) {
                groupFields.style.display = 'block';
                document.getElementById('qualifiers_per_group').closest('.form-group').style.display = 'block';
                document.getElementById('allow_lucky_losers').closest('.form-group').style.display = 'block';
            }""")

with open('app/templates/category/create.html', 'w') as f:
    f.write(content)
