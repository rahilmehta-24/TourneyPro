import re

def process_file(filepath, is_tournament=False):
    with open(filepath, 'r') as f:
        content = f.read()

    # 1. Update the button
    if is_tournament:
        btn_pattern = r'''onclick="openMatchModal\(\{\{ match\.id \}\}, '\{\{ match\.status \}\}', '\{\{ match\.scheduled_time\.strftime\('%Y-%m-%dT%H:%M'\) if match\.scheduled_time else '' \}\}'\)'''
    else:
        btn_pattern = r'''onclick="openMatchModal\(\{\{ match\.id \}\}, '\{\{ match\.status \}\}', '\{\{ match\.scheduled_time\.strftime\('%Y-%m-%dT%H:%M'\) if match\.scheduled_time else '' \}\}'\)'''
        
    btn_repl = r'''onclick="openMatchModal({{ match.id }}, '{{ match.status }}', '{{ match.scheduled_time.strftime('%Y-%m-%dT%H:%M') if match.scheduled_time else '' }}', '{{ match.participant1.name|escape if match.participant1 else '' }}', {{ match.participant1_id or 'null' }}, '{{ match.participant2.name|escape if match.participant2 else '' }}', {{ match.participant2_id or 'null' }})"'''
    content = content.replace('''onclick="openMatchModal({{ match.id }}, '{{ match.status }}', '{{ match.scheduled_time.strftime('%Y-%m-%dT%H:%M') if match.scheduled_time else '' }}')"''', btn_repl)

    # 2. Delete reportModal
    report_modal_pattern = r'<div id="reportModal" class="modal">.*?</form>\s*</div>\s*</div>'
    content = re.sub(report_modal_pattern, '', content, flags=re.DOTALL)

    # 3. Replace Match Management Modal and associated JS
    # We will search for everything from `let currentManageMatchId = null;` to the end `{% endblock %}`
    js_and_modal_pattern = r'let currentManageMatchId = null;.*?(?={% endblock %})'
    
    new_js_and_modal = """
let currentManageMatchId = null;

function handleStatusChange(status) {
    const defaultActions = document.getElementById('modalActionsDefault');
    const scoringSection = document.getElementById('reportForm');
    
    if (status === 'in_progress' || status === 'completed') {
        defaultActions.style.display = 'none';
        scoringSection.style.display = 'block';
    } else {
        defaultActions.style.display = 'flex';
        scoringSection.style.display = 'none';
    }
}

function openMatchModal(matchId, currentStatus, currentScheduledTime, p1Name, p1Id, p2Name, p2Id) {
    currentManageMatchId = matchId;
    document.getElementById('modalMatchId').innerText = matchId;
    
    // Set status
    const statusSelect = document.getElementById('modalMatchStatus');
    statusSelect.value = currentStatus || 'pending';
    
    // Set time
    const timeInput = document.getElementById('modalMatchTime');
    if (currentScheduledTime && currentScheduledTime !== 'None') {
        timeInput.value = currentScheduledTime;
    } else {
        timeInput.value = '';
    }
    
    // Set form action
    const form = document.getElementById('reportForm');
    const slug = '{{ tournament.url_slug }}';
    const catId = '{{ category.id if category else 'null' }}';
    if (catId !== 'null') {
        form.action = `/tournaments/${slug}/categories/${catId}/match/${matchId}/report`;
    } else {
        form.action = `/tournaments/${slug}/match/${matchId}/report`;
    }

    // Set participants
    document.getElementById('winner1').value = p1Id;
    document.getElementById('winner1Label').textContent = p1Name;
    document.getElementById('p1SetHeader').textContent = p1Name;

    document.getElementById('winner2').value = p2Id;
    document.getElementById('winner2Label').textContent = p2Name;
    document.getElementById('p2SetHeader').textContent = p2Name;

    // Reset tiebreaks
    const numSets = {{ category.num_sets if category else (tournament.num_sets or 3) }};
    for (let s = 1; s <= numSets; s++) {
        const p1Input = document.getElementById(`set${s}_p1`);
        const p2Input = document.getElementById(`set${s}_p2`);
        if (p1Input) p1Input.readOnly = false;
        if (p2Input) p2Input.readOnly = false;
        
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

async function saveMatchManagement() {
    if (!currentManageMatchId) return;
    
    const status = document.getElementById('modalMatchStatus').value;
    const scheduledTime = document.getElementById('modalMatchTime').value;
    
    try {
        let success = true;
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
        
        const statusRes = await fetch(`/match/${currentManageMatchId}/toggle-status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: status })
        });
        const statusData = await statusRes.json();
        if (!statusData.success) {
            alert('Status Error: ' + statusData.message);
            success = false;
        }
        
        if (success) {
            window.location.reload();
        }
    } catch (err) {
        console.error('Error saving:', err);
        alert('An error occurred while saving.');
    }
}

function checkTiebreak(setNum, winThreshold) {
    const p1Input = document.getElementById(`set${setNum}_p1`);
    const p2Input = document.getElementById(`set${setNum}_p2`);
    const tbRow = document.getElementById(`tbRow${setNum}`);
    
    if (!p1Input || !p2Input) return;
    
    const g1 = parseInt(p1Input.value) || 0;
    const g2 = parseInt(p2Input.value) || 0;
    
    const tbLose = winThreshold === 4 ? 3 : winThreshold;
    
    // Lock at 6-6 (or 3-3)
    if (g1 === tbLose && g2 === tbLose) {
        p1Input.readOnly = true;
        p2Input.readOnly = true;
        p1Input.style.opacity = '0.7';
        p2Input.style.opacity = '0.7';
        
        if (tbRow) tbRow.style.display = 'table-row';
    } else {
        p1Input.readOnly = false;
        p2Input.readOnly = false;
        p1Input.style.opacity = '1';
        p2Input.style.opacity = '1';
        
        if (tbRow) tbRow.style.display = 'none';
        
        // Also clear TB scores if unlocking
        const tb1 = document.getElementById(`tb${setNum}_p1`);
        const tb2 = document.getElementById(`tb${setNum}_p2`);
        if(tb1) tb1.value = '';
        if(tb2) tb2.value = '';
    }
}
</script>

<!-- Match Management Modal -->
<div id="matchManagementModal" class="glass-modal-overlay" onclick="if(event.target === this) closeMatchModal()">
    <div class="glass-modal" style="max-height: 90vh; overflow-y: auto;">
        <span class="close" onclick="closeMatchModal()" style="position: absolute; top: 1rem; right: 1rem; font-size: 2rem; cursor: pointer; color: #94a3b8;">&times;</span>
        <h3>Match #<span id="modalMatchId"></span></h3>
        
        <div class="glass-modal-form-group">
            <label for="modalMatchStatus">Match Status</label>
            <select id="modalMatchStatus" onchange="handleStatusChange(this.value)">
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
            </select>
        </div>
        
        <div class="glass-modal-form-group">
            <label for="modalMatchTime">Scheduled Time</label>
            <input type="datetime-local" id="modalMatchTime">
        </div>
        
        <div class="glass-modal-actions" id="modalActionsDefault">
            <button class="glass-btn-secondary" onclick="closeMatchModal()">Cancel</button>
            <button class="glass-btn-primary" onclick="saveMatchManagement()">Save Changes</button>
        </div>
        
        <form id="reportForm" method="POST" style="display: none; margin-top: 1.5rem; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 1.5rem;">
            <div class="form-group" style="margin-bottom: 1.5rem;">
                <label class="form-label" style="display: block; margin-bottom: 1rem; font-weight: 600; font-size: 1.1rem;">Select Winner</label>
                <div class="winner-options" style="display: flex; flex-direction: column; gap: 1rem;">
                    <label class="winner-option" style="display: flex; align-items: center; padding: 1rem; background: rgba(0,0,0,0.3); border-radius: var(--radius-md); cursor: pointer;">
                        <input type="radio" name="winner_id" id="winner1" value="" style="margin-right: 1rem; width: 20px; height: 20px;">
                        <span id="winner1Label" style="font-size: 1.1rem; font-weight: 500;">Participant 1</span>
                    </label>
                    <label class="winner-option" style="display: flex; align-items: center; padding: 1rem; background: rgba(0,0,0,0.3); border-radius: var(--radius-md); cursor: pointer;">
                        <input type="radio" name="winner_id" id="winner2" value="" style="margin-right: 1rem; width: 20px; height: 20px;">
                        <span id="winner2Label" style="font-size: 1.1rem; font-weight: 500;">Participant 2</span>
                    </label>
                </div>
            </div>
            
            <label class="form-label" style="font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem; display: block;">Set Scores</label>
            <table style="width: 100%; border-collapse: collapse; margin-top: 0.5rem;">
                <thead>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <th style="padding: 0.5rem; text-align: left; color: var(--text-secondary);">Set</th>
                        <th id="p1SetHeader" style="padding: 0.5rem; text-align: center; color: var(--text-secondary);">Player 1</th>
                        <th id="p2SetHeader" style="padding: 0.5rem; text-align: center; color: var(--text-secondary);">Player 2</th>
                    </tr>
                </thead>
                <tbody>
                    {% set num_sets_val = category.num_sets if category else (tournament.num_sets or 3) %}
                    {% set games_per_set_val = category.games_per_set if category else (tournament.games_per_set or 6) %}
                    {% for s in range(1, num_sets_val + 1) %}
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.02);">
                        <td style="padding: 0.75rem 0.5rem; font-weight: bold; color: var(--text-secondary);">Set {{ s }}</td>
                        <td style="padding: 0.75rem 0.5rem; text-align: center;">
                            <input type="number" name="set{{ s }}_p1" id="set{{ s }}_p1" min="0" class="form-input" style="width: 60px; text-align:center; padding: 4px;" oninput="checkTiebreak({{ s }}, {{ games_per_set_val }})">
                        </td>
                        <td style="padding: 0.75rem 0.5rem; text-align: center;">
                            <input type="number" name="set{{ s }}_p2" id="set{{ s }}_p2" min="0" class="form-input" style="width: 60px; text-align:center; padding: 4px;" oninput="checkTiebreak({{ s }}, {{ games_per_set_val }})">
                        </td>
                    </tr>
                    <!-- Tiebreak Row (Hidden by default) -->
                    <tr id="tbRow{{ s }}" style="display: none; background: rgba(255,165,0,0.1);">
                        <td style="padding: 0.5rem; color: #ffb74d; font-size: 0.85rem; text-align: right;">Tiebreak Pts:</td>
                        <td style="padding: 0.5rem; text-align: center;">
                            <input type="number" name="tb{{ s }}_p1" id="tb{{ s }}_p1" min="0" class="form-input" style="width: 60px; text-align:center; padding: 4px; border-color: #ffb74d;">
                        </td>
                        <td style="padding: 0.5rem; text-align: center;">
                            <input type="number" name="tb{{ s }}_p2" id="tb{{ s }}_p2" min="0" class="form-input" style="width: 60px; text-align:center; padding: 4px; border-color: #ffb74d;">
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            <div class="glass-modal-actions" style="justify-content: flex-end; gap: 1rem; margin-top: 2rem;">
                <button type="button" class="glass-btn-secondary" onclick="closeMatchModal()">Cancel</button>
                <button type="submit" name="action" value="live_score" class="glass-btn-secondary">Save Live Score</button>
                <button type="submit" name="action" value="complete_match" class="glass-btn-primary">Complete Match</button>
            </div>
        </form>
    </div>
</div>
"""
    
    # We also need to remove the old checkTiebreak script if it's there
    content = re.sub(r'<script>\s*function checkTiebreak.*?</script>', '', content, flags=re.DOTALL)
    
    # And openReportModal
    content = re.sub(r'<script>\s*function openReportModal.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<script>\s*function validateWinnerSelected.*?</script>', '', content, flags=re.DOTALL)

    content = re.sub(js_and_modal_pattern, new_js_and_modal, content, flags=re.DOTALL)
    
    with open(filepath, 'w') as f:
        f.write(content)

process_file('app/templates/category/view.html', is_tournament=False)
process_file('app/templates/tournament/view.html', is_tournament=True)
