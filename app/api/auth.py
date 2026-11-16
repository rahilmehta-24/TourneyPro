from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from datetime import datetime
from . import api_bp
from app.domain.models import (
    User, db, Tournament, TournamentStaff,
    DeviceRegistration, InAppNotification, UserNotificationPreferences
)
from app.domain.schemas import (
    user_schema, notification_schema, notifications_schema,
    notification_preferences_schema
)

@api_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"success": False, "message": "Missing username or password"}), 400

    username = str(data['username']).strip()
    user = User.query.filter(db.or_(User.username.ilike(username), User.email.ilike(username))).first()

    if user and user.role == 'deleted':
        return jsonify({"success": False, "message": "This account has been deleted."}), 401

    if user and user.check_password(data['password']):
        from app.services.user_service import ensure_user_profile
        ensure_user_profile(user.id)

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        return jsonify({
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }), 200
    
    return jsonify({"success": False, "message": "Invalid credentials"}), 401


@api_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    from app.services.user_service import register_user
    result = register_user(
        username=data['username'],
        email=data['email'],
        password=data['password'],
        password_confirm=data.get('password_confirm'),
        full_name=data.get('full_name') or data.get('name'),
        gender=data.get('gender', 'Male'),
        contact_number=data.get('contact_number')
    )

    if not result.success:
        return jsonify({"success": False, "message": result.message}), result.status_code

    user = result.user
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    return jsonify({
        "success": True,
        "message": result.message,
        "category": result.category,
        "is_clean": result.is_clean,
        "has_existing_data": result.has_existing_data,
        "verification_failed": result.verification_failed,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 201


@api_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id)) if current_user_id and str(current_user_id).isdigit() else None
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    new_access_token = create_access_token(identity=str(user.id))
    return jsonify({
        "success": True,
        "access_token": new_access_token
    }), 200


@api_bp.route('/auth/court-login', methods=['POST'])
def court_login():
    """Court umpire & scorer quick login using 4 to 6 digit tournament PIN."""
    data = request.get_json() or {}
    pin = str(data.get('pin', '')).strip()
    slug = data.get('slug')
    tournament_id = data.get('tournament_id')

    if not pin or not pin.isdigit():
        return jsonify({"success": False, "message": "Valid numeric PIN required"}), 400

    tournament = None
    if slug:
        tournament = Tournament.query.filter_by(url_slug=slug).first()
    elif tournament_id:
        tournament = Tournament.query.get(tournament_id)

    query = TournamentStaff.query.filter_by(access_pin=pin)
    if tournament:
        query = query.filter_by(tournament_id=tournament.id)

    staff_candidates = query.all()
    if not staff_candidates:
        return jsonify({"success": False, "message": "Invalid access PIN"}), 401

    staff = staff_candidates[0]
    if staff.pin_expires_at and staff.pin_expires_at < datetime.utcnow():
        return jsonify({"success": False, "message": "Court access PIN has expired"}), 401

    if not tournament:
        tournament = Tournament.query.get(staff.tournament_id)

    identity = str(staff.user_id) if staff.user_id else f"court_staff_{staff.id}"
    additional_claims = {
        "court_pin_staff_id": staff.id,
        "tournament_id": tournament.id,
        "court": staff.assigned_court or "All Courts",
        "role": staff.role
    }

    access_token = create_access_token(identity=identity, additional_claims=additional_claims)

    return jsonify({
        "success": True,
        "access_token": access_token,
        "court": staff.assigned_court or "All Courts",
        "role": staff.role,
        "tournament": {
            "id": tournament.id,
            "name": tournament.name,
            "slug": tournament.url_slug
        }
    }), 200


@api_bp.route('/users/me', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id)) if current_user_id and str(current_user_id).isdigit() else None
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    # Ensure profile exists for authenticated user (self-healing if missing)
    from app.services.user_service import ensure_user_profile
    player = ensure_user_profile(user.id)

    player_data = None
    if player:
        total_m = player.matches_played or 0
        won_m = player.matches_won or 0
        lost_m = player.matches_lost or 0
        win_rate = round((won_m / total_m * 100), 1) if total_m > 0 else 0.0

        player_data = {
            "id": player.id,
            "name": player.name,
            "email": player.email,
            "registration_no": player.registration_no,
            "gender": player.gender,
            "age_category": player.age_category,
            "dob": player.dob.isoformat() if player.dob else None,
            "age": player.age,
            "contact_number": player.contact_number,
            "nationality": player.nationality,
            "height": player.height,
            "weight": player.weight,
            "blood_group": player.blood_group,
            "current_status": player.current_status,
            "academy": player.academy,
            "coach": player.coach,
            "avatar_url": player.avatar_url,
            "total_points": player.total_points or 0.0,
            "matches_played": total_m,
            "matches_won": won_m,
            "matches_lost": lost_m,
            "win_rate": win_rate
        }

    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None
        },
        "player": player_data
    }), 200


@api_bp.route('/users/delete_account', methods=['POST'])
@jwt_required()
def delete_account():
    """Mandatory account deletion for Google Play and Apple App Store compliance."""
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id)) if current_user_id and str(current_user_id).isdigit() else None
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    # Scrub push device registrations and notifications
    DeviceRegistration.query.filter_by(user_id=user.id).delete()
    InAppNotification.query.filter_by(user_id=user.id).delete()
    UserNotificationPreferences.query.filter_by(user_id=user.id).delete()

    # Check if user owns active tournaments
    owned_tournaments_count = Tournament.query.filter_by(user_id=user.id).count()
    if owned_tournaments_count > 0:
        # Anonymize PII to prevent breaking historic tournament integrity
        user.username = f"deleted_user_{user.id}"
        user.email = f"deleted_{user.id}@baseline.local"
        user.set_password("DELETED_ACCOUNT_SECURE_TOKEN_STUB")
    else:
        db.session.delete(user)

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Account successfully deleted and PII scrubbed"
    }), 200


# ----------------------------------------------------------------------
# DEVICE TOKEN REGISTRATION & NOTIFICATION ENDPOINTS
# ----------------------------------------------------------------------

@api_bp.route('/devices/register', methods=['POST'])
@jwt_required()
def register_device():
    current_user_id = get_jwt_identity()
    data = request.get_json() or {}
    device_token = data.get('device_token')
    platform = data.get('platform', 'android').lower()

    if not device_token:
        return jsonify({"success": False, "message": "device_token is required"}), 400

    existing = DeviceRegistration.query.filter_by(device_token=device_token).first()
    if existing:
        existing.user_id = int(current_user_id)
        existing.platform = platform
        existing.device_name = data.get('device_name', existing.device_name)
        existing.os_version = data.get('os_version', existing.os_version)
        existing.app_version = data.get('app_version', existing.app_version)
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
    else:
        reg = DeviceRegistration(
            user_id=int(current_user_id),
            device_token=device_token,
            platform=platform,
            device_name=data.get('device_name'),
            os_version=data.get('os_version'),
            app_version=data.get('app_version'),
            is_active=True
        )
        db.session.add(reg)

    db.session.commit()
    return jsonify({"success": True, "message": "Device registered successfully"}), 200


@api_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_user_notifications():
    current_user_id = get_jwt_identity()
    notifications = InAppNotification.query.filter_by(
        user_id=int(current_user_id)
    ).order_by(InAppNotification.created_at.desc()).limit(50).all()

    unread_count = InAppNotification.query.filter_by(
        user_id=int(current_user_id),
        is_read=False
    ).count()

    return jsonify({
        "success": True,
        "unread_count": unread_count,
        "notifications": notifications_schema.dump(notifications)
    }), 200


@api_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@jwt_required()
def mark_notification_read(notification_id):
    current_user_id = get_jwt_identity()
    notif = InAppNotification.query.filter_by(
        id=notification_id,
        user_id=int(current_user_id)
    ).first_or_404()

    notif.is_read = True
    notif.read_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"success": True, "message": "Notification marked as read"}), 200


@api_bp.route('/users/notification-preferences', methods=['GET'])
@jwt_required()
def get_notification_preferences():
    current_user_id = get_jwt_identity()
    prefs = UserNotificationPreferences.query.filter_by(user_id=int(current_user_id)).first()
    if not prefs:
        prefs = UserNotificationPreferences(user_id=int(current_user_id))
        db.session.add(prefs)
        db.session.commit()

    return jsonify({
        "success": True,
        "preferences": notification_preferences_schema.dump(prefs)
    }), 200


@api_bp.route('/users/notification-preferences', methods=['PUT'])
@jwt_required()
def update_notification_preferences():
    current_user_id = get_jwt_identity()
    prefs = UserNotificationPreferences.query.filter_by(user_id=int(current_user_id)).first()
    if not prefs:
        prefs = UserNotificationPreferences(user_id=int(current_user_id))
        db.session.add(prefs)

    data = request.get_json() or {}
    for field in [
        'notify_match_called', 'notify_draw_published',
        'notify_registration_updates', 'notify_match_results',
        'notify_academy_announcements'
    ]:
        if field in data:
            setattr(prefs, field, bool(data[field]))

    prefs.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "success": True,
        "preferences": notification_preferences_schema.dump(prefs)
    }), 200


@api_bp.route('/admin/users', methods=['POST'])
@jwt_required()
def admin_create_user_api():
    """Administrator user creation endpoint with workspace initialization and verification."""
    current_user_id = get_jwt_identity()
    admin_user = User.query.get(int(current_user_id)) if current_user_id and str(current_user_id).isdigit() else None
    if not admin_user or admin_user.role not in ('superadmin', 'admin'):
        return jsonify({"success": False, "message": "Forbidden: Administrator privileges required"}), 403

    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'user')
    full_name = data.get('full_name')
    simulate_fail = bool(data.get('simulate_verification_failure', False))

    from app.services.user_service import admin_create_user
    result = admin_create_user(
        username=username,
        email=email,
        password=password,
        role=role,
        full_name=full_name,
        simulate_verification_failure=simulate_fail
    )

    return jsonify(result.to_dict()), result.status_code
