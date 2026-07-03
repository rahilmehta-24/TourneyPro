
with open('app/templates/category/create.html', 'r') as f:
    content = f.read()

# Replace the javascript toggle for round_robin
# we need to hide `num_groups` and only require `teams_per_group`
old_rr_js = """        } else if (format === 'round_robin') {
            if (groupFields) {
                groupFields.style.display = 'block';
                // Show qualifiers and lucky losers just like group stage
                document.getElementById('qualifiers_per_group').closest('.form-group').style.display = 'block';
                document.getElementById('allow_lucky_losers').closest('.form-group').style.display = 'block';
                
                document.getElementById('num_groups').required = true;
                document.getElementById('teams_per_group').required = true;
            }"""

new_rr_js = """        } else if (format === 'round_robin') {
            if (groupFields) {
                groupFields.style.display = 'block';
                // Hide num_groups because it will be dynamically calculated based on total players
                document.getElementById('num_groups').closest('.form-group').style.display = 'none';
                document.getElementById('num_groups').required = false;
                
                document.getElementById('teams_per_group').required = true;
                document.getElementById('teams_per_group').min = "3";
                
                // Show qualifiers and lucky losers just like group stage
                document.getElementById('qualifiers_per_group').closest('.form-group').style.display = 'block';
                document.getElementById('allow_lucky_losers').closest('.form-group').style.display = 'block';
            }"""

if "document.getElementById('num_groups').closest('.form-group').style.display = 'none';" not in content:
    content = content.replace(old_rr_js, new_rr_js)
    
with open('app/templates/category/create.html', 'w') as f:
    f.write(content)
