
with open('app/templates/base.html', 'r') as f:
    content = f.read()

# 1. Add the init script to <head>
target_head = """    <title>{% block title %}Tournament Platform{% endblock %}</title>"""
replace_head = """    <title>{% block title %}Tournament Platform{% endblock %}</title>
    <script>
        // Check for saved theme preference, otherwise use system preference
        const savedTheme = localStorage.getItem('tourneypro-theme');
        if (savedTheme === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
        } else if (!savedTheme && window.matchMedia('(prefers-color-scheme: light)').matches) {
            document.documentElement.setAttribute('data-theme', 'light');
        }
    </script>"""

if target_head in content:
    content = content.replace(target_head, replace_head)

# 2. Add the toggle button to nav-user-actions
target_nav = """            <!-- User Actions (Right) -->
            <div class="nav-user-actions" id="navUserActions">"""
replace_nav = """            <!-- User Actions (Right) -->
            <div class="nav-user-actions" id="navUserActions">
                <button id="themeToggleBtn" class="btn btn-outline btn-small" style="padding: 0.5rem; border-radius: 50%; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; margin-right: 0.5rem;" title="Toggle Light/Dark Mode">
                    <span id="themeIcon" style="font-size: 1.1rem;">☀️</span>
                </button>"""

if target_nav in content:
    content = content.replace(target_nav, replace_nav)

# 3. Add the toggle logic before </body>
target_body = """    </body>
</html>"""
replace_body = """        <script>
            document.addEventListener('turbo:load', setupThemeToggle);
            document.addEventListener('DOMContentLoaded', setupThemeToggle);
            
            function setupThemeToggle() {
                const themeBtn = document.getElementById('themeToggleBtn');
                const themeIcon = document.getElementById('themeIcon');
                
                if (!themeBtn) return;
                
                // Set initial icon
                if (document.documentElement.getAttribute('data-theme') === 'light') {
                    themeIcon.textContent = '🌙';
                } else {
                    themeIcon.textContent = '☀️';
                }
                
                // Only attach once
                if (themeBtn.dataset.listenerAttached) return;
                themeBtn.dataset.listenerAttached = 'true';
                
                themeBtn.addEventListener('click', () => {
                    const currentTheme = document.documentElement.getAttribute('data-theme');
                    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
                    
                    document.documentElement.setAttribute('data-theme', newTheme);
                    localStorage.setItem('tourneypro-theme', newTheme);
                    
                    if (newTheme === 'light') {
                        themeIcon.textContent = '🌙';
                    } else {
                        themeIcon.textContent = '☀️';
                    }
                });
            }
        </script>
    </body>
</html>"""

if target_body in content:
    content = content.replace(target_body, replace_body)

with open('app/templates/base.html', 'w') as f:
    f.write(content)
print("base.html patched with theme logic.")
