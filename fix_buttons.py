
def fix_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # 1. Fix HTML Buttons
    # Find the Save Changes button
    # It looks like: <button type="button" id="saveChangesBtn" class="glass-btn-primary" onclick="saveMatchManagement()">Save Changes</button>
    
    old_btn = '<button type="button" id="saveChangesBtn" class="glass-btn-primary" onclick="saveMatchManagement()">Save Changes</button>'
    new_btns = """<button type="button" id="savePendingBtn" class="glass-btn-primary" onclick="saveMatchAction('pending')">Save Changes</button>
            <button type="button" id="saveLiveBtn" class="glass-btn-warning" onclick="saveMatchAction('live_score')" style="display: none; background: rgba(234, 179, 8, 0.2); border: 1px solid rgba(234, 179, 8, 0.3); color: #fde047;">Save Live Score</button>
            <button type="button" id="completeMatchBtn" class="glass-btn-success" onclick="saveMatchAction('complete_match')" style="display: none;">Complete Match</button>"""
    
    content = content.replace(old_btn, new_btns)

    # 2. Fix JS function name and actionType injection
    # Replace `async function saveMatchManagement() {` with `async function saveMatchAction(actionType) {`
    content = content.replace("async function saveMatchManagement() {", "async function saveMatchAction(actionType) {")
    
    # Replace `formData.append('action', status === 'completed' ? 'complete_match' : 'live_score');`
    # with `formData.append('action', actionType);`
    content = content.replace("formData.append('action', status === 'completed' ? 'complete_match' : 'live_score');", "formData.append('action', actionType);")

    # 3. Fix handleStatusChange to ALWAYS show the scoring section if not disabled!
    # The previous logic was hiding the scoring section for 'pending'. 
    # Let's fix that too:
    old_handle_status = """    if (scoringSection) {
        scoringSection.style.display = (status === 'in_progress' || status === 'completed') ? 'block' : 'none';
    }"""
    
    new_handle_status = """    if (scoringSection) {
        scoringSection.style.display = (isAdmin || status === 'in_progress' || status === 'completed') ? 'block' : 'none';
    }"""
    content = content.replace(old_handle_status, new_handle_status)

    with open(filename, 'w') as f:
        f.write(content)

fix_file('app/templates/category/view.html')
fix_file('app/templates/tournament/view.html')
