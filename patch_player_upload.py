
with open('app/routes/player.py', 'r') as f:
    content = f.read()

target = """        if action == 'update_profile':
            player_id = request.form.get('player_id', type=int)
            player = Player.query.filter_by(id=player_id, user_id=current_user.id).first_or_404()
            populate_player_from_request(player)
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('player.dashboard'))"""

replace = """        if action == 'update_profile':
            import os
            from werkzeug.utils import secure_filename
            from flask import current_app
            
            player_id = request.form.get('player_id', type=int)
            player = Player.query.filter_by(id=player_id, user_id=current_user.id).first_or_404()
            populate_player_from_request(player)
            
            # Handle profile photo upload
            if 'profile_photo' in request.files:
                file = request.files['profile_photo']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    upload_dir = os.path.join('app', 'static', 'uploads')
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, f"{player.id}_{filename}")
                    file.save(file_path)
                    player.avatar_url = url_for('static', filename=f"uploads/{player.id}_{filename}")
                    
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('player.dashboard'))"""

if target in content:
    content = content.replace(target, replace)
    with open('app/routes/player.py', 'w') as f:
        f.write(content)
    print("player.py patched for upload.")
else:
    print("Target not found.")
