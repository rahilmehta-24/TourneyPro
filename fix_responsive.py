
# 1. Fix app/templates/category/view.html
with open('app/templates/category/view.html', 'r') as f:
    cat_html = f.read()

# Replace <table class="standings-table"> with <div class="table-container"><table class="standings-table">
cat_html = cat_html.replace('<table class="standings-table">', '<div class="table-container" style="width: 100%; overflow-x: auto;">\n            <table class="standings-table">')
# Close the div after the table
cat_html = cat_html.replace('</table>', '</table>\n            </div>')

with open('app/templates/category/view.html', 'w') as f:
    f.write(cat_html)


# 2. Fix app/templates/tournament/view.html
with open('app/templates/tournament/view.html', 'r') as f:
    tour_html = f.read()

# Fix flex headers that lack flex-wrap
tour_html = tour_html.replace(
    'style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;"',
    'style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.5rem;"'
)

with open('app/templates/tournament/view.html', 'w') as f:
    f.write(tour_html)

