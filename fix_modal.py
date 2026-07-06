import re

def fix_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # 1. Update onclick handler in match cards to pass score1 and score2
    # Before: onclick="openMatchModal({{ match.id }}, '{{ match.status }}', '{{ match.scheduled_time... }}', '{{ match.participant1.name... }}', {{ match.participant1_id or 'null' }}, '{{ match.participant2.name... }}', {{ match.participant2_id or 'null' }}, {{ 'true' if current_user... else 'false' }})"
    # After: append ', '{{ match.score1 or '' }}', '{{ match.score2 or '' }}'
    
    content = re.sub(
        r"(onclick=\"openMatchModal\(.*?{{ 'true' if current_user.*?else 'false' }}\))\"",
        r"\1, '{{ match.score1 or '' }}', '{{ match.score2 or '' }}')\"",
        content
    )

    # 2. Update modal buttons HTML
    # Find: <button type="button" id="saveChangesBtn"...>Save Changes</button>
    old_buttons = r'<button type="button" id="saveChangesBtn" class="glass-btn-primary" onclick="saveMatchManagement\(\)">Save Changes</button>'
    new_buttons = """<button type="button" id="savePendingBtn" class="glass-btn-primary" onclick="saveMatchAction('pending')">Save Changes</button>
            <button type="button" id="saveLiveBtn" class="glass-btn-warning" onclick="saveMatchAction('live_score')" style="display: none; background: rgba(234, 179, 8, 0.2); border: 1px solid rgba(234, 179, 8, 0.3); color: #fde047;">Save Live Score</button>
            <button type="button" id="completeMatchBtn" class="glass-btn-success" onclick="saveMatchAction('complete_match')" style="display: none;">Complete Match</button>"""
    content = content.replace(old_buttons, new_buttons)

    # 3. Update JS openMatchModal signature and logic
    old_open_sig = r'function openMatchModal\(matchId, currentStatus, currentScheduledTime, p1Name, p1Id, p2Name, p2Id, isAdmin\) \{'
    new_open_sig = r'function openMatchModal(matchId, currentStatus, currentScheduledTime, p1Name, p1Id, p2Name, p2Id, isAdmin, score1, score2) {'
    content = content.replace('function openMatchModal(matchId, currentStatus, currentScheduledTime, p1Name, p1Id, p2Name, p2Id, isAdmin) {', new_open_sig)

    # In openMatchModal, replace the old saveChangesBtn logic with the new buttons
    old_save_btn_logic = r"""const saveChangesBtn = document.getElementById\('saveChangesBtn'\);
    if \(saveChangesBtn\) saveChangesBtn.style.display = isReadOnly \? 'none' : 'block';"""
    
    new_save_btn_logic = """const savePendingBtn = document.getElementById('savePendingBtn');
    const saveLiveBtn = document.getElementById('saveLiveBtn');
    const completeMatchBtn = document.getElementById('completeMatchBtn');
    
    if (isReadOnly) {
        if (savePendingBtn) savePendingBtn.style.display = 'none';
        if (saveLiveBtn) saveLiveBtn.style.display = 'none';
        if (completeMatchBtn) completeMatchBtn.style.display = 'none';
    }"""
    content = re.sub(old_save_btn_logic, new_save_btn_logic, content)

    # Add score parsing loop
    # Right after the loop that enables/disables inputs
    score_parsing = """
    // Pre-populate existing scores if available
    for (let s = 1; s <= numSets; s++) {
        const p1Input = document.getElementById(`set${s}_p1`);
        const p2Input = document.getElementById(`set${s}_p2`);
        const tb1Input = document.getElementById(`tb${s}_p1`);
        const tb2Input = document.getElementById(`tb${s}_p2`);
        const tbRow = document.getElementById(`tbRow${s}`);
        
        if (p1Input) p1Input.value = '';
        if (p2Input) p2Input.value = '';
        if (tb1Input) tb1Input.value = '';
        if (tb2Input) tb2Input.value = '';
        if (tbRow) tbRow.style.display = 'none';
    }
    
    if (score1) {
        const s1Parts = score1.split(', ');
        const s2Parts = (score2 || '').split(', ');
        
        for (let i = 0; i < s1Parts.length; i++) {
            const s = i + 1;
            if (s > numSets) break;
            
            let s1Val = s1Parts[i];
            let tb1 = null;
            if (s1Val.includes('(')) {
                tb1 = s1Val.split('(')[1].replace(')', '');
                s1Val = s1Val.split('(')[0];
            }
            
            let s2Val = s2Parts[i] || '';
            let tb2 = null;
            if (s2Val.includes('(')) {
                tb2 = s2Val.split('(')[1].replace(')', '');
                s2Val = s2Val.split('(')[0];
            }
            
            const p1Input = document.getElementById(`set${s}_p1`);
            const p2Input = document.getElementById(`set${s}_p2`);
            if (p1Input) p1Input.value = s1Val;
            if (p2Input) p2Input.value = s2Val;
            
            if ((tb1 !== null || tb2 !== null) && tb1 !== '' && tb2 !== '') {
                const tbRow = document.getElementById(`tbRow${s}`);
                if (tbRow) tbRow.style.display = 'table-row';
                const tb1Input = document.getElementById(`tb${s}_p1`);
                const tb2Input = document.getElementById(`tb${s}_p2`);
                if (tb1Input && tb1 !== null) tb1Input.value = tb1;
                if (tb2Input && tb2 !== null) tb2Input.value = tb2;
                
                if (p1Input) p1Input.readOnly = true;
                if (p2Input) p2Input.readOnly = true;
            }
        }
    }
"""
    # Insert this before handleStatusChange(statusSelect.value);
    content = content.replace("handleStatusChange(statusSelect.value);", score_parsing + "\n    handleStatusChange(statusSelect.value);")

    # 4. Update handleStatusChange
    old_handle_status = r"""function handleStatusChange\(status\) \{
    const scoringSection = document.getElementById\('reportForm'\);
    if \(status === 'in_progress' \|\| status === 'completed'\) \{
        scoringSection.style.display = 'block';
    \} else \{
        scoringSection.style.display = 'none';
    \}
\}"""
    new_handle_status = """function handleStatusChange(status) {
    const scoringSection = document.getElementById('reportForm');
    const savePendingBtn = document.getElementById('savePendingBtn');
    const saveLiveBtn = document.getElementById('saveLiveBtn');
    const completeMatchBtn = document.getElementById('completeMatchBtn');
    const statusSelect = document.getElementById('modalMatchStatus');
    const isAdmin = !statusSelect.disabled;
    
    if (scoringSection) {
        scoringSection.style.display = (status === 'in_progress' || status === 'completed') ? 'block' : 'none';
    }
    
    if (isAdmin) {
        if (savePendingBtn) savePendingBtn.style.display = (status === 'pending') ? 'block' : 'none';
        if (saveLiveBtn) saveLiveBtn.style.display = (status === 'in_progress') ? 'block' : 'none';
        if (completeMatchBtn) completeMatchBtn.style.display = (status === 'completed') ? 'block' : 'none';
    }
}"""
    content = re.sub(old_handle_status, new_handle_status, content, flags=re.DOTALL)

    # 5. Update saveMatchManagement to saveMatchAction(actionType)
    old_save_match = r"async function saveMatchManagement\(\) \{"
    new_save_match = "async function saveMatchAction(actionType) {"
    content = content.replace(old_save_match, new_save_match)

    # In the new function, instead of formData.append('action', status === 'completed' ? 'complete_match' : 'live_score');
    # Use actionType!
    content = content.replace("formData.append('action', status === 'completed' ? 'complete_match' : 'live_score');", "formData.append('action', actionType);")

    with open(filename, 'w') as f:
        f.write(content)

fix_file('app/templates/category/view.html')
fix_file('app/templates/tournament/view.html')
