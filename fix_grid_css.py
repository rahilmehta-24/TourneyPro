with open('app/templates/category/view.html', 'r') as f:
    content = f.read()

# Add styles for the grid
grid_css = """
<style>
    .round-robin-grid {
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 2rem;
    }
    .round-robin-grid th, .round-robin-grid td {
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 10px;
        text-align: center;
    }
    .round-robin-grid th {
        background-color: rgba(255, 255, 255, 0.05);
        font-weight: bold;
    }
    .round-robin-grid .empty-cell {
        background-color: rgba(0, 0, 0, 0.2);
    }
</style>
"""

if ".round-robin-grid {" not in content:
    content = content.replace("<style>", grid_css + "\n<style>")
    
# Add borders and remove inline padding from my injected table
content = content.replace('style="background: rgba(255,255,255,0.05);">-</td>', 'class="empty-cell"></td>')

with open('app/templates/category/view.html', 'w') as f:
    f.write(content)
