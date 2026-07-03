with open('app/templates/category/view.html', 'r') as f:
    lines = f.readlines()

groups_start = -1
for i, line in enumerate(lines):
    if "{% if groups_data %}" in line:
        groups_start = i
        break

rounds_start = -1
for i, line in enumerate(lines):
    if "{% if rounds %}" in line:
        rounds_start = i
        break

rounds_end = rounds_start
for i in range(rounds_start, len(lines)):
    if "{% endif %}" in lines[i] and i > 470:
        rounds_end = i
        break

if groups_start != -1 and rounds_start != -1 and rounds_end != rounds_start:
    rounds_block = lines[rounds_start:rounds_end+1]
    
    new_lines = lines[:rounds_start] + lines[rounds_end+1:]
    new_lines = new_lines[:groups_start] + rounds_block + new_lines[groups_start:]
    
    with open('app/templates/category/view.html', 'w') as f:
        f.writelines(new_lines)
    print("Reordered successfully!")
else:
    print("Failed")
