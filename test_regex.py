import re

with open('app/templates/category/view.html', 'r') as f:
    content = f.read()

pattern = r'let currentManageMatchId = null;.*?(?={% endblock %})'
match = re.search(pattern, content, flags=re.DOTALL)
if match:
    print("MATCH FOUND")
else:
    print("NO MATCH")
