import re

def update_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # 1. Update match cards to have onclick instead of the manage button
    # Look for the manage-match-btn blocks and remove them
    manage_btn_pattern = r'{%\s*if\s+current_user\s+and\s+current_user\.role\s+in\s+\[\'admin\',\s*\'superadmin\'\]\s+and\s+match\.status\s+!=\s+\'completed\'\s+and\s+match\.participant1\s+and\s+match\.participant2\s*%}.*?{%\s*endif\s*%}'
    content = re.sub(manage_btn_pattern, '', content, flags=re.DOTALL)
    
    # In round-robin cards, there is a wrapper div for the button that might be left empty, but the regex above matches the whole block if we make sure it's clean.
    # Let's write a regex that safely removes the block
    btn_wrapper_pattern = r'<div style="display:\s*flex;\s*align-items:\s*center;\s*gap:\s*8px;">\s*{%\s*if\s+current_user\s+and\s+current_user\.role\s+in\s+\[\'admin\',\s*\'superadmin\'\]\s+and\s+match\.status\s+!=\s+\'completed\'\s+and\s+match\.participant1\s+and\s+match\.participant2\s*%}.*?{%\s*endif\s*%}\s*</div>'
    content = re.sub(btn_wrapper_pattern, '', content, flags=re.DOTALL)
    
    # Wait, the match-card in round robin is:
    # <div class="match-card {% if match.status == 'completed' %}completed{% endif %}">
    # Let's replace the opening tag for tennis-match and match-card to include the onclick and hover class
    
    # For bracket matches:
    # <div class="tennis-match {% if match.status == 'completed' %}tennis-match-completed{% endif %}">
    tennis_match_repl = r'<div class="tennis-match {% if match.status == \'completed\' %}tennis-match-completed{% endif %} {% if match.participant1 and match.participant2 %}clickable-match{% endif %}" {% if match.participant1 and match.participant2 %}onclick="openMatchModal({{ match.id }}, \'{{ match.status }}\', \'{{ match.scheduled_time.strftime(\'%Y-%m-%dT%H:%M\') if match.scheduled_time else \'\' }}\', \'{{ match.participant1.name|escape if match.participant1 else \'\' }}\', {{ match.participant1_id or \'null\' }}, \'{{ match.participant2.name|escape if match.participant2 else \'\' }}\', {{ match.participant2_id or \'null\' }}, {{ \'true\' if current_user and current_user.role in [\'admin\', \'superadmin\'] else \'false\' }})" title="Click to view details"{% endif %}>'
    
    content = re.sub(
        r'<div class="tennis-match \{\% if match\.status == \'completed\' \%\}tennis-match-completed\{\% endif \%\}">',
        tennis_match_repl,
        content
    )
    
    # For round robin matches:
    # <div class="match-card {% if match.status == 'completed' %}completed{% endif %}">
    match_card_repl = r'<div class="match-card {% if match.status == \'completed\' %}completed{% endif %} {% if match.participant1 and match.participant2 %}clickable-match{% endif %}" {% if match.participant1 and match.participant2 %}onclick="openMatchModal({{ match.id }}, \'{{ match.status }}\', \'{{ match.scheduled_time.strftime(\'%Y-%m-%dT%H:%M\') if match.scheduled_time else \'\' }}\', \'{{ match.participant1.name|escape if match.participant1 else \'\' }}\', {{ match.participant1_id or \'null\' }}, \'{{ match.participant2.name|escape if match.participant2 else \'\' }}\', {{ match.participant2_id or \'null\' }}, {{ \'true\' if current_user and current_user.role in [\'admin\', \'superadmin\'] else \'false\' }})" title="Click to view details"{% endif %}>'
    
    content = re.sub(
        r'<div class="match-card \{\% if match\.status == \'completed\' \%\}completed\{\% endif \%\}">',
        match_card_repl,
        content
    )
    
    # 2. Update Modal HTML to include the tick button
    old_time_html = r'<div class="glass-modal-form-group">\s*<label for="modalMatchTime">Scheduled Time</label>\s*<input type="datetime-local" id="modalMatchTime">\s*</div>'
    new_time_html = """<div class="glass-modal-form-group" style="display: flex; gap: 8px; align-items: flex-end;">
            <div style="flex-grow: 1;">
                <label for="modalMatchTime">Scheduled Time</label>
                <input type="datetime-local" id="modalMatchTime" style="width: 100%;">
            </div>
            <button type="button" id="saveTimeBtn" class="glass-btn-primary" onclick="saveDateTimeOnly()" style="padding: 0.75rem; height: 42px; display: flex; align-items: center; justify-content: center; margin-bottom: 2px;" title="Save Date & Time">✔️</button>
        </div>"""
    
    content = re.sub(old_time_html, new_time_html, content)
    
    # 3. Update JavaScript logic
    # Replace openMatchModal and saveMatchManagement
    js_pattern = r'function openMatchModal.*?function closeMatchModal\(\) {.*?}.*?async function saveMatchManagement\(\) {.*?}\n'
    
    new_js = """function openMatchModal(matchId, currentStatus, currentScheduledTime, p1Name, p1Id, p2Name, p2Id, isAdmin) {
    currentManageMatchId = matchId;
    document.getElementById('modalMatchId').innerText = matchId;
    
    const statusSelect = document.getElementById('modalMatchStatus');
    statusSelect.value = currentStatus || 'pending';
    
    const timeInput = document.getElementById('modalMatchTime');
    if (currentScheduledTime && currentScheduledTime !== 'None') {
        timeInput.value = currentScheduledTime;
    } else {
        timeInput.value = '';
    }
    
    const form = document.getElementById('reportForm');
    const slug = '{{ tournament.url_slug }}';
    const catId = '{{ category.id if category else 'null' }}';
    if (catId !== 'null') {
        form.action = `/tournaments/${slug}/categories/${catId}/match/${matchId}/report`;
    } else {
        form.action = `/tournaments/${slug}/match/${matchId}/report`;
    }

    document.getElementById('winner1').value = p1Id;
    document.getElementById('winner1Label').textContent = p1Name;
    document.getElementById('p1SetHeader').textContent = p1Name;

    document.getElementById('winner2').value = p2Id;
    document.getElementById('winner2Label').textContent = p2Name;
    document.getElementById('p2SetHeader').textContent = p2Name;
    
    const isReadOnly = (!isAdmin || currentStatus === 'completed');
    
    // Apply read-only states
    statusSelect.disabled = isReadOnly;
    timeInput.disabled = isReadOnly;
    document.getElementById('winner1').disabled = isReadOnly;
    document.getElementById('winner2').disabled = isReadOnly;
    
    const saveTimeBtn = document.getElementById('saveTimeBtn');
    if (saveTimeBtn) saveTimeBtn.style.display = isReadOnly ? 'none' : 'flex';
    
    const saveChangesBtn = document.getElementById('saveChangesBtn');
    if (saveChangesBtn) saveChangesBtn.style.display = isReadOnly ? 'none' : 'block';

    const numSets = {{ category.num_sets if category else (tournament.num_sets or 3) }};
    for (let s = 1; s <= numSets; s++) {
        const p1Input = document.getElementById(`set${s}_p1`);
        const p2Input = document.getElementById(`set${s}_p2`);
        if (p1Input) p1Input.disabled = isReadOnly;
        if (p2Input) p2Input.disabled = isReadOnly;
        
        const tbP1 = document.getElementById(`tb${s}_p1`);
        const tbP2 = document.getElementById(`tb${s}_p2`);
        if (tbP1) tbP1.disabled = isReadOnly;
        if (tbP2) tbP2.disabled = isReadOnly;
        
        const tbRow = document.getElementById(`tbRow${s}`);
        if (tbRow) tbRow.style.display = 'none';
    }
    
    handleStatusChange(statusSelect.value);
    document.getElementById('matchManagementModal').classList.add('active');
}

function closeMatchModal() {
    document.getElementById('matchManagementModal').classList.remove('active');
    currentManageMatchId = null;
}

async function saveDateTimeOnly() {
    if (!currentManageMatchId) return;
    const scheduledTime = document.getElementById('modalMatchTime').value;
    try {
        const schedRes = await fetch(`/match/${currentManageMatchId}/schedule`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scheduled_time: scheduledTime })
        });
        const schedData = await schedRes.json();
        if (schedData.success) {
            // Flash a small checkmark or just reload
            window.location.reload();
        } else {
            alert('Schedule Error: ' + schedData.message);
        }
    } catch (err) {
        console.error(err);
        alert('Error saving date and time');
    }
}

async function saveMatchManagement() {
    if (!currentManageMatchId) return;
    
    const status = document.getElementById('modalMatchStatus').value;
    const scheduledTime = document.getElementById('modalMatchTime').value;
    
    let success = true;
    
    try {
        const schedRes = await fetch(`/match/${currentManageMatchId}/schedule`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scheduled_time: scheduledTime })
        });
        const schedData = await schedRes.json();
        if (!schedData.success) {
            alert('Schedule Error: ' + schedData.message);
            success = false;
        }
    } catch (err) {
        console.error(err);
        success = false;
    }
    
    if (status === 'pending') {
        try {
            const statusRes = await fetch(`/match/${currentManageMatchId}/toggle-status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'pending' })
            });
            const statusData = await statusRes.json();
            if (!statusData.success) {
                alert('Status Error: ' + statusData.message);
                success = false;
            }
        } catch (err) {
            console.error(err);
            success = false;
        }
    } else {
        if (status === 'completed' && !validateWinnerSelected()) {
            return;
        }
        
        const form = document.getElementById('reportForm');
        const formData = new FormData(form);
        formData.append('action', status === 'completed' ? 'complete_match' : 'live_score');
        
        try {
            const reportRes = await fetch(form.action, {
                method: 'POST',
                body: formData
            });
            if (!reportRes.ok) {
                alert('Error updating score.');
                success = false;
            }
        } catch (err) {
            console.error(err);
            success = false;
        }
    }
    
    if (success) {
        window.location.reload();
    }
}
"""
    content = re.sub(js_pattern, new_js, content, flags=re.DOTALL)
    
    # Also need to make sure the modal save button has the ID 'saveChangesBtn'
    btn_pattern = r'<button type="button" class="glass-btn-primary" onclick="saveMatchManagement\(\)">Save Changes</button>'
    btn_repl = r'<button type="button" id="saveChangesBtn" class="glass-btn-primary" onclick="saveMatchManagement()">Save Changes</button>'
    content = re.sub(btn_pattern, btn_repl, content)

    # Let's add the CSS for clickable match cards
    css_pattern = r'</style>'
    css_repl = r'''.clickable-match {
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .clickable-match:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        border-color: rgba(255,255,255,0.2);
    }
</style>'''
    if '.clickable-match' not in content:
        content = re.sub(css_pattern, css_repl, content)

    with open(filename, 'w') as f:
        f.write(content)

update_file('app/templates/category/view.html')
update_file('app/templates/tournament/view.html')

