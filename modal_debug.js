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
