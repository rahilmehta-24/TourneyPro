
with open('app/templates/player/dashboard.html', 'r') as f:
    content = f.read()

target = """                            <div class="form-group">
                                <label class="form-label">Academy Name</label>
                                <input type="text" name="academy" class="form-input" value="{{ player.academy or '' }}">
                            </div>
                        </div>"""

replace = """                            <div class="form-group">
                                <label class="form-label">Academy Name</label>
                                <input type="text" name="academy" class="form-input" value="{{ player.academy or '' }}">
                            </div>
                            <div class="form-group" style="grid-column: 1 / -1;">
                                <label class="form-label">Profile Photo</label>
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    {% if player.avatar_url %}
                                        <img src="{{ player.avatar_url }}" alt="Profile Photo" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;">
                                    {% endif %}
                                    <input type="file" name="profile_photo" class="form-input" accept="image/*">
                                </div>
                            </div>
                        </div>"""

if target in content:
    content = content.replace(target, replace)
    with open('app/templates/player/dashboard.html', 'w') as f:
        f.write(content)
    print("dashboard.html patched.")
else:
    print("Target not found.")
