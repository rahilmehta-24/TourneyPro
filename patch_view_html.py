import re

with open('app/templates/player/view.html', 'r') as f:
    content = f.read()

target = """    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 2rem; margin-bottom: 2rem;">
        <!-- Biological & Contact Profile -->"""

replace = """    {% set is_authorized = current_user and (current_user.role in ['admin', 'superadmin'] or current_user.id == player.user_id) %}
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 2rem; margin-bottom: 2rem;">
        <!-- Biological & Contact Profile -->"""

if target in content:
    content = content.replace(target, replace)
    
    # Wrap the entire Personal Information card in an is_authorized block
    target2 = """        <div class="card">
            <div class="card-header">
                <h3 style="margin: 0; color: var(--accent-primary);"><i class="fas fa-id-card"></i> Personal Information</h3>
            </div>
            <div class="card-body">"""
            
    replace2 = """        {% if is_authorized %}
        <div class="card">
            <div class="card-header">
                <h3 style="margin: 0; color: var(--accent-primary);"><i class="fas fa-id-card"></i> Personal Information</h3>
            </div>
            <div class="card-body">"""
            
    content = content.replace(target2, replace2)
    
    # Close the if block before Registration & Coaching Profile
    target3 = """        <!-- Registration & Coaching Profile -->"""
    replace3 = """        {% endif %}
        
        <!-- Registration & Coaching Profile -->"""
        
    content = content.replace(target3, replace3)
    
    with open('app/templates/player/view.html', 'w') as f:
        f.write(content)
    print("view.html patched.")
else:
    print("Target not found.")
