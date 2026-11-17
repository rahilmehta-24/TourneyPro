from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from . import api_bp
from app.domain.models import (
    db, Tournament, Category, Player, Participant, Registration,
    TournamentStaff, User, InAppNotification
)
from app.domain.schemas import registration_schema, registrations_schema


@api_bp.route('/tournaments/<slug>/register', methods=['POST'])
@jwt_required()
def register_for_tournament(slug):
    """Register a player for a tournament category via mobile app."""
    current_user_id = int(get_jwt_identity())
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    if tournament.status not in ['registration', 'setup', 'in_progress']:
        return jsonify({"success": False, "message": "Tournament registration is closed"}), 400

    if tournament.registration_closes_at and tournament.registration_closes_at < datetime.utcnow():
        return jsonify({"success": False, "message": "Tournament registration deadline has passed"}), 400

    data = request.get_json() or {}
    category_id = data.get('category_id')
    player_id = data.get('player_id')

    if not category_id or not player_id:
        return jsonify({"success": False, "message": "category_id and player_id are required"}), 400

    category = Category.query.filter_by(id=category_id, tournament_id=tournament.id).first()
    if not category:
        return jsonify({"success": False, "message": "Invalid category for this tournament"}), 400

    player = Player.query.get(player_id)
    if not player:
        return jsonify({"success": False, "message": "Player profile not found"}), 404

    caller = User.query.get(current_user_id)
    is_authorized = (
        player.user_id == current_user_id or
        (caller and (caller.role == 'superadmin' or tournament.user_id == caller.id))
    )
    if not is_authorized:
        return jsonify({"success": False, "message": "Forbidden: You may only register player profiles associated with your account"}), 403

    if player.user_id == current_user_id and caller and not caller.profile_completed:
        return jsonify({
            "success": False,
            "message": f"Player profile is {caller.completion_percentage}% complete. Please complete your profile before registering.",
            "code": "PROFILE_INCOMPLETE",
            "completion_percentage": caller.completion_percentage
        }), 400

    # Duplicate check
    existing = Registration.query.filter_by(
        tournament_id=tournament.id,
        category_id=category_id,
        player_id=player_id
    ).first()
    if existing:
        return jsonify({"success": False, "message": "Player is already registered for this category"}), 409

    expected_fee = float(category.entry_fee or 0.0)
    if "doubles" in (category.format or "").lower() or "doubles" in (category.name or "").lower():
        expected_fee *= 2

    payment_method = data.get('payment_method', 'online').strip().lower()
    if payment_method not in ['online', 'cash', 'free']:
        payment_method = 'online'

    if expected_fee > 0 and payment_method == 'free':
        return jsonify({"success": False, "message": "This category requires an entry fee. Free registration is not permitted."}), 400

    amount_due = expected_fee

    transaction_id = data.get('transaction_id', '').strip()
    partner_name = data.get('partner_name', '').strip() or None
    partner_mobile = data.get('partner_mobile', '').strip() or None
    player2_id = data.get('player2_id')

    payment_status = 'pending'
    if payment_method == 'free':
        payment_status = 'paid'

    registration = Registration(
        tournament_id=tournament.id,
        category_id=category.id,
        user_id=current_user_id,
        player_id=player.id,
        player2_id=player2_id,
        partner_name=partner_name,
        partner_mobile=partner_mobile,
        status='pending',
        payment_status=payment_status,
        amount_due=amount_due,
        transaction_id=transaction_id,
        payment_method=payment_method
    )
    db.session.add(registration)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Registration submitted successfully",
        "registration": registration_schema.dump(registration)
    }), 201


@api_bp.route('/registrations/<int:registration_id>/review', methods=['POST'])
@jwt_required()
def review_registration(registration_id):
    """Tournament organizer/admin reviews and approves or rejects a registration."""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    reg = Registration.query.get_or_404(registration_id)
    tournament = reg.tournament

    # Verify authorization
    is_staff = False
    staff = TournamentStaff.query.filter_by(tournament_id=tournament.id, user_id=user.id).first()
    if staff and staff.role in ('manager', 'official'):
        is_staff = True

    if user.role != 'superadmin' and tournament.user_id != user.id and not is_staff:
        return jsonify({"success": False, "message": "Forbidden: Only tournament organizers can review entries"}), 403

    data = request.get_json() or {}
    status = data.get('status', '').strip().lower()
    if status not in ['approved', 'rejected']:
        return jsonify({"success": False, "message": "Status must be 'approved' or 'rejected'"}), 400

    payment_status = data.get('payment_status', reg.payment_status).strip().lower()
    payment_method = data.get('payment_method', reg.payment_method or 'online').strip().lower()

    reg.status = status
    reg.payment_status = payment_status
    if payment_method:
        reg.payment_method = payment_method

    if status == 'approved':
        # Add participant to category if not already exists
        participant_name = f"{reg.player.name}{' / ' + reg.partner_name if reg.partner_name else ''}"
        existing_part = Participant.query.filter_by(
            tournament_id=tournament.id,
            category_id=reg.category_id,
            player_id=reg.player_id
        ).first()

        if not existing_part:
            participant = Participant(
                tournament_id=tournament.id,
                category_id=reg.category_id,
                name=participant_name,
                player_id=reg.player_id,
                player2_id=reg.player2_id,
                partner_name=reg.partner_name,
                partner_mobile=reg.partner_mobile,
                email=reg.player.email or "",
                mobile=reg.player.contact_number or "",
                gender=reg.player.gender or "",
                dob=reg.player.dob,
                payment_status=payment_status,
                payment_method=payment_method
            )
            db.session.add(participant)

        # Notify player
        notif = InAppNotification(
            user_id=reg.user_id,
            title="Registration Approved! 🎾",
            body=f"Your entry for {tournament.name} ({reg.category.name if reg.category else 'General'}) has been approved.",
            notification_type="registration_update",
            reference_type="tournament",
            reference_id=tournament.id
        )
        db.session.add(notif)

    elif status == 'rejected':
        reason = data.get('reason', 'Entry could not be accepted')
        notif = InAppNotification(
            user_id=reg.user_id,
            title="Registration Update",
            body=f"Your entry for {tournament.name} was not accepted: {reason}",
            notification_type="registration_update",
            reference_type="tournament",
            reference_id=tournament.id
        )
        db.session.add(notif)

    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"Registration {status}",
        "registration": registration_schema.dump(reg)
    }), 200


@api_bp.route('/users/my-registrations', methods=['GET'])
@jwt_required()
def get_my_registrations():
    """Return all tournament registrations for the currently authenticated user."""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    if not user or user.username == 'anonymous_registrations' or user.email == 'anonymous@tourneypro.com':
        return jsonify({"success": False, "message": "Forbidden"}), 403

    registrations = Registration.query.filter_by(
        user_id=current_user_id
    ).order_by(Registration.created_at.desc()).all()

    return jsonify({
        "success": True,
        "registrations": registrations_schema.dump(registrations)
    }), 200


@api_bp.route('/tournaments/<slug>/registrations', methods=['GET'])
@jwt_required()
def get_tournament_registrations(slug):
    """Organizer view: return all registrations for this tournament."""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    is_staff = False
    if user:
        staff = TournamentStaff.query.filter_by(tournament_id=tournament.id, user_id=user.id).first()
        if staff and staff.role in ('manager', 'official'):
            is_staff = True

    if user.role != 'superadmin' and tournament.user_id != user.id and not is_staff:
        return jsonify({"success": False, "message": "Forbidden"}), 403

    status_filter = request.args.get('status')
    query = Registration.query.filter_by(tournament_id=tournament.id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    registrations = query.order_by(Registration.created_at.desc()).all()
    return jsonify({
        "success": True,
        "registrations": registrations_schema.dump(registrations)
    }), 200

