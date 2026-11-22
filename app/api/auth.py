from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from datetime import datetime
from . import api_bp
from app.domain.models import (
    User, db, Tournament, TournamentStaff,
    DeviceRegistration, InAppNotification, UserNotificationPreferences
)
from app.domain.schemas import (
    notifications_schema,
    notification_preferences_schema
)

@api_bp.route('/auth/login', methods=['POST'])
def login():
    from app.services.utils.rate_limiter import check_rate_limit, get_client_ip, reset_rate_limit
    client_ip = get_client_ip()
    allowed, retry_after = check_rate_limit(f"api_login_{client_ip}", max_requests=10, window_seconds=60)
    if not allowed:
        return jsonify({"success": False, "message": f"Too many login attempts. Please wait {retry_after} seconds before trying again."}), 429

    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"success": False, "message": "Missing username or password"}), 400

    username = str(data['username']).strip()
    user = User.query.filter(db.or_(User.username.ilike(username), User.email.ilike(username))).first()

    if user and (user.role == 'deleted' or user.username == 'anonymous_registrations' or user.email == 'anonymous@tourneypro.com'):
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

    if user and user.check_password(data['password']):
        reset_rate_limit(f"api_login_{client_ip}")
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
                "role": user.role,
                "full_name": user.full_name,
                "registration_intent": user.registration_intent,
                "completion_percentage": user.completion_percentage,
                "profile_completed": user.profile_completed,
                "is_email_verified": user.is_email_verified,
                "account_status": user.account_status
            }
        }), 200
    
    return jsonify({"success": False, "message": "Invalid credentials"}), 401


@api_bp.route('/auth/register', methods=['POST'])
def register():
    from app.services.utils.rate_limiter import check_rate_limit, get_client_ip, reset_rate_limit
    client_ip = get_client_ip()
    allowed, retry_after = check_rate_limit(f"api_register_{client_ip}", max_requests=5, window_seconds=60)
    if not allowed:
        return jsonify({"success": False, "message": f"Too many registration attempts. Please wait {retry_after} seconds before trying again."}), 429

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
        registration_intent=data.get('registration_intent', 'user'),
        gender=data.get('gender'),
        contact_number=data.get('contact_number')
    )

    if not result.success:
        return jsonify({"success": False, "message": result.message}), result.status_code

    reset_rate_limit(f"api_register_{client_ip}")
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
            "role": user.role,
            "full_name": user.full_name,
            "registration_intent": user.registration_intent,
            "completion_percentage": user.completion_percentage,
            "profile_completed": user.profile_completed,
            "is_email_verified": user.is_email_verified,
            "account_status": user.account_status
        }
    }), 201


@api_bp.route('/auth/profile/complete', methods=['POST'])
@jwt_required()
def complete_profile():
    """Stage 2 Onboarding: Complete athletic player profile and calculate percentage."""
    current_user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    from datetime import datetime
    dob_val = None
    if data.get('dob'):
        try:
            dob_val = datetime.strptime(str(data['dob']), "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format for dob (YYYY-MM-DD required)"}), 400

    from app.services.user_service import complete_player_profile
    res = complete_player_profile(
        user_id=current_user_id,
        full_name=data.get('full_name') or data.get('name'),
        gender=data.get('gender'),
        dob=dob_val,
        contact_number=data.get('contact_number') or data.get('phone_number'),
        primary_sport=data.get('primary_sport', 'Tennis'),
        skill_level=data.get('skill_level'),
        preferred_competition_category=data.get('preferred_competition_category'),
        emergency_contact_name=data.get('emergency_contact_name'),
        emergency_contact_phone=data.get('emergency_contact_phone'),
        nationality=data.get('nationality'),
        height=data.get('height'),
        weight=data.get('weight'),
        blood_group=data.get('blood_group'),
        address=data.get('address'),
        academy=data.get('academy'),
        coach=data.get('coach'),
        avatar_url=data.get('avatar_url'),
        bio=data.get('bio')
    )
    status_code = 200 if res.get('success') else 400
    return jsonify(res), status_code


@api_bp.route('/auth/verify-email', methods=['POST'])
def verify_email():
    data = request.get_json() or {}
    token = data.get('token') or request.args.get('token')
    if not token:
        return jsonify({"success": False, "message": "Verification token required"}), 400

    from app.services.user_service import verify_user_email
    res = verify_user_email(token)
    status_code = 200 if res.get('success') else 400
    return jsonify(res), status_code


@api_bp.route('/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({"success": False, "message": "Email is required"}), 400

    from app.services.user_service import request_password_reset
    res = request_password_reset(email)
    return jsonify(res), 200


@api_bp.route('/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    token = data.get('token')
    password = data.get('password')
    password_confirm = data.get('password_confirm')
    if not token or not password:
        return jsonify({"success": False, "message": "Token and new password are required"}), 400

    from app.services.user_service import reset_password_with_token
    res = reset_password_with_token(token, password, password_confirm)
    status_code = 200 if res.get('success') else 400
    return jsonify(res), status_code


@api_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, int(current_user_id)) if current_user_id and str(current_user_id).isdigit() else None
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
        tournament = db.session.get(Tournament, tournament_id)

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
        tournament = db.session.get(Tournament, staff.tournament_id)

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
    user = db.session.get(User, int(current_user_id)) if current_user_id and str(current_user_id).isdigit() else None
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
            "profile_status": player.profile_status,
            "primary_sport": player.primary_sport,
            "skill_level": player.skill_level,
            "preferred_competition_category": player.preferred_competition_category,
            "emergency_contact_name": player.emergency_contact_name,
            "emergency_contact_phone": player.emergency_contact_phone,
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
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "registration_intent": user.registration_intent,
            "completion_percentage": user.completion_percentage,
            "profile_completed": user.profile_completed,
            "is_email_verified": user.is_email_verified,
            "account_status": user.account_status,
            "created_at": user.created_at.isoformat() if user.created_at else None
        },
        "player": player_data
    }), 200


@api_bp.route('/security/app-verify', methods=['GET', 'POST'])
def app_verify_security():
    """
    On-boot mobile security verification endpoint.
    Performs comprehensive verification of backend security controls,
    session validity, profile data integrity, and database health.
    Returns 100% pass score only when all applicable checks succeed.
    """
    checks = {}
    passed_count = 0
    total_checks = 0

    # Check 1: Database Connectivity & Query Health
    total_checks += 1
    try:
        db.session.execute(db.text("SELECT 1")).scalar()
        checks["database_connectivity"] = {
            "status": "PASS",
            "description": "Database connection and query engine operational"
        }
        passed_count += 1
    except Exception as e:
        checks["database_connectivity"] = {
            "status": "FAIL",
            "description": f"Database check failed: {str(e)}"
        }

    # Check 2: Environment & Cryptographic Security
    total_checks += 1
    from flask import current_app
    has_secret = bool(current_app.config.get('SECRET_KEY'))
    has_jwt_secret = bool(current_app.config.get('JWT_SECRET_KEY'))
    httponly = current_app.config.get('SESSION_COOKIE_HTTPONLY', True)
    if has_secret and has_jwt_secret and httponly:
        checks["environment_security"] = {
            "status": "PASS",
            "description": "Cryptographic secrets and cookie protections active"
        }
        passed_count += 1
    else:
        checks["environment_security"] = {
            "status": "FAIL",
            "description": "Environment security flags misconfigured"
        }

    # Check 3: Rate Limiter Status
    total_checks += 1
    from app.services.utils.rate_limiter import get_client_ip, check_rate_limit
    client_ip = get_client_ip()
    allowed, retry_after = check_rate_limit(f"app_boot_{client_ip}", max_requests=60, window_seconds=60)
    if allowed:
        checks["rate_limiter"] = {
            "status": "PASS",
            "description": f"Client IP {client_ip} clean and within security thresholds"
        }
        passed_count += 1
    else:
        checks["rate_limiter"] = {
            "status": "FAIL",
            "description": f"Rate limit exceeded. Retry after {retry_after}s"
        }

    # Check 4 & 5: Authentication Session & Data Isolation (if Bearer token supplied)
    auth_header = request.headers.get('Authorization', '')
    user_payload = None
    player_payload = None

    if auth_header.startswith('Bearer '):
        total_checks += 2
        raw_token = auth_header.split(' ', 1)[1].strip()
        try:
            from flask_jwt_extended import decode_token
            decoded = decode_token(raw_token)
            user_id = decoded.get('sub')
            
            user = db.session.get(User, int(user_id)) if user_id and str(user_id).isdigit() else None
            if not user or user.role == 'deleted':
                checks["auth_session"] = {
                    "status": "FAIL",
                    "description": "Account does not exist or has been deleted"
                }
                checks["data_isolation"] = {
                    "status": "FAIL",
                    "description": "Cannot verify data isolation for invalid user"
                }
            else:
                checks["auth_session"] = {
                    "status": "PASS",
                    "description": f"Authenticated session valid for user '{user.username}' (role: {user.role})"
                }
                passed_count += 1

                # Data isolation & profile self-healing
                from app.services.user_service import ensure_user_profile
                player = ensure_user_profile(user.id)
                if player and player.user_id == user.id:
                    checks["data_isolation"] = {
                        "status": "PASS",
                        "description": f"Profile isolation verified. Player record #{player.id} bound to UID #{user.id}"
                    }
                    passed_count += 1

                    total_m = player.matches_played or 0
                    won_m = player.matches_won or 0
                    lost_m = player.matches_lost or 0
                    win_rate = round((won_m / total_m * 100), 1) if total_m > 0 else 0.0

                    player_payload = {
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
                else:
                    checks["data_isolation"] = {
                        "status": "FAIL",
                        "description": "Player profile failed isolation binding"
                    }

                user_payload = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }

        except Exception as e:
            checks["auth_session"] = {
                "status": "FAIL",
                "description": f"Token verification error: {str(e)}"
            }
            checks["data_isolation"] = {
                "status": "FAIL",
                "description": "Data isolation check aborted due to token error"
            }

    score = int((passed_count / total_checks) * 100) if total_checks > 0 else 0
    all_passed = (score == 100)

    status_code = 200 if all_passed else 400
    if not all_passed and checks.get("auth_session", {}).get("status") == "FAIL":
        status_code = 401

    return jsonify({
        "success": all_passed,
        "status": "passed" if all_passed else "failed",
        "score": score,
        "passed_checks": passed_count,
        "total_checks": total_checks,
        "checks": checks,
        "user": user_payload,
        "player": player_payload
    }), status_code


@api_bp.route('/organizer/activate', methods=['POST'])
@jwt_required()
def activate_organizer():
    """Self-service tournament organizer activation for mobile app."""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, int(current_user_id)) if current_user_id and str(current_user_id).isdigit() else None
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    data = request.get_json() or {}
    org_name = (data.get('organization_name') or '').strip()
    contact_phone = (data.get('contact_phone') or '').strip()
    agreed_terms = data.get('agreed_terms')

    if not org_name or len(org_name) < 3:
        return jsonify({"success": False, "message": "Organization, club, or host name must be at least 3 characters."}), 400

    if not agreed_terms:
        return jsonify({"success": False, "message": "You must agree to the Tournament Organizer Fair Play & Security terms."}), 400

    user.role = 'admin'
    user.admin_requested = False

    from app.domain.models import Player
    player = Player.query.filter_by(user_id=user.id).first()
    if player:
        if not player.academy:
            player.academy = org_name
        if contact_phone and not player.contact_number:
            player.contact_number = contact_phone

    from app.services.utils.audit import log_audit
    log_audit(
        action_type="organizer_self_activation",
        target_id=user.id,
        target_name=user.username,
        reason="Self-Service Organizer Activation",
        explanation=f"User activated tournament organizer status for club/org '{org_name}'.",
        user_id=user.id
    )

    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"Organizer status activated! Welcome to the Baseline Society Tournament Host Network, {org_name}.",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 200


@api_bp.route('/users/delete_account', methods=['POST'])
@jwt_required()
def delete_account():
    """Mandatory account deletion for Google Play and Apple App Store compliance."""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, int(current_user_id)) if current_user_id and str(current_user_id).isdigit() else None
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
    admin_user = db.session.get(User, int(current_user_id)) if current_user_id and str(current_user_id).isdigit() else None
    if not admin_user or admin_user.role != 'superadmin':
        return jsonify({"success": False, "message": "Forbidden: Superadmin privileges required"}), 403

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
