def fix_category():
    with open('app/routes/category.py', 'r') as f:
        lines = f.readlines()
    
    with open('app/routes/category.py', 'w') as f:
        for i, line in enumerate(lines):
            # Fix live update flash
            if "flash('Live score updated successfully.', 'success')" in line:
                line = "            flash('Live score updated successfully.', 'success')\n"
            
            # The exception might be caused by a missing 'try' or an extra 'try'
            f.write(line)

def fix_tournament():
    with open('app/routes/tournament.py', 'r') as f:
        lines = f.readlines()
    
    with open('app/routes/tournament.py', 'w') as f:
        for i, line in enumerate(lines):
            if "flash('Live score updated successfully.', 'success')" in line:
                line = "            flash('Live score updated successfully.', 'success')\n"
            f.write(line)

fix_category()
fix_tournament()
