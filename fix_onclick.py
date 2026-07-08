import re

def fix_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # The broken string is:
    # onclick="openMatchModal(... else 'false' }}), '{{ match.score1 or '' }}', '{{ match.score2 or '' }}')\"
    # We want to change it to:
    # onclick="openMatchModal(... else 'false' }}, '{{ match.score1 or '' }}', '{{ match.score2 or '' }}')"
    
    # Let's match the broken pattern exactly.
    pattern = r"onclick=\"openMatchModal\((.*?)else 'false' \}\}\), '\{\{ match\.score1 or '' \}\}', '\{\{ match\.score2 or '' \}\}'\)\\\""
    replacement = r"onclick=\"openMatchModal(\1else 'false' }}, '{{ match.score1 or '' }}', '{{ match.score2 or '' }}')\""
    
    content = re.sub(pattern, replacement, content)
    
    with open(filename, 'w') as f:
        f.write(content)

fix_file('app/templates/category/view.html')
fix_file('app/templates/tournament/view.html')
