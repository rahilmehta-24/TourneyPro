
with open('app/static/css/style.css', 'r') as f:
    content = f.read()

target = """.card {
    background-color: var(--bg-card);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    border: 1px solid rgba(255, 255, 255, 0.05);
}"""

replace = """.card {
    background-color: var(--bg-card);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
    transition: transform 0.3s ease, box-shadow 0.3s ease, background-color 0.3s ease, border-color 0.3s ease;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

[data-theme="light"] .card {
    border: 1px solid rgba(0, 0, 0, 0.05);
}"""

if target in content:
    content = content.replace(target, replace)
    with open('app/static/css/style.css', 'w') as f:
        f.write(content)
    print("style.css card patched.")
else:
    print("Target not found.")
