
with open('app/routes/tournament.py', 'r') as f:
    content = f.read()

target = """@tournament_bp.route('/tournaments/<slug>/register', methods=['GET', 'POST'])
@login_required
def register_for_tournament(slug):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    if tournament.status != 'registration':
        flash('Registration is currently closed for this tournament.', 'warning')
        return redirect(url_for('tournament.view_tournament', slug=slug))
        
    categories = Category.query.filter_by(tournament_id=tournament.id).all()
    
    # Check if user has a profile
    current_u = get_current_user()
    player = Player.query.filter_by(user_id=current_u.id).first()
    if not player:
        flash('You must create your Player Profile before registering for a tournament.', 'error')
        return redirect(url_for('player.dashboard'))
    
    if request.method == 'POST':
        category_id = request.form.get('category_id', type=int)
        
        category = Category.query.get_or_404(category_id)
        
        is_doubles = "Doubles" in category.name
        partner_name = request.form.get('partner_name', '').strip() if is_doubles else None
        partner_mobile = request.form.get('partner_mobile', '').strip() if is_doubles else None
        
        if is_doubles and not partner_name:
            flash('Partner name is required for Doubles categories.', 'error')
            return redirect(url_for('tournament.register_for_tournament', slug=slug))
        
        # Check if already registered
        existing = Registration.query.filter_by(
            tournament_id=tournament.id, 
            category_id=category_id, 
            player_id=player.id
        ).first()
        
        if existing:
            flash('You are already registered for this category.', 'warning')
            return redirect(url_for('tournament.view_tournament', slug=slug))
            
        # Create Registration
        reg = Registration(
            tournament_id=tournament.id,
            category_id=category_id,
            user_id=current_u.id,
            player_id=player.id,
            partner_name=partner_name,
            partner_mobile=partner_mobile,
            status='approved' # Auto-approve for now
        )
        db.session.add(reg)
        
        # Create Participant instantly
        p = Participant(
            tournament_id=tournament.id,
            category_id=category_id,
            player_id=player.id,
            name=player.name,
            email=current_u.email,
            partner_name=partner_name,
            partner_mobile=partner_mobile
        )
        db.session.add(p)
        db.session.commit()
        
        flash('Registration successful! You are now officially enrolled in the tournament.', 'success')
        return redirect(url_for('tournament.view_tournament', slug=slug))
        
    return render_template('tournament/register.html', tournament=tournament, categories=categories, player=player)"""

replace = """@tournament_bp.route('/tournaments/<slug>/register', methods=['GET', 'POST'])
def register_for_tournament(slug):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    if tournament.status != 'registration':
        flash('Registration is currently closed for this tournament.', 'warning')
        return redirect(url_for('tournament.view_tournament', slug=slug))
        
    categories = Category.query.filter_by(tournament_id=tournament.id).all()
    
    current_u = get_current_user()
    player = None
    if current_u:
        player = Player.query.filter_by(user_id=current_u.id).first()
        if not player:
            flash('You must create your Player Profile before registering for a tournament.', 'error')
            return redirect(url_for('player.dashboard'))
    
    if request.method == 'POST':
        category_id = request.form.get('category_id', type=int)
        category = Category.query.get_or_404(category_id)
        is_doubles = "Doubles" in category.name
        
        partner_name = request.form.get('partner_name', '').strip() if is_doubles else None
        partner_mobile = request.form.get('partner_mobile', '').strip() if is_doubles else None
        
        if is_doubles and not partner_name:
            flash('Partner name is required for Doubles categories.', 'error')
            return redirect(url_for('tournament.register_for_tournament', slug=slug))
            
        # Process participant details based on login status
        from datetime import datetime
        
        if player:
            # Logged in User
            participant_name = player.name
            participant_email = current_u.email
            participant_mobile = player.mobile if hasattr(player, 'mobile') else None
            participant_gender = player.gender
            participant_dob = player.dob
            
            # Check if already registered
            existing = Registration.query.filter_by(
                tournament_id=tournament.id, 
                category_id=category_id, 
                player_id=player.id
            ).first()
            if existing:
                flash('You are already registered for this category.', 'warning')
                return redirect(url_for('tournament.view_tournament', slug=slug))
                
            reg = Registration(
                tournament_id=tournament.id, category_id=category_id,
                user_id=current_u.id, player_id=player.id,
                partner_name=partner_name, partner_mobile=partner_mobile,
                status='approved'
            )
            db.session.add(reg)
            
        else:
            # Guest User
            participant_name = request.form.get('guest_name', '').strip()
            participant_mobile = request.form.get('guest_mobile', '').strip()
            participant_gender = request.form.get('guest_gender', '').strip()
            participant_dob_str = request.form.get('guest_dob', '').strip()
            
            if not participant_name or not participant_mobile or not participant_gender or not participant_dob_str:
                flash('All guest information is required.', 'error')
                return redirect(url_for('tournament.register_for_tournament', slug=slug))
                
            try:
                participant_dob = datetime.strptime(participant_dob_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format for Date of Birth.', 'error')
                return redirect(url_for('tournament.register_for_tournament', slug=slug))
                
            participant_email = None # Email removed for guests, using mobile instead
            
            # Can't reliably check if guest is already registered without player_id, but could check by name/mobile
            existing = Participant.query.filter_by(
                tournament_id=tournament.id, category_id=category_id, name=participant_name, mobile=participant_mobile
            ).first()
            if existing:
                flash('A guest with this name and mobile number is already registered for this category.', 'warning')
                return redirect(url_for('tournament.view_tournament', slug=slug))
                
            reg = Registration(
                tournament_id=tournament.id, category_id=category_id,
                user_id=None, player_id=None,
                partner_name=partner_name, partner_mobile=partner_mobile,
                status='approved'
            )
            db.session.add(reg)
            
        # Create Participant instantly for both
        p = Participant(
            tournament_id=tournament.id, category_id=category_id,
            player_id=player.id if player else None,
            name=participant_name, email=participant_email, mobile=participant_mobile,
            gender=participant_gender, dob=participant_dob,
            partner_name=partner_name, partner_mobile=partner_mobile
        )
        db.session.add(p)
        db.session.commit()
        
        flash('Registration successful! You are now officially enrolled in the tournament.', 'success')
        return redirect(url_for('tournament.view_tournament', slug=slug))
        
    return render_template('tournament/register.html', tournament=tournament, categories=categories, player=player)"""

if target in content:
    content = content.replace(target, replace)
    with open('app/routes/tournament.py', 'w') as f:
        f.write(content)
    print("tournament.py updated for guests.")
else:
    print("Target not found.")
