import re

def process_file(filepath, is_tournament=False):
    with open(filepath, 'r') as f:
        content = f.read()

    # 1. Update the manage-match-btn onclick
    if is_tournament:
        btn_pattern = r'onclick="openMatchModal\(\{\{ match\.id \}\}, \'\{\{ match\.status \}\}\', \'\{\{ match\.scheduled_time\.strftime\(\'%Y-%m-%dT%H:%M\'\) if match\.scheduled_time else \'\' \}\}\'\)"'
    else:
        btn_pattern = r'onclick="openMatchModal\(\{\{ match\.id \}\}, \'\{\{ match\.status \}\}\', \'\{\{ match\.scheduled_time\.strftime\(\'%Y-%m-%dT%H:%M\'\) if match\.scheduled_time else \'\' \}\}\'\)"'
        
    replacement = r'''onclick="openMatchModal({{ match.id }}, '{{ match.status }}', '{{ match.scheduled_time.strftime('%Y-%m-%dT%H:%M') if match.scheduled_time else '' }}', '{{ match.participant1.name|escape if match.participant1 else '' }}', {{ match.participant1_id or 'null' }}, '{{ match.participant2.name|escape if match.participant2 else '' }}', {{ match.participant2_id or 'null' }})"'''
    
    content = re.sub(btn_pattern, replacement, content)
    
    # 2. Delete the old openReportModal button entirely because it is now combined
    # find something like <div class="match-actions"> ... <button onclick="openReportModal..." ... </div>
    content = re.sub(r'{% if current_user and current_user\.role in \[\'admin\', \'superadmin\'\] %}\s*<div class="match-actions">\s*<button\s*onclick="openReportModal[^>]+>Report Result</button>\s*</div>\s*{% endif %}', '', content)
    
    # 3. Replace the entire JS and Modal section at the bottom.
    # We will locate `let currentManageMatchId = null;` up to `{% endblock %}`
    
    # But wait, there is `function checkTiebreak` earlier in the file?
    # No, checkTiebreak is at the end of the <script> block or near the modals.
    
    # Let's just output the file so we can see where checkTiebreak is.

process_file('app/templates/category/view.html')
