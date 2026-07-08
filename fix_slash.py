
def fix_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # Replace literal backslash-quote with just double quote for onclick=
    content = content.replace(r'onclick=\"openMatchModal', 'onclick="openMatchModal')
    
    # Replace literal backslash-quote at the end of the onclick attribute
    content = content.replace(r')\" title="Click', ')" title="Click')

    with open(filename, 'w') as f:
        f.write(content)

fix_file('app/templates/category/view.html')
fix_file('app/templates/tournament/view.html')
