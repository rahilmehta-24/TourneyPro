import re

def fix_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # Remove inline style from saveLiveBtn
    content = content.replace(
        '''<button type="button" id="saveLiveBtn" class="glass-btn-warning" onclick="saveMatchAction('live_score')" style="display: none; background: rgba(234, 179, 8, 0.2); border: 1px solid rgba(234, 179, 8, 0.3); color: #fde047;">Save Live Score</button>''',
        '''<button type="button" id="saveLiveBtn" class="glass-btn-warning" onclick="saveMatchAction('live_score')" style="display: none;">Save Live Score</button>'''
    )

    with open(filename, 'w') as f:
        f.write(content)

fix_file('app/templates/category/view.html')
fix_file('app/templates/tournament/view.html')
