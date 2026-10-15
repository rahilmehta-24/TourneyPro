from app.services.utils.audit import log_audit
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.domain.models import (
    db, Tournament, Participant, Match, TournamentSettings, Registration, Category, Player, User,
    determine_age_category, estimate_dob_from_age, calculate_age_from_dob
)
from app.services.format_engine import get_format
from app.core.constants import TOURNAMENT_FORMATS
from app.web.controllers.auth import login_required, role_required, get_current_user, check_tournament_ownership
from app.services.tennis_logic import validate_and_format_score
from app.services.utils.validation import (
    validate_name, validate_mobile, validate_email, validate_age, validate_dob,
    validate_upi_id, validate_transaction_id, validate_tournament_dates,
    validate_operating_hours
)
import json
from slugify import slugify
from datetime import datetime, timedelta

tournament_bp = Blueprint('tournament', __name__)

@tournament_bp.route('/tournaments/new', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def create_tournament():
    """Create new tournament"""
    academy_id = request.args.get('academy_id')
    if request.method == 'POST':
        name = request.form.get('name')
        creator_name = request.form.get('creator_name', 'Anonymous')
        description = request.form.get('description', '')
        payment_upi_id = request.form.get('payment_upi_id', '').strip()
        game_info = request.form.get('game_info', '')
        academy_id = request.form.get('academy_id') or academy_id
        is_internal = request.form.get('is_internal') == 'on'

        ok, clean_name = validate_name(name, min_len=3, max_len=100, field_name="Tournament Name")
        if not ok:
            flash(clean_name, 'error')
            return render_template('tournament/create.html', academy_id=academy_id, formats=TOURNAMENT_FORMATS)
        name = clean_name

        if payment_upi_id:
            ok, clean_upi = validate_upi_id(payment_upi_id, required=False)
            if not ok:
                flash(clean_upi, 'error')
                return render_template('tournament/create.html', academy_id=academy_id, formats=TOURNAMENT_FORMATS)
            payment_upi_id = clean_upi

        # Set legacy values for backwards compatibility, but do not prompt for them
        format_type = None
        max_participants = None
        num_sets = 1
        games_per_set = 6

        # Generate URL slug
        url_slug = slugify(name)

        # Check if slug already exists
        existing = Tournament.query.filter_by(url_slug=url_slug).first()
        if existing:
            url_slug = f"{url_slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create tournament
        tournament = Tournament(
            user_id=get_current_user().id,
            creator_name=creator_name,
            name=name,
            url_slug=url_slug,
            description=description,
            game_info=game_info,
            format=format_type,
            max_participants=max_participants,
            num_sets=num_sets,
            games_per_set=games_per_set,
            has_categories=True,  # Force categories for all new tournaments
            academy_id=academy_id if academy_id else None,
            is_internal=is_internal,
            payment_upi_id=payment_upi_id if payment_upi_id else None
        )

        try:
            db.session.add(tournament)
            db.session.commit()

            # Create default settings
            settings = TournamentSettings(tournament_id=tournament.id)
            db.session.add(settings)
            db.session.commit()
            log_audit(
                action_type='CREATE_TOURNAMENT',
                target_id=tournament.id,
                target_name=tournament.name,
                reason='Created new tournament',
                details={'creator_name': creator_name, 'academy_id': academy_id}
            )

            flash('Tournament created successfully!', 'success')
            return redirect(url_for('tournament.manage_tournament', slug=tournament.url_slug))
        except Exception as e:
            db.session.rollback()
            flash('Error creating tournament. Please try again.', 'error')

    academy_id = request.args.get('academy_id')
    return render_template('tournament/create.html', academy_id=academy_id, formats=TOURNAMENT_FORMATS)

@tournament_bp.route('/t/<slug>')
@tournament_bp.route('/tournaments/<slug>')
def view_tournament(slug):
    """View tournament hub (brackets, schedule, organizer dashboard)"""
    tournament = Tournament.query.options(
        db.joinedload(Tournament.categories).joinedload(Category.participants)
    ).filter_by(url_slug=slug).first_or_404()
    
    # If tournament is in registration phase, visiting/clicking the shared link opens the Registration page
    if tournament.status == 'registration' and request.args.get('view') not in ['bracket', 'manage']:
        return redirect(url_for('tournament.register_for_tournament', slug=slug))

    participants = Participant.query.filter_by(tournament_id=tournament.id).order_by(Participant.seed).all()
    matches = Match.query.options(
        db.joinedload(Match.participant1),
        db.joinedload(Match.participant2),
        db.joinedload(Match.winner),
        db.joinedload(Match.category)
    ).filter_by(tournament_id=tournament.id).order_by(Match.round, Match.match_number).all()

    # Group matches by round
    rounds = {}
    winners_rounds = {}
    losers_rounds = {}
    grand_finals = []
    for match in matches:
        if match.round not in rounds:
            rounds[match.round] = []
        rounds[match.round].append(match)

        # Double elimination separation
        if match.bracket_type == 'winners':
            if match.round not in winners_rounds:
                winners_rounds[match.round] = []
            winners_rounds[match.round].append(match)
        elif match.bracket_type == 'losers':
            if match.round not in losers_rounds:
                losers_rounds[match.round] = []
            losers_rounds[match.round].append(match)
        elif match.bracket_type in ['grand_finals', 'grand_final']:
            grand_finals.append(match)

    # Aggregate player registry data efficiently
    player_stats = {}
    if tournament.has_categories:
        # Pre-build stats dictionary from participants
        for category in tournament.categories:
            for participant in category.participants:
                if participant.name not in player_stats:
                    player_stats[participant.name] = {
                        'name': participant.name,
                        'categories': [],
                        'total_matches': 0,
                        'total_wins': 0,
                        'placements': []
                    }
                player_stats[participant.name]['categories'].append(category.name)

        # Iterate over pre-loaded matches once to count matches and wins
        for match in matches:
            if match.status == 'completed' and match.category_id:
                p1_name = match.participant1.name if match.participant1 else None
                p2_name = match.participant2.name if match.participant2 else None
                winner_name = match.winner.name if match.winner else None

                if p1_name and p1_name in player_stats:
                    player_stats[p1_name]['total_matches'] += 1
                if p2_name and p2_name in player_stats:
                    player_stats[p2_name]['total_matches'] += 1
                if winner_name and winner_name in player_stats:
                    player_stats[winner_name]['total_wins'] += 1

        # Calculate placements
        for category in tournament.categories:
            if category.status == 'completed':
                cat_matches = [m for m in matches if m.category_id == category.id and m.match_type != 'round_robin']
                if cat_matches:
                    max_round = max([m.round for m in cat_matches], default=0)
                    finals = [m for m in cat_matches if m.round == max_round]
                    semis = [m for m in cat_matches if m.round == max_round - 1] if max_round >= 2 else []

                    for participant in category.participants:
                        p_name = participant.name
                        if p_name in player_stats:
                            if finals and finals[0].winner_id == participant.id:
                                player_stats[p_name]['placements'].append(('Champion', category.name))
                            elif finals and participant.id in [finals[0].participant1_id, finals[0].participant2_id]:
                                player_stats[p_name]['placements'].append(('Runner-Up', category.name))
                            else:
                                for sm in semis:
                                    if participant.id in [sm.participant1_id, sm.participant2_id] and sm.winner_id != participant.id:
                                        player_stats[p_name]['placements'].append(('Semi-Finalist', category.name))
                                        break

    # Sort registry by wins
    player_registry = sorted(player_stats.values(), key=lambda x: x['total_wins'], reverse=True)

    # Sort placements for each player to find the "best" one
    placement_weights = {
        'Champion': 3,
        'Runner-Up': 2,
        'Semi-Finalist': 1
    }

    for player in player_registry:
        if player['placements']:
            player['placements'].sort(key=lambda x: placement_weights.get(x[0], 0), reverse=True)

    return render_template('tournament/view.html',
                         tournament=tournament,
                         participants=participants,
                         matches=matches,
                         rounds=rounds,
                         winners_rounds=winners_rounds,
                         losers_rounds=losers_rounds,
                         grand_finals=grand_finals,
                         player_registry=player_registry,
                         formats=TOURNAMENT_FORMATS)

@tournament_bp.route('/t/<slug>/print')
@tournament_bp.route('/tournaments/<slug>/print')
def print_tournament(slug):
    """Print tournament bracket and standings"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    return render_template('tournament/print.html', tournament=tournament)



@tournament_bp.route('/t/<slug>/register', methods=['GET', 'POST'])
@tournament_bp.route('/tournaments/<slug>/register', methods=['GET', 'POST'])
def register_for_tournament(slug):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    if tournament.status != 'registration':
        flash('Registration is currently closed for this tournament.', 'warning')
        return redirect(url_for('tournament.view_tournament', slug=slug))
        
    if tournament.registration_closes_at and datetime.utcnow() > tournament.registration_closes_at:
        if tournament.status == 'registration':
            tournament.status = 'in_progress'
            db.session.commit()
        flash('Registration deadline has passed for this tournament.', 'warning')
        return redirect(url_for('tournament.view_tournament', slug=slug))

    categories = Category.query.filter_by(tournament_id=tournament.id).all()
    
    current_u = get_current_user()
    player = None
    if current_u:
        player = Player.query.filter_by(user_id=current_u.id).first()
    
    if request.method == 'POST':
        category_ids = request.form.getlist('category_id', type=int)
        if not category_ids:
            flash('Please select at least one category.', 'error')
            return redirect(url_for('tournament.register_for_tournament', slug=slug))
            
        selected_categories = Category.query.filter(Category.id.in_(category_ids)).all()
        
        # Calculate total fee
        total_due = sum(
            (cat.entry_fee or 0.0) * 2 if ("Doubles" in cat.name or (cat.format and 'doubles' in cat.format)) else (cat.entry_fee or 0.0)
            for cat in selected_categories
        )
        transaction_id = request.form.get('transaction_id', '').strip()
        if total_due > 0 and tournament.payment_upi_id:
            ok, tx_res = validate_transaction_id(transaction_id, required=True)
            if not ok:
                flash(tx_res, 'error')
                return redirect(url_for('tournament.register_for_tournament', slug=slug))
            transaction_id = tx_res
        
        partners_data = {}
        for cat in selected_categories:
            if "Doubles" in cat.name or (cat.format and 'doubles' in cat.format):
                p_name = request.form.get(f'partner_name_{cat.id}', '').strip()
                p_age_str = request.form.get(f'partner_age_{cat.id}', '').strip()
                p_mobile = request.form.get(f'partner_mobile_{cat.id}', '').strip()
                p_email = request.form.get(f'partner_email_{cat.id}', '').strip()
                p_gender = request.form.get(f'partner_gender_{cat.id}', '').strip()
                
                if not p_gender:
                    if cat.gender in ['Mens', 'Boys', 'Male']:
                        p_gender = 'Male'
                    elif cat.gender in ['Womens', 'Girls', 'Female']:
                        p_gender = 'Female'
                    else:
                        p_gender = 'Male'

                ok, clean_p_name = validate_name(p_name, field_name=f"Partner Name for {cat.name}")
                if not ok:
                    flash(clean_p_name, 'error')
                    return redirect(url_for('tournament.register_for_tournament', slug=slug))

                ok, clean_p_age = validate_age(p_age_str, min_age=4, max_age=100, field_name=f"Partner Age for {cat.name}")
                if not ok:
                    flash(clean_p_age, 'error')
                    return redirect(url_for('tournament.register_for_tournament', slug=slug))

                ok, clean_p_mobile = validate_mobile(p_mobile, required=True, field_name=f"Partner Mobile for {cat.name}")
                if not ok:
                    flash(clean_p_mobile, 'error')
                    return redirect(url_for('tournament.register_for_tournament', slug=slug))

                if p_email:
                    ok, clean_p_email = validate_email(p_email, required=False, field_name=f"Partner Email for {cat.name}")
                    if not ok:
                        flash(clean_p_email, 'error')
                        return redirect(url_for('tournament.register_for_tournament', slug=slug))
                    p_email = clean_p_email

                partners_data[cat.id] = {
                    'name': clean_p_name,
                    'age': clean_p_age,
                    'mobile': clean_p_mobile,
                    'email': p_email or None,
                    'gender': p_gender
                }

        participant_name = request.form.get('guest_name', '').strip()
        participant_age_str = request.form.get('guest_age', '').strip()
        participant_mobile = request.form.get('guest_mobile', '').strip()
        participant_email = request.form.get('guest_email', '').strip()
        participant_gender = request.form.get('guest_gender', '').strip()
        participant_dob_str = request.form.get('guest_dob', '').strip()

        # If user is logged in with profile, auto-fill
        if player:
            participant_name = participant_name or player.name
            participant_email = participant_email or player.email or (current_u.email if current_u else None)
            participant_mobile = participant_mobile or player.contact_number
            participant_gender = participant_gender or player.gender
            participant_dob = player.dob
            participant_age = player.age
        else:
            ok, clean_p_name = validate_name(participant_name, field_name="Full Name")
            if not ok:
                flash(clean_p_name, 'error')
                return redirect(url_for('tournament.register_for_tournament', slug=slug))
            participant_name = clean_p_name

            ok, clean_p_mobile = validate_mobile(participant_mobile, required=True, field_name="Mobile Number")
            if not ok:
                flash(clean_p_mobile, 'error')
                return redirect(url_for('tournament.register_for_tournament', slug=slug))
            participant_mobile = clean_p_mobile

            if participant_email:
                ok, clean_p_email = validate_email(participant_email, required=False, field_name="Email Address")
                if not ok:
                    flash(clean_p_email, 'error')
                    return redirect(url_for('tournament.register_for_tournament', slug=slug))
                participant_email = clean_p_email

            if not participant_gender:
                flash('Gender is required.', 'error')
                return redirect(url_for('tournament.register_for_tournament', slug=slug))

            participant_dob = None
            participant_age = None
            if participant_dob_str:
                ok, clean_dob = validate_dob(participant_dob_str, field_name="Date of Birth")
                if not ok:
                    flash(clean_dob, 'error')
                    return redirect(url_for('tournament.register_for_tournament', slug=slug))
                participant_dob = clean_dob
                participant_age = calculate_age_from_dob(participant_dob)
            elif participant_age_str:
                ok, clean_age = validate_age(participant_age_str, field_name="Age")
                if not ok:
                    flash(clean_age, 'error')
                    return redirect(url_for('tournament.register_for_tournament', slug=slug))
                participant_age = clean_age
                participant_dob = estimate_dob_from_age(participant_age)
            else:
                flash('Age or Date of Birth is required.', 'error')
                return redirect(url_for('tournament.register_for_tournament', slug=slug))

        # 1. SMART REGISTRATION: Ensure we have an anonymous dummy user for Registration.user_id 
        anon_email = 'anonymous@tourneypro.com'
        anon_user = User.query.filter_by(email=anon_email).first()
        if not anon_user:
            anon_user = User(username='anonymous_registrations', email=anon_email, role='user')
            anon_user.set_password('random_unused_password_1234')
            db.session.add(anon_user)
            db.session.flush()
            
        current_u_id = current_u.id if current_u else anon_user.id
            
        # 2. AUTO PROFILE CREATION: Create or link Player profile
        if player:
            new_player = player
            if participant_mobile and not new_player.contact_number:
                new_player.contact_number = participant_mobile
            if participant_email and not new_player.email:
                new_player.email = participant_email
            if participant_dob and not new_player.dob:
                new_player.dob = participant_dob
        else:
            existing_player = None
            if current_u:
                existing_player = Player.query.filter_by(user_id=current_u.id).first()
            if not existing_player and participant_mobile:
                existing_player = Player.query.filter(Player.contact_number == participant_mobile).first()
            if not existing_player and participant_name and participant_mobile:
                existing_player = Player.query.filter(Player.name == participant_name, Player.contact_number == participant_mobile).first()

            if existing_player:
                new_player = existing_player
                if current_u and not new_player.user_id:
                    new_player.user_id = current_u.id
                if participant_email and not new_player.email:
                    new_player.email = participant_email
                if participant_dob and not new_player.dob:
                    new_player.dob = participant_dob
            else:
                age_cat = determine_age_category(age=participant_age, dob=participant_dob)
                new_player = Player(
                    user_id=current_u.id if current_u else None,
                    name=participant_name,
                    email=participant_email or None,
                    contact_number=participant_mobile,
                    gender=participant_gender,
                    dob=participant_dob,
                    age_category=age_cat
                )
                db.session.add(new_player)
                db.session.flush()

        # 3. AUTO PROFILE CREATION FOR DOUBLES PARTNERS
        partner_players = {}
        for cat_id, p_info in partners_data.items():
            p_name = p_info['name']
            p_age = p_info['age']
            p_mobile = p_info['mobile']
            p_email = p_info.get('email')
            p_gender = p_info.get('gender') or 'Male'
            p_dob = estimate_dob_from_age(p_age)
            p_cat = determine_age_category(age=p_age, dob=p_dob)

            # Check if partner already exists
            p_player = Player.query.filter(Player.contact_number == p_mobile).first()
            if not p_player:
                p_player = Player.query.filter(Player.name == p_name, Player.contact_number == p_mobile).first()

            if not p_player:
                p_player = Player(
                    user_id=None,
                    name=p_name,
                    email=p_email or None,
                    contact_number=p_mobile,
                    gender=p_gender,
                    dob=p_dob,
                    age_category=p_cat
                )
                db.session.add(p_player)
                db.session.flush()
            else:
                if p_email and not p_player.email:
                    p_player.email = p_email

            partner_players[cat_id] = p_player

        # Create Registrations and Participants for each category
        for cat in selected_categories:
            p2_obj = partner_players.get(cat.id)
            p2_id = p2_obj.id if p2_obj else None
            cat_partner_name = p2_obj.name if p2_obj else partners_data.get(cat.id, {}).get('name')
            cat_partner_mobile = p2_obj.contact_number if p2_obj else partners_data.get(cat.id, {}).get('mobile')
            
            cat_fee = cat.entry_fee or 0.0
            amount_due = cat_fee * 2 if ("Doubles" in cat.name or (cat.format and 'doubles' in cat.format)) else cat_fee
            
            reg_status = 'pending' if amount_due > 0 else 'approved'
            
            reg = Registration(
                tournament_id=tournament.id, category_id=cat.id,
                user_id=current_u_id, player_id=new_player.id, player2_id=p2_id,
                partner_name=cat_partner_name, partner_mobile=cat_partner_mobile,
                status=reg_status,
                amount_due=amount_due,
                transaction_id=transaction_id if amount_due > 0 else None,
                payment_status='pending' if amount_due > 0 else 'paid'
            )
            db.session.add(reg)
            
            if reg_status == 'approved':
                display_name = f"{participant_name} / {cat_partner_name}" if cat_partner_name else participant_name
                p = Participant(
                    tournament_id=tournament.id, category_id=cat.id,
                    player_id=new_player.id, player2_id=p2_id,
                    name=display_name, email=participant_email or '', mobile=participant_mobile,
                    gender=participant_gender, dob=participant_dob,
                    partner_name=cat_partner_name, partner_mobile=cat_partner_mobile
                )
                db.session.add(p)
            
        db.session.commit()
        
        flash('Registration successful! You are now officially enrolled in the tournament.', 'success')
        return redirect(url_for('tournament.view_tournament', slug=slug))
        
    return render_template('tournament/register.html', tournament=tournament, categories=categories, player=player)

@tournament_bp.route('/t/<slug>/manage', methods=['GET', 'POST'])
@tournament_bp.route('/tournaments/<slug>/manage', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def manage_tournament(slug):
    """Manage tournament (add participants, start tournament)"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    
    participants = Participant.query.filter_by(tournament_id=tournament.id).order_by(Participant.seed).all()

    if request.method == 'POST':
        action = request.form.get('action')

        try:
            if action == 'approve_registration':
                reg_id = request.form.get('registration_id', type=int)
                reg = Registration.query.get(reg_id)
                if reg:
                    reg.status = 'approved'
                    # Create Participant
                    participant = Participant(
                        tournament_id=tournament.id,
                        category_id=reg.category_id,
                        name=f"{reg.player.name}{' / ' + reg.partner_name if reg.partner_name else ''}",
                        player_id=reg.player_id,
                        player2_id=reg.player2_id,
                        partner_name=reg.partner_name,
                        partner_mobile=reg.partner_mobile
                    )
                    db.session.add(participant)
                    db.session.commit()
                    flash(f"Registration for {participant.name} approved.", 'success')
                return redirect(url_for('tournament.manage_tournament', slug=slug))
                
            elif action == 'reject_registration':
                reg_id = request.form.get('registration_id', type=int)
                reg = Registration.query.get(reg_id)
                if reg:
                    reg.status = 'rejected'
                    db.session.commit()
                    flash("Registration rejected.", 'warning')
                return redirect(url_for('tournament.manage_tournament', slug=slug))
                
            elif action == 'add_participant':
                participant_name = request.form.get('participant_name', '').strip()
                participant_age_str = request.form.get('participant_age', '').strip()
                participant_mobile = request.form.get('participant_mobile', '').strip()
                participant_email = request.form.get('participant_email', '').strip()
                participant_gender = request.form.get('participant_gender', 'Male').strip()
                category_id = request.form.get('category_id', type=int)
                manual_seed = request.form.get('manual_seed', type=int)

                partner_name = request.form.get('partner_name', '').strip()
                partner_age_str = request.form.get('partner_age', '').strip()
                partner_mobile = request.form.get('partner_mobile', '').strip()
                partner_email = request.form.get('partner_email', '').strip()
                partner_gender = request.form.get('partner_gender', '').strip()

                if not participant_name:
                    flash('Participant name is required.', 'error')
                    return redirect(url_for('tournament.manage_tournament', slug=slug))

                if manual_seed is not None and manual_seed < 1:
                    flash('Seed must be a positive integer (1 or greater).', 'error')
                    return redirect(url_for('tournament.manage_tournament', slug=slug))

                if participant_mobile:
                    ok, clean_mob = validate_mobile(participant_mobile, required=False)
                    if not ok:
                        flash(clean_mob, 'error')
                        return redirect(url_for('tournament.manage_tournament', slug=slug))
                    participant_mobile = clean_mob

                if participant_email:
                    ok, clean_em = validate_email(participant_email, required=False)
                    if not ok:
                        flash(clean_em, 'error')
                        return redirect(url_for('tournament.manage_tournament', slug=slug))
                    participant_email = clean_em

                if participant_age_str:
                    ok, clean_age = validate_age(participant_age_str, required=False)
                    if not ok:
                        flash(clean_age, 'error')
                        return redirect(url_for('tournament.manage_tournament', slug=slug))

                if partner_name:
                    ok, clean_pname = validate_name(partner_name, field_name="Partner Name")
                    if not ok:
                        flash(clean_pname, 'error')
                        return redirect(url_for('tournament.manage_tournament', slug=slug))
                    partner_name = clean_pname

                    if partner_mobile:
                        ok, clean_pmob = validate_mobile(partner_mobile, required=False, field_name="Partner Mobile")
                        if not ok:
                            flash(clean_pmob, 'error')
                            return redirect(url_for('tournament.manage_tournament', slug=slug))
                        partner_mobile = clean_pmob

                    if partner_email:
                        ok, clean_pem = validate_email(partner_email, required=False, field_name="Partner Email")
                        if not ok:
                            flash(clean_pem, 'error')
                            return redirect(url_for('tournament.manage_tournament', slug=slug))
                        partner_email = clean_pem

                    if partner_age_str:
                        ok, clean_page = validate_age(partner_age_str, required=False, field_name="Partner Age")
                        if not ok:
                            flash(clean_page, 'error')
                            return redirect(url_for('tournament.manage_tournament', slug=slug))

                target_category = Category.query.get(category_id) if category_id else None
                if target_category and not participant_gender:
                    participant_gender = target_category.gender

                # Handle comma-separated names
                names = [n.strip() for n in participant_name.split(',') if n.strip()]
                for n in names:
                    ok, clean_n = validate_name(n, field_name="Participant Name")
                    if not ok:
                        flash(clean_n, 'error')
                        return redirect(url_for('tournament.manage_tournament', slug=slug))

                added_names = []

                for name in names:
                    p1_name = name
                    p2_name = partner_name
                    p1_age_str = participant_age_str
                    p2_age_str = partner_age_str
                    p1_mobile = participant_mobile
                    p2_mobile = partner_mobile

                    # If slash in name: e.g. "P1 / P2"
                    if '/' in name and not p2_name:
                        parts = [p.strip() for p in name.split('/', 1)]
                        p1_name = parts[0]
                        p2_name = parts[1]

                    # Auto-create or fetch Player 1
                    p1_player = None
                    if p1_mobile:
                        p1_player = Player.query.filter(Player.contact_number == p1_mobile).first()
                    if not p1_player:
                        p1_player = Player.query.filter_by(name=p1_name).first()

                    p1_age = None
                    if p1_age_str:
                        try:
                            p1_age = int(p1_age_str)
                        except ValueError:
                            pass
                    p1_dob = estimate_dob_from_age(p1_age)
                    p1_cat = determine_age_category(age=p1_age, dob=p1_dob)

                    if not p1_player:
                        p1_player = Player(
                            name=p1_name,
                            contact_number=p1_mobile or None,
                            email=participant_email if len(names) == 1 else None,
                            gender=participant_gender or 'Male',
                            dob=p1_dob,
                            age_category=p1_cat
                        )
                        db.session.add(p1_player)
                        db.session.flush()
                    else:
                        if p1_mobile and not p1_player.contact_number:
                            p1_player.contact_number = p1_mobile
                        if participant_email and len(names) == 1 and not p1_player.email:
                            p1_player.email = participant_email

                    p2_player = None
                    if p2_name:
                        p2_age = None
                        if p2_age_str:
                            try:
                                p2_age = int(p2_age_str)
                            except ValueError:
                                pass
                        p2_dob = estimate_dob_from_age(p2_age)
                        p2_cat = determine_age_category(age=p2_age, dob=p2_dob)

                        if p2_mobile:
                            p2_player = Player.query.filter(Player.contact_number == p2_mobile).first()
                        if not p2_player:
                            p2_player = Player.query.filter_by(name=p2_name).first()

                        if not p2_player:
                            p2_player = Player(
                                name=p2_name,
                                contact_number=p2_mobile or None,
                                email=partner_email or None,
                                gender=partner_gender or participant_gender or 'Male',
                                dob=p2_dob,
                                age_category=p2_cat
                            )
                            db.session.add(p2_player)
                            db.session.flush()

                    display_name = f"{p1_name} / {p2_name}" if p2_name else p1_name
                    participant = Participant(
                        tournament_id=tournament.id,
                        category_id=category_id,
                        player_id=p1_player.id,
                        player2_id=p2_player.id if p2_player else None,
                        name=display_name,
                        email=participant_email if len(names) == 1 else '',
                        mobile=p1_mobile if len(names) == 1 else '',
                        gender=participant_gender,
                        dob=p1_dob,
                        partner_name=p2_name if p2_name else None,
                        partner_mobile=p2_mobile if p2_mobile else None,
                        manual_seed=manual_seed if len(names) == 1 else None
                    )
                    db.session.add(participant)
                    added_names.append(display_name)

                db.session.commit()

                flash(f'Added participant(s): {", ".join(added_names)}', 'success')
                return redirect(url_for('tournament.manage_tournament', slug=slug))

            elif action == 'delete_participant':
                participant_id = request.form.get('participant_id', type=int)
                participant = Participant.query.get(participant_id)
                if participant:
                    reason = request.form.get('audit_reason')
                    explanation = request.form.get('audit_explanation', '')
                    if not reason:
                        flash("Audit validation failed: Reason required to delete a participant.", "error")
                        return redirect(url_for('tournament.manage_tournament', slug=slug))
                        
                    log_audit(
                        action_type='delete_participant',
                        target_id=participant.id,
                        target_name=participant.name,
                        reason=reason,
                        explanation=explanation
                    )
                    db.session.delete(participant)
                    db.session.commit()
                    flash(f'Removed participant: {participant.name}', 'info')
                return redirect(url_for('tournament.manage_tournament', slug=slug))

            elif action == 'open_registration':
                tournament.status = 'registration'
                
                reg_closes_str = request.form.get('registration_closes_at')
                if reg_closes_str:
                    try:
                        local_dt = datetime.strptime(reg_closes_str, '%Y-%m-%dT%H:%M')
                        tz_offset = request.form.get('tz_offset', type=int)
                        if tz_offset is not None:
                            utc_dt = local_dt + timedelta(minutes=tz_offset)
                        else:
                            utc_dt = local_dt
                        tournament.registration_closes_at = utc_dt
                    except ValueError:
                        pass
                
                db.session.commit()
                flash('Tournament registration is now open!', 'success')
                return redirect(url_for('tournament.manage_tournament', slug=slug))

            elif action == 'close_registration':
                tournament.status = 'setup'
                db.session.commit()
                flash('Tournament registration is now closed. Status returned to setup.', 'info')
                return redirect(url_for('tournament.manage_tournament', slug=slug))

            elif action == 'start_tournament':
                if tournament.status not in ['setup', 'registration']:
                    flash('Tournament is already started.', 'warning')
                    return redirect(url_for('tournament.manage_tournament', slug=slug))
                
                from app.services.utils.scheduler import auto_schedule_tournament

                if tournament.has_categories:
                    tournament.status = 'in_progress'
                    tournament.started_at = datetime.utcnow()
                    db.session.commit()
                    
                    from app.web.controllers.category import start_single_category
                    for cat in tournament.categories:
                        if cat.status == 'setup':
                            start_single_category(cat, tournament)
                    
                    # Automatically schedule Order of Play across all courts and days
                    sched_result = auto_schedule_tournament(tournament.id)
                    num_sched = sched_result.get('scheduled', 0) if isinstance(sched_result, dict) else 0

                    flash(f'Tournament started! Brackets generated and Order of Play automatically scheduled ({num_sched} matches assigned to courts).', 'success')
                    return redirect(url_for('tournament.manage_tournament', slug=slug))
                else:
                    # Legacy tournament without categories
                    if tournament.format == 'single_elimination':
                        fmt = get_format(tournament.format)
                        if fmt:
                            matches_data = fmt.generate(tournament, participants)
                        else:
                            matches_data = []

                        # Create match records
                        for match_data in matches_data:
                            match = Match(**match_data, tournament_id=tournament.id)
                            db.session.add(match)

                        tournament.status = 'in_progress'
                        tournament.started_at = datetime.utcnow()
                        db.session.commit()

                        # Automatically schedule Order of Play across all courts and days
                        sched_result = auto_schedule_tournament(tournament.id)
                        num_sched = sched_result.get('scheduled', 0) if isinstance(sched_result, dict) else 0

                        flash(f'Tournament started! Bracket generated and Order of Play automatically scheduled ({num_sched} matches assigned to courts).', 'success')
                        return redirect(url_for('tournament.manage_tournament', slug=slug))
                    else:
                        flash(f'Format "{tournament.format}" is not yet implemented. Coming soon!', 'warning')

            elif action == 'reset_tournament':
                if tournament.status in ['in_progress', 'completed']:
                    reason = request.form.get('audit_reason')
                    explanation = request.form.get('audit_explanation', '')
                    if not reason:
                        flash("Audit validation failed: Reason required to reset a tournament.", "error")
                        return redirect(url_for('tournament.manage_tournament', slug=slug))
                    if len(explanation.strip()) < 20:
                        flash("Audit validation failed: A detailed explanation (minimum 20 characters) is required for high-risk actions.", "error")
                        return redirect(url_for('tournament.manage_tournament', slug=slug))
                        
                    log_audit(
                        action_type='reset_tournament',
                        target_id=tournament.id,
                        target_name=f"Tournament Bracket: {tournament.name}",
                        reason=reason,
                        explanation=explanation
                    )
                    
                    # Delete matches
                    Match.query.filter_by(tournament_id=tournament.id).delete()

                    # Reset participants stats
                    for p in participants:
                        p.final_rank = None

                    tournament.status = 'setup'
                    tournament.started_at = None
                    tournament.completed_at = None

                    db.session.commit()
                    flash('Tournament bracket stopped and reset! You can now edit settings and add/remove players.', 'success')
                    return redirect(url_for('tournament.manage_tournament', slug=slug))
                else:
                    flash('Tournament is already in setup status.', 'warning')
                    return redirect(url_for('tournament.manage_tournament', slug=slug))

            elif action == 'update_schedule_settings':
                start_date_str = request.form.get('start_date', '').strip()
                end_date_str = request.form.get('end_date', '').strip()
                if start_date_str or end_date_str:
                    ok, dates_or_err = validate_tournament_dates(start_date_str, end_date_str)
                    if not ok:
                        flash(dates_or_err, 'error')
                        return redirect(url_for('tournament.manage_tournament', slug=slug))
                    tournament.start_date, tournament.end_date = dates_or_err

                num_courts_val = request.form.get('num_courts', type=int, default=1)
                tournament.num_courts = max(1, num_courts_val) if num_courts_val else 1
                tournament.court_names = request.form.get('court_names', '').strip()

                court_operating_start = request.form.get('court_operating_start', '08:00').strip()
                court_operating_end = request.form.get('court_operating_end', '20:00').strip()
                ok, hours_or_err = validate_operating_hours(court_operating_start, court_operating_end)
                if not ok:
                    flash(hours_or_err, 'error')
                    return redirect(url_for('tournament.manage_tournament', slug=slug))
                tournament.court_operating_start, tournament.court_operating_end = hours_or_err

                avg_dur = request.form.get('avg_match_duration', type=int, default=60)
                tournament.avg_match_duration = max(10, min(360, avg_dur if avg_dur else 60))

                buffer_mins = request.form.get('court_buffer_minutes', type=int, default=10)
                tournament.court_buffer_minutes = max(0, min(120, buffer_mins if buffer_mins is not None else 10))

                min_rest_str = request.form.get('min_rest_minutes')
                if min_rest_str and min_rest_str.strip() != '':
                    try:
                        tournament.min_rest_minutes = max(0, min(240, int(min_rest_str)))
                    except ValueError:
                        tournament.min_rest_minutes = 0
                else:
                    tournament.min_rest_minutes = 0

                max_matches_str = request.form.get('max_matches_per_player_day')
                if max_matches_str and max_matches_str.strip() != '':
                    try:
                        tournament.max_matches_per_player_day = max(1, min(20, int(max_matches_str)))
                    except ValueError:
                        tournament.max_matches_per_player_day = None
                else:
                    tournament.max_matches_per_player_day = None

                # Parse dynamic daily operating hours
                daily_dict = {}
                raw_json = request.form.get('daily_operating_hours')
                if raw_json:
                    try:
                        daily_dict = json.loads(raw_json)
                    except Exception:
                        daily_dict = {}

                for k, v in request.form.items():
                    if k.startswith('daily_start_'):
                        d_key = k[len('daily_start_'):]
                        if d_key not in daily_dict:
                            daily_dict[d_key] = {}
                        daily_dict[d_key]['start'] = v
                    elif k.startswith('daily_end_'):
                        d_key = k[len('daily_end_'):]
                        if d_key not in daily_dict:
                            daily_dict[d_key] = {}
                        daily_dict[d_key]['end'] = v

                if tournament.start_date and tournament.end_date:
                    num_days = (tournament.end_date - tournament.start_date).days + 1
                    valid_range = {(tournament.start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(num_days)}
                    daily_dict = {dk: dv for dk, dv in daily_dict.items() if dk in valid_range}

                tournament.daily_operating_hours = json.dumps(daily_dict) if daily_dict else None

                db.session.commit()

                # If tournament is already started, immediately recalculate the Order of Play with new hours
                if tournament.status == 'in_progress':
                    from app.services.utils.scheduler import auto_schedule_tournament
                    auto_schedule_tournament(tournament.id)

                flash('Tournament dates, courts, and operating hours updated successfully!', 'success')
                return redirect(url_for('tournament.manage_tournament', slug=slug))

            elif action == 'finish_tournament':
                tournament.status = 'completed'
                tournament.completed_at = datetime.utcnow()
                db.session.commit()

                flash('Tournament completed! 🏆', 'success')
                return redirect(url_for('tournament.manage_tournament', slug=slug))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to perform action: {str(e)}', 'error')
            return redirect(url_for('tournament.manage_tournament', slug=slug))


    # Calculate total unique players
    if tournament.has_categories:
        unique_players = set()
        for category in tournament.categories:
            for participant in category.participants:
                unique_players.add(participant.name)
        total_players = len(unique_players)
    else:
        # For non-category tournaments, participants are directly under the tournament
        total_players = len(participants)

    parsed_daily_hours = {}
    if tournament.daily_operating_hours:
        try:
            parsed_daily_hours = json.loads(tournament.daily_operating_hours)
        except Exception:
            parsed_daily_hours = {}

    pending_registrations = Registration.query.filter_by(tournament_id=tournament.id, status='pending').all()
    return render_template('tournament/manage.html',
                           pending_registrations=pending_registrations,
                           tournament=tournament,
                           participants=participants,
                           total_players=total_players,
                           parsed_daily_hours=parsed_daily_hours,
                           formats=TOURNAMENT_FORMATS)

@tournament_bp.route('/tournaments/<slug>/match/<int:match_id>/report', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def report_match_result(slug, match_id):
    """Report match result"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    
    match = Match.query.get_or_404(match_id)

    action = request.form.get('action')
    is_live_update = (action == 'live_score')
    winner_id = request.form.get('winner_id', type=int) if not is_live_update else None

    # Extract set scores from request
    form_data = {
        'set1_p1': request.form.get('set1_p1', ''),
        'set1_p2': request.form.get('set1_p2', ''),
        'tb1_p1': request.form.get('tb1_p1', ''),
        'tb1_p2': request.form.get('tb1_p2', ''),
        'set2_p1': request.form.get('set2_p1', ''),
        'set2_p2': request.form.get('set2_p2', ''),
        'tb2_p1': request.form.get('tb2_p1', ''),
        'tb2_p2': request.form.get('tb2_p2', ''),
        'set3_p1': request.form.get('set3_p1', ''),
        'set3_p2': request.form.get('set3_p2', ''),
        'tb3_p1': request.form.get('tb3_p1', ''),
        'tb3_p2': request.form.get('tb3_p2', ''),
        'set4_p1': request.form.get('set4_p1', ''),
        'set4_p2': request.form.get('set4_p2', ''),
        'tb4_p1': request.form.get('tb4_p1', ''),
        'tb4_p2': request.form.get('tb4_p2', ''),
        'set5_p1': request.form.get('set5_p1', ''),
        'set5_p2': request.form.get('set5_p2', ''),
        'tb5_p1': request.form.get('tb5_p1', ''),
        'tb5_p2': request.form.get('tb5_p2', ''),
    }

    try:
        # Process overrides
        scoring_format_override = request.form.get('scoring_format')
        if scoring_format_override:
            match.scoring_format = scoring_format_override
            
        num_sets_override = request.form.get('num_sets', type=int)
        if num_sets_override:
            match.num_sets = num_sets_override
            
        games_per_set_override = request.form.get('games_per_set', type=int)
        if games_per_set_override:
            match.games_per_set = games_per_set_override
            
        points_to_win_override = request.form.get('points_to_win', type=int)
        if points_to_win_override:
            match.points_to_win = points_to_win_override
            
        if match.category_id:
            category = Category.query.get(match.category_id)
            
            scoring_format = match.scoring_format or (category.scoring_format if category else 'games')
            
            if category and category.format == 'group_stage':
                # New scoring system based on total games
                total_games_target = category.total_games
                g1_val = form_data.get('set1_p1')
                g2_val = form_data.get('set1_p2')
                
                if not g1_val or not g2_val:
                    raise ValueError("Score is required.")
                
                try:
                    g1 = int(g1_val)
                    g2 = int(g2_val)
                except ValueError:
                    raise ValueError("Score must be integers.")
                    
                if g1 < 0 or g2 < 0:
                    raise ValueError("Scores cannot be negative.")

                if not is_live_update:
                    if g1 + g2 != total_games_target:
                        raise ValueError(f"Total games must sum to {total_games_target}. You entered {g1} and {g2} (sum: {g1+g2}).")
                        
                    actual_winner = match.participant1_id if g1 > g2 else match.participant2_id
                    if winner_id != actual_winner:
                        raise ValueError("Selected winner does not match the scores.")
                    
                match.score1 = str(g1)
                match.score2 = str(g2)
                
            elif scoring_format == 'points' or (category and category.format in ['round_robin', 'doubles_round_robin']):
                points_to_win = match.points_to_win or (category.points_to_win if category else 11)
                if scoring_format == 'points':
                    g1_val = request.form.get('points_p1')
                    g2_val = request.form.get('points_p2')
                else:
                    g1_val = form_data.get('set1_p1')
                    g2_val = form_data.get('set1_p2')
                
                if not g1_val or not g2_val:
                    raise ValueError("Score is required.")
                
                try:
                    g1 = int(g1_val)
                    g2 = int(g2_val)
                except ValueError:
                    raise ValueError("Score must be integers.")

                if g1 < 0 or g2 < 0:
                    raise ValueError("Scores cannot be negative.")
                    
                if not is_live_update:
                    winning_score = max(g1, g2)
                    losing_score = min(g1, g2)
                    
                    if winning_score < points_to_win:
                        raise ValueError(f"One player must reach {points_to_win} points to win.")
                        
                    diff = winning_score - losing_score
                    if diff < 2:
                        raise ValueError("A player must win by a difference of at least 2 points.")
                        
                    if winning_score > points_to_win and diff > 2:
                        raise ValueError(f"Invalid score. When extending past {points_to_win} points, the match ends as soon as a 2-point difference is reached.")
                        
                    actual_winner = match.participant1_id if g1 > g2 else match.participant2_id
                    if winner_id != actual_winner:
                        raise ValueError("Selected winner does not match the scores.")
                    
                match.score1 = str(g1)
                match.score2 = str(g2)
                
            else:
                # Legacy set scoring
                num_sets = match.num_sets or (category.num_sets if category and category.num_sets else (tournament.num_sets or 3))
                games_per_set = match.games_per_set or (category.games_per_set if category and category.games_per_set else (tournament.games_per_set or 6))

                score1, score2 = validate_and_format_score(
                    winner_id, match.participant1_id, match.participant2_id,
                    num_sets, games_per_set, form_data, is_live_update=is_live_update
                )

                match.score1 = score1
                match.score2 = score2
        else:
            # Fallback for tournaments without categories
            num_sets = tournament.num_sets or 3
            games_per_set = tournament.games_per_set or 6

            score1, score2 = validate_and_format_score(
                winner_id, match.participant1_id, match.participant2_id,
                num_sets, games_per_set, form_data, is_live_update=is_live_update
            )

            match.score1 = score1
            match.score2 = score2

        if is_live_update:
            match.status = 'in_progress'
            db.session.commit()
            flash('Live score updated successfully.', 'success')
            return redirect(url_for('tournament.view_tournament', slug=slug))

        match.winner_id = winner_id
        match.status = 'completed'
        match.completed_at = datetime.utcnow()
        db.session.commit()

        from app.services.leaderboard import update_live_player_stats
        update_live_player_stats(match)

        # Update next round match
        if tournament.format == 'single_elimination':
            # Find next round match
            next_round = match.round + 1
            next_match_number = (match.match_number + 1) // 2

            next_match = Match.query.filter_by(
                tournament_id=tournament.id,
                round=next_round,
                match_number=next_match_number
            ).first()

            if next_match:
                # Determine which slot to fill (participant1 or participant2)
                if match.match_number % 2 == 1:
                    next_match.participant1_id = winner_id
                else:
                    next_match.participant2_id = winner_id

        db.session.commit()
        
            
        flash('Match result reported successfully!', 'success')
    except ValueError as ve:
        db.session.rollback()
        flash(f'Invalid Tennis Score: {str(ve)}', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to report match result: {str(e)}', 'error')

    return redirect(url_for('tournament.view_tournament', slug=slug))

@tournament_bp.route('/match/<int:match_id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def toggle_match_status(match_id):
    """Toggle match status between pending and in_progress"""
    match = Match.query.get_or_404(match_id)
    if match.tournament:
        check_tournament_ownership(match.tournament)
    
    if match.status == 'completed':
        return jsonify({'success': False, 'message': 'Cannot toggle a completed match.'}), 400
        
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in ['pending', 'in_progress']:
        return jsonify({'success': False, 'message': 'Invalid status.'}), 400
        
    match.status = new_status
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'status': match.status})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@tournament_bp.route('/match/<int:match_id>/schedule', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def schedule_match(match_id):
    """Set the scheduled time for a match"""
    match = Match.query.get_or_404(match_id)
    if match.tournament:
        check_tournament_ownership(match.tournament)
    
    if match.status == 'completed':
        return jsonify({'success': False, 'message': 'Cannot schedule a completed match.'}), 400
        
    data = request.get_json()
    scheduled_time_str = data.get('scheduled_time')
    
    if scheduled_time_str:
        try:
            # First try parsing the custom format they type in
            match.scheduled_time = datetime.strptime(scheduled_time_str, '%d/%m/%Y %H:%M %p')
        except ValueError:
            try:
                # Fall back to standard ISO string from datetime-local
                match.scheduled_time = datetime.fromisoformat(scheduled_time_str)
            except Exception as e:
                return jsonify({'success': False, 'message': f'Invalid datetime format: {str(e)}'}), 400
    else:
        match.scheduled_time = None
        
    try:
        db.session.commit()
        return jsonify({
            'success': True, 
            'scheduled_time': match.scheduled_time.isoformat() if match.scheduled_time else None
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@tournament_bp.route('/tournaments/<slug>/seeding', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'superadmin')
def manage_tournament_seeding(slug):
    """Manage manual seeding for tournament participants"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    
    participants = Participant.query.filter_by(tournament_id=tournament.id).all()

    if request.method == 'POST':
        try:
            # Update seeds from form
            for participant in participants:
                seed_key = f'seed_{participant.id}'
                if seed_key in request.form:
                    new_seed = request.form.get(seed_key, type=int)
                    participant.manual_seed = new_seed

            db.session.commit()
            flash('Seeding updated successfully!', 'success')
            return redirect(url_for('tournament.manage_tournament', slug=slug))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update seeding: {str(e)}', 'error')
            return redirect(url_for('tournament.manage_tournament', slug=slug))

    return render_template('tournament/seeding.html',
                         tournament=tournament,
                         participants=participants)

@tournament_bp.route('/tournaments/<slug>/delete', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def delete_tournament(slug):
    """Delete tournament"""
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)
    
    # Audit Validation
    reason = request.form.get('audit_reason')
    explanation = request.form.get('audit_explanation', '')
    if not reason:
        flash("Audit validation failed: Reason required to delete a tournament.", "error")
        return redirect(url_for('tournament.manage_tournament', slug=slug))
    if len(explanation.strip()) < 20:
        flash("Audit validation failed: A detailed explanation (minimum 20 characters) is required for high-risk actions.", "error")
        return redirect(url_for('tournament.manage_tournament', slug=slug))

    try:
        
        log_audit(
            action_type='delete_tournament',
            target_id=tournament.id,
            target_name=tournament.name,
            reason=reason,
            explanation=explanation
        )
        db.session.delete(tournament)
        db.session.commit()
        flash('Tournament deleted successfully!', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete tournament: {str(e)}', 'error')

    return redirect(url_for('main.index'))


@tournament_bp.route('/t/<slug>/schedule')
@tournament_bp.route('/tournaments/<slug>/schedule')
def court_schedule(slug):
    """Public Court Schedule — shows all scheduled matches across all courts."""
    from app.services.utils.scheduler import get_order_of_play
    data = get_order_of_play(slug)
    return render_template(
        'tournament/order_of_play.html',
        courts=data['courts'],
        all_courts=list(data['courts'].keys()),
        tournament=data['tournament'],
        selected_court=None,
        is_export=request.args.get('export', '0') == '1',
    )


@tournament_bp.route('/t/<slug>/order-of-play', methods=['GET', 'POST'])
@tournament_bp.route('/tournaments/<slug>/order-of-play', methods=['GET', 'POST'])
def order_of_play(slug):
    """Order of Play page — Multi-day, PDF-ready, filterable by day & court."""
    from app.services.utils.scheduler import (
        get_order_of_play,
        auto_schedule_tournament,
        apply_weather_delay,
        reassign_match_court
    )
    from datetime import datetime

    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    # Handle organizer actions: Rain delay, regenerate schedule, move match
    if request.method == 'POST':
        action = request.form.get('action')
        user = get_current_user()
        if not user or user.role not in ('admin', 'superadmin') or (user.role != 'superadmin' and tournament.user_id != user.id):
            flash('Unauthorized to manage schedule.', 'error')
            return redirect(url_for('tournament.order_of_play', slug=slug))

        if action == 'reschedule_all':
            res = auto_schedule_tournament(tournament.id)
            flash(res.get('message', 'Tournament matches scheduled!'), 'success')
            return redirect(url_for('tournament.order_of_play', slug=slug))

        elif action == 'apply_delay':
            minutes = request.form.get('delay_minutes', type=int, default=30)
            court_filter = request.form.get('delay_court') or None
            count = apply_weather_delay(tournament.id, minutes, court_filter=court_filter)
            court_str = f" on {court_filter}" if court_filter else " across all courts"
            flash(f'Shifted {count} pending matches by +{minutes} minutes{court_str}.', 'info')
            return redirect(url_for('tournament.order_of_play', slug=slug))

        elif action == 'reassign_court':
            match_id = request.form.get('match_id', type=int)
            new_court = request.form.get('new_court')
            if match_id and new_court:
                reassign_match_court(match_id, new_court)
                flash(f'Match moved to {new_court}.', 'success')
            return redirect(url_for('tournament.order_of_play', slug=slug))

        elif action == 'set_match_status':
            match_id = request.form.get('match_id', type=int)
            new_status = request.form.get('status')
            if match_id and new_status in ['pending', 'in_progress']:
                match = Match.query.get(match_id)
                if match and match.tournament_id == tournament.id and match.status != 'completed':
                    match.status = new_status
                    db.session.commit()
                    status_label = "In Progress" if new_status == 'in_progress' else "To Play"
                    flash(f'Match #{match.match_number} marked as {status_label}.', 'success')
            date_arg = request.form.get('date') or request.args.get('date') or ''
            court_arg = request.form.get('court') or request.args.get('court') or ''
            return redirect(url_for('tournament.order_of_play', slug=slug, date=date_arg, court=court_arg))

    # Parse optional date filter
    date_param = request.args.get('date')
    filter_date = None
    if date_param:
        try:
            filter_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            pass

    data = get_order_of_play(slug, filter_date=filter_date)
    selected_court = request.args.get('court', None)
    is_export = request.args.get('export', '0') == '1'

    courts = data['courts']
    if selected_court and selected_court in courts:
        filtered_courts = {selected_court: courts[selected_court]}
    else:
        filtered_courts = courts

    return render_template(
        'tournament/order_of_play.html',
        courts=filtered_courts,
        all_courts=list(courts.keys()),
        selected_court=selected_court,
        tournament=data['tournament'],
        days_meta=data['days_meta'],
        active_date=data['active_date'],
        active_day_start=data.get('active_day_start'),
        active_day_end=data.get('active_day_end'),
        total_matches_scheduled=data['total_matches_scheduled'],
        is_export=is_export,
    )
