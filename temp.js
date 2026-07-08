<script>
function copyShareLink(url, btn) {
    navigator.clipboard.writeText(url).then(() => {
        const originalText = btn.innerText;
        btn.innerText = '✅ Copied!';
        setTimeout(() => {
            btn.innerText = originalText;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
        alert("Failed to copy link: " + url);
    });
}

async function updateMatchSchedule(matchId, dateTimeStr) {
    try {
        const response = await fetch(`/match/${matchId}/schedule`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ scheduled_time: dateTimeStr })
        });
        
        const data = await response.json();
        if (data.success) {
            window.location.reload();
        } else {
            alert('Error: ' + data.message);
        }
    } catch (err) {
        console.error('Error scheduling match:', err);
        alert('An error occurred while updating the match schedule: ' + err.message);
    }
}

async function toggleMatchStatus(matchId, checkbox) {
    const newStatus = checkbox.checked ? 'in_progress' : 'pending';
    
    try {
        const response = await fetch(`/match/${matchId}/toggle-status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        const data = await response.json();
        if (data.success) {
            window.location.reload();
        } else {
            alert('Error: ' + data.message);
            checkbox.checked = !checkbox.checked; // Revert
        }
    } catch (err) {
        console.error('Error toggling status:', err);
        alert('An error occurred while updating the match status.');
        checkbox.checked = !checkbox.checked; // Revert
    }
}



let currentManageMatchId = null;

function handleStatusChange(status) {
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
}

function openMatchModal(matchId, currentStatus, currentScheduledTime, p1Name, p1Id, p2Name, p2Id, isAdmin, score1, score2) {
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
    
    const savePendingBtn = document.getElementById('savePendingBtn');
    const saveLiveBtn = document.getElementById('saveLiveBtn');
    const completeMatchBtn = document.getElementById('completeMatchBtn');
    
    if (isReadOnly) {
        if (savePendingBtn) savePendingBtn.style.display = 'none';
        if (saveLiveBtn) saveLiveBtn.style.display = 'none';
        if (completeMatchBtn) completeMatchBtn.style.display = 'none';
    }

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
        formData.append('action', actionType);
        
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
function validateWinnerSelected() {
    const winner1 = document.getElementById('winner1');
    const winner2 = document.getElementById('winner2');
    if (!winner1.checked && !winner2.checked) {
        alert("Please select a winner to complete the match.");
        return false;
    }
    return true;
}

function checkTiebreak(setNum, winThreshold) {
    const p1Input = document.getElementById(`set${setNum}_p1`);
    const p2Input = document.getElementById(`set${setNum}_p2`);
    const tbRow = document.getElementById(`tbRow${setNum}`);
    
    if (!p1Input || !p2Input) return;
    
    const g1 = parseInt(p1Input.value) || 0;
    const g2 = parseInt(p2Input.value) || 0;
    
    const tbLose = winThreshold === 4 ? 3 : winThreshold;
    
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
        
        const tb1 = document.getElementById(`tb${setNum}_p1`);
        const tb2 = document.getElementById(`tb${setNum}_p2`);
        if(tb1) tb1.value = '';
        if(tb2) tb2.value = '';
    }
}
</script>
