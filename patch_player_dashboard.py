
with open('app/routes/player.py', 'r') as f:
    content = f.read()

target = """    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create_profile':
            name = request.form.get('name')
            gender = request.form.get('gender')
            age_category = request.form.get('age_category')
            dob_str = request.form.get('dob')
            registration_no = request.form.get('registration_no')
            
            dob = None
            if dob_str:
                try:
                    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            new_player = Player(
                user_id=current_user.id,
                name=name,
                gender=gender,
                age_category=age_category,
                dob=dob,
                registration_no=registration_no,
                current_status='Active'
            )
            db.session.add(new_player)
            db.session.commit()
            flash('Player profile created successfully!', 'success')
            
        elif action == 'update_profile':"""

replace = """    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':"""

if target in content:
    content = content.replace(target, replace)
    
    # Also update the update_profile parsing logic
    target2 = """            # Basic fields
            player.name = request.form.get('name', player.name)
            player.gender = request.form.get('gender', player.gender)
            player.age_category = request.form.get('age_category', player.age_category)
            player.registration_no = request.form.get('registration_no', player.registration_no)"""
            
    replace2 = """            # Basic fields
            player.name = request.form.get('name', player.name)
            player.gender = request.form.get('gender', player.gender)
            player.age_category = request.form.get('age_category', player.age_category)
            
            # New fields
            player.email = request.form.get('email', player.email)
            player.contact_number = request.form.get('contact_number', player.contact_number)
            player.blood_group = request.form.get('blood_group', player.blood_group)
            player.height = request.form.get('height', player.height)
            player.weight = request.form.get('weight', player.weight)
            player.nationality = request.form.get('nationality', player.nationality)
            player.coach = request.form.get('coach', player.coach)
            player.academy = request.form.get('academy', player.academy)
            player.address = request.form.get('address', player.address)"""
            
    content = content.replace(target2, replace2)
    
    with open('app/routes/player.py', 'w') as f:
        f.write(content)
    print("player.py patched.")
else:
    print("Target not found.")
