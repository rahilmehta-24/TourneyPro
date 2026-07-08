
def fix_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # Replace `if (status === 'pending') {` with `if (actionType === 'pending') {`
    content = content.replace("if (status === 'pending') {", "if (actionType === 'pending') {")

    # The validation was: `if (status === 'completed' && !validateWinnerSelected()) {`
    # Replace with `if (actionType === 'complete_match' && !validateWinnerSelected()) {`
    content = content.replace("if (status === 'completed' && !validateWinnerSelected()) {", "if (actionType === 'complete_match' && !validateWinnerSelected()) {")

    # In handleStatusChange, instead of only showing one button based on dropdown,
    # let's just ALWAYS show the buttons based on the *action* we want to allow?
    # No, it's fine if they change the dropdown to reveal the buttons,
    # BUT if the match is pending, they might want to click "Save Live Score" directly without changing the dropdown!
    # So if status is pending, show BOTH 'Save Changes' (pending) AND 'Save Live Score'.
    
    old_handle = """        if (savePendingBtn) savePendingBtn.style.display = (status === 'pending') ? 'block' : 'none';
        if (saveLiveBtn) saveLiveBtn.style.display = (status === 'in_progress') ? 'block' : 'none';"""
        
    new_handle = """        if (savePendingBtn) savePendingBtn.style.display = (status === 'pending') ? 'block' : 'none';
        if (saveLiveBtn) saveLiveBtn.style.display = (status === 'in_progress' || status === 'pending') ? 'block' : 'none';"""
    
    content = content.replace(old_handle, new_handle)

    with open(filename, 'w') as f:
        f.write(content)

fix_file('app/templates/category/view.html')
fix_file('app/templates/tournament/view.html')
