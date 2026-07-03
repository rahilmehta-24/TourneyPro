with open('app/templates/category/create.html', 'r') as f:
    content = f.read()

content = content.replace("""            if (groupFields) {
                groupFields.style.display = 'block';
                // Hide qualifiers and lucky losers for pure round robin
                document.getElementById('qualifiers_per_group').closest('.form-group').style.display = 'none';
                document.getElementById('allow_lucky_losers').closest('.form-group').style.display = 'none';
                document.getElementById('num_groups').required = true;
                document.getElementById('teams_per_group').required = true;
            }
            if (groupFields) groupFields.style.display = 'none';""", """            if (groupFields) {
                groupFields.style.display = 'block';
                // Hide qualifiers and lucky losers for pure round robin
                document.getElementById('qualifiers_per_group').closest('.form-group').style.display = 'none';
                document.getElementById('allow_lucky_losers').closest('.form-group').style.display = 'none';
                
                // Make them not strictly required so a single large pool can be created by leaving them blank
                document.getElementById('num_groups').required = false;
                document.getElementById('teams_per_group').required = false;
            }""")

with open('app/templates/category/create.html', 'w') as f:
    f.write(content)
