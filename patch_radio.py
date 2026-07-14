with open('app/templates/category/view.html', 'r') as f:
    content = f.read()

target = """    document.getElementById('winner2').value = p2Id;
    document.getElementById('winner2Label').textContent = p2Name;
    document.getElementById('p2SetHeader').textContent = p2Name; document.getElementById('p1PointsHeader').textContent = p1Name; document.getElementById('p2PointsHeader').textContent = p2Name;"""

replacement = """    document.getElementById('winner2').value = p2Id;
    document.getElementById('winner2Label').textContent = p2Name;
    document.getElementById('p2SetHeader').textContent = p2Name; document.getElementById('p1PointsHeader').textContent = p1Name; document.getElementById('p2PointsHeader').textContent = p2Name;
    
    document.getElementById('winner1').checked = (p1Id === winnerId);
    document.getElementById('winner2').checked = (p2Id === winnerId);"""

if target in content:
    content = content.replace(target, replacement)
    with open('app/templates/category/view.html', 'w') as f:
        f.write(content)
    print("Patched radio buttons successfully.")
else:
    print("Target not found for radio buttons.")
