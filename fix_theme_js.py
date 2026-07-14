with open('app/templates/base.html', 'r') as f:
    content = f.read()

script = """
        <script>
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
"""

if 'setupThemeToggle' not in content:
    content = content.replace('</body>', script + '</body>')
    with open('app/templates/base.html', 'w') as f:
        f.write(content)
    print("Fixed theme JS")
else:
    print("JS already exists")
