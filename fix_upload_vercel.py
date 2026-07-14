
with open('app/routes/player.py', 'r') as f:
    content = f.read()

target = """            # Handle profile photo upload
            if 'profile_photo' in request.files:
                file = request.files['profile_photo']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    upload_dir = os.path.join('app', 'static', 'uploads')
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, f"{player.id}_{filename}")
                    file.save(file_path)
                    player.avatar_url = url_for('static', filename=f"uploads/{player.id}_{filename}")"""

replace = """            # Handle profile photo (Vercel is read-only, so we accept a URL instead of a file)
            avatar_url = request.form.get('avatar_url')
            if avatar_url:
                player.avatar_url = avatar_url"""

if target in content:
    content = content.replace(target, replace)
    with open('app/routes/player.py', 'w') as f:
        f.write(content)
    print("player.py fixed for Vercel")
else:
    print("Target not found in player.py")

with open('app/templates/player/dashboard.html', 'r') as f:
    content = f.read()

target2 = """                            <div class="form-group" style="grid-column: 1 / -1;">
                                <label class="form-label">Profile Photo</label>
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    {% if player.avatar_url %}
                                        <img src="{{ player.avatar_url }}" alt="Profile Photo" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;">
                                    {% endif %}
                                    <input type="file" name="profile_photo" class="form-input" accept="image/*">
                                </div>
                            </div>"""

replace2 = """                            <div class="form-group" style="grid-column: 1 / -1;">
                                <label class="form-label">Profile Photo URL</label>
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    {% if player.avatar_url %}
                                        <img src="{{ player.avatar_url }}" alt="Profile Photo" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;">
                                    {% endif %}
                                    <input type="url" name="avatar_url" class="form-input" placeholder="https://example.com/your-image.jpg" value="{{ player.avatar_url or '' }}" style="flex: 1;">
                                </div>
                                <small style="color: var(--text-muted); margin-top: 0.5rem; display: block;">Since the platform is hosted on a read-only server (Vercel), please provide a direct link to an image (e.g. from Imgur or Google Photos).</small>
                            </div>"""

if target2 in content:
    content = content.replace(target2, replace2)
    # Also remove enctype
    content = content.replace('enctype="multipart/form-data"', '')
    with open('app/templates/player/dashboard.html', 'w') as f:
        f.write(content)
    print("dashboard.html fixed for Vercel")
else:
    print("Target not found in dashboard.html")
