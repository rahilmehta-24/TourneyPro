with open('app/routes/category.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.startswith("@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/delete', methods=['POST'])"):
        # Check if the next function definition is rename_category
        # We need to look ahead
        j = i
        found_rename = False
        while j < len(lines) and j < i + 10:
            if "def rename_category" in lines[j]:
                found_rename = True
                break
            j += 1
        
        if found_rename:
            # We found the orphaned decorators. Skip them.
            skip = True
            continue
    
    if skip and line.startswith("@category_bp.route('/tournaments/<slug>/categories/<int:category_id>/rename', methods=['POST'])"):
        skip = False
        
    if not skip:
        new_lines.append(line)

with open('app/routes/category.py', 'w') as f:
    f.writelines(new_lines)
