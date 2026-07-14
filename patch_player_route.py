
with open('app/routes/player.py', 'r') as f:
    content = f.read()

target = """        def populate_player_from_request(p):
            p.name = request.form.get('name', p.name)
            p.gender = request.form.get('gender', p.gender)
            p.age_category = request.form.get('age_category', p.age_category)
            p.registration_no = request.form.get('registration_no')
            p.dob = parse_date(request.form.get('dob'))
            p.email = request.form.get('email')
            p.contact_number = request.form.get('contact_number')
            p.height = request.form.get('height')
            p.weight = request.form.get('weight')
            p.blood_group = request.form.get('blood_group')
            p.nationality = request.form.get('nationality')
            p.address = request.form.get('address')
            p.coach = request.form.get('coach')
            p.academy = request.form.get('academy')
            p.registration_details = request.form.get('registration_details')
            p.registration_date = parse_date(request.form.get('registration_date'))
            p.registration_validity = parse_date(request.form.get('registration_validity'))
            p.current_status = request.form.get('current_status', 'Active')
            p.avatar_url = request.form.get('avatar_url')
            p.bio = request.form.get('bio')
            
        action = request.form.get('action')
        
        if action == 'create_profile':
            new_player = Player(
                user_id=current_user.id,
                name=request.form.get('name', 'New Player'),
                gender=request.form.get('gender', 'Boys'),
                age_category=request.form.get('age_category', 'Open')
            )
            populate_player_from_request(new_player)
            db.session.add(new_player)
            db.session.commit()
            flash('Player Profile created successfully!', 'success')
            return redirect(url_for('player.dashboard'))
            
        elif action == 'update_profile':
            player_id = request.form.get('player_id', type=int)
            player = Player.query.filter_by(id=player_id, user_id=current_user.id).first_or_404()
            populate_player_from_request(player)
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('player.dashboard'))"""

replace = """        def populate_player_from_request(p):
            p.name = request.form.get('name', p.name)
            p.gender = request.form.get('gender', p.gender)
            p.age_category = request.form.get('age_category', p.age_category)
            p.dob = parse_date(request.form.get('dob'))
            p.email = request.form.get('email', p.email)
            p.contact_number = request.form.get('contact_number', p.contact_number)
            p.height = request.form.get('height', p.height)
            p.weight = request.form.get('weight', p.weight)
            p.blood_group = request.form.get('blood_group', p.blood_group)
            p.nationality = request.form.get('nationality', p.nationality)
            p.address = request.form.get('address', p.address)
            p.coach = request.form.get('coach', p.coach)
            p.academy = request.form.get('academy', p.academy)
            
        action = request.form.get('action')
        
        if action == 'update_profile':
            player_id = request.form.get('player_id', type=int)
            player = Player.query.filter_by(id=player_id, user_id=current_user.id).first_or_404()
            populate_player_from_request(player)
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('player.dashboard'))"""

if target in content:
    content = content.replace(target, replace)
    with open('app/routes/player.py', 'w') as f:
        f.write(content)
    print("player.py updated.")
else:
    print("Target not found.")
