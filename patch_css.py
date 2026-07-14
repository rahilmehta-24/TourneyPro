
with open('app/static/css/style.css', 'r') as f:
    content = f.read()

target = """    --radius-sm: 0.5rem;
    --radius-md: 0.75rem;
    --radius-lg: 1rem;

    /* Transitions */"""

replace = """    --radius-sm: 0.5rem;
    --radius-md: 0.75rem;
    --radius-lg: 1rem;
}

[data-theme="light"] {
    /* Color Palette - Light Theme */
    --bg-primary: #f8fafc;
    --bg-secondary: #f1f5f9;
    --bg-tertiary: #e2e8f0;
    --bg-card: #ffffff;

    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-muted: #64748b;

    --accent-primary: #ea580c; /* slightly darker orange for contrast */
    --accent-primary-hover: #c2410c;
    
    /* Shadows - softer for light mode */
    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
    --shadow-glow: 0 0 20px rgba(234, 88, 12, 0.2);
}

:root {
    /* Transitions */"""

if target in content:
    content = content.replace(target, replace)
    
    # Also add a smooth transition to body
    target2 = """body {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
    line-height: 1.6;
    min-height: 100vh;
    display: flex;
    flex-direction: column;"""
    
    replace2 = """body {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
    line-height: 1.6;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    transition: background-color 0.3s ease, color 0.3s ease;"""
    
    content = content.replace(target2, replace2)
    
    with open('app/static/css/style.css', 'w') as f:
        f.write(content)
    print("style.css patched.")
else:
    print("Target not found.")
