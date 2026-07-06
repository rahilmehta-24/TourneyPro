import re

def fix_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # The issue is the duplicated fragment of saveMatchManagement.
    # It looks like:
    #     if (success) {
    #         window.location.reload();
    #     }
    # }
    #     } catch (err) {
    #         console.error(err);
    #         success = false;
    #     }
    # ... down to the next function validateWinnerSelected() {
    
    pattern = r'async function saveMatchManagement\(\) \{.*?(?=function validateWinnerSelected\(\) \{)'
    
    new_js = """async function saveMatchManagement() {
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
    content = re.sub(pattern, new_js, content, flags=re.DOTALL)
    
    with open(filename, 'w') as f:
        f.write(content)

fix_file('app/templates/category/view.html')
fix_file('app/templates/tournament/view.html')
