import re

admin_start = "{% if current_user and current_user.role in ['admin', 'superadmin'] %}"
admin_end = "{% endif %}"

# Fix category/view.html
with open('app/templates/category/view.html', 'r') as f:
    cat = f.read()

# 1. Report result simple button (line ~110)
cat = re.sub(r'(<button onclick="openReportModal[^>]+>Report Result</button>)', 
             f"{admin_start}\\n\\1\\n{admin_end}", cat)

# 2. Match actions block
cat = re.sub(r'(<div class="match-actions">.*?</div>)',
             f"{admin_start}\\n\\1\\n{admin_end}", cat, flags=re.DOTALL)

# 3. Manage Category
cat = re.sub(r'(<a href="{{ url_for\(\'category.manage_category\'[^>]+>Manage Category</a>)',
             f"{admin_start}\\n\\1\\n{admin_end}", cat)

# 4. Start Knockout form
cat = re.sub(r'(<form method="POST"\s+action="{{ url_for\(\'category.start_knockout_stage\'.*?</form>)',
             f"{admin_start}\\n\\1\\n{admin_end}", cat, flags=re.DOTALL)

# 5. Finish category form
cat = re.sub(r'(<form method="POST"\s+action="{{ url_for\(\'category.manage_category\'.*?Finish Tournament.*?</form>)',
             f"{admin_start}\\n\\1\\n{admin_end}", cat, flags=re.DOTALL)

with open('app/templates/category/view.html', 'w') as f:
    f.write(cat)

# Fix tournament/view.html
with open('app/templates/tournament/view.html', 'r') as f:
    tourn = f.read()

# 1. Manage Tournament buttons
tourn = re.sub(r'(<a href="{{ url_for\(\'tournament.manage_tournament\'[^>]+>.*?Manage\s+Tournament</a>)',
               f"{admin_start}\\n\\1\\n{admin_end}", tourn, flags=re.DOTALL)

# 2. Create Category button
tourn = re.sub(r'(<a href="{{ url_for\(\'category.create_category\'[^>]+>.*?Create Category.*?</a>)',
               f"{admin_start}\\n\\1\\n{admin_end}", tourn, flags=re.DOTALL)

# 3. Add participants link (in empty state alert)
tourn = re.sub(r'(<a href="{{ url_for\(\'tournament.manage_tournament\'[^>]+>Add.*?participants.*?</a>)',
               f"{admin_start}\\n\\1\\n{admin_end}", tourn, flags=re.DOTALL)

# 4. Match actions block
tourn = re.sub(r'(<div class="match-actions">.*?</div>)',
               f"{admin_start}\\n\\1\\n{admin_end}", tourn, flags=re.DOTALL)

with open('app/templates/tournament/view.html', 'w') as f:
    f.write(tourn)

