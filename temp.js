let currentManageMatchId = null;

function handleStatusChange(status) {
    const scoringSection = document.getElementById('reportForm');
    if (status === 'in_progress' || status === 'completed') {
        scoringSection.style.display = 'block';
    } else {
        scoringSection.style.display = 'none';
    }
}

function openMatchModal(matchId, currentStatus, currentScheduledTime, p1Name, p1Id, p2Name, p2Id, isAdmin) {
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
