"""
User Service — User Creation, Workspace Initialization & Persistence Verification
The Baseline Society
"""

import random
from datetime import date, timedelta
from typing import Optional, Dict, Any
from app import db
from app.domain.models import (
    User, Player, Tournament, Registration,
    TournamentStaff, Academy, AcademyMember,
    UserNotificationPreferences
)

# Standard Notification Messages (Exact String Specifications)
MSG_CLEAN_WORKSPACE = (
    "User created successfully! A fresh workspace has been initialized. "
    "No existing user data was found or carried over."
)
MSG_EXISTING_DATA_RETAINED = (
    "User created successfully! Previously saved data associated with this user "
    "has been detected and retained."
)
MSG_VERIFICATION_FAILED = (
    "User created successfully, but workspace initialization could not be verified. "
    "Please review the user's data before proceeding."
)

# Standard User Registration Messages
MSG_REGISTRATION_CLEAN_WORKSPACE = (
    "Registration successful! Your Baseline Society account and personal workspace have been created."
)
MSG_REGISTRATION_EXISTING_DATA = (
    "Your account has been successfully registered. Previously saved data associated with your account has been retained."
)
MSG_REGISTRATION_INIT_FAILED = (
    "Your account was created, but profile initialization could not be completed. Please contact the administrator."
)


class UserCreationResult:
    """Encapsulates the result of admin user creation and workspace verification."""

    def __init__(
        self,
        success: bool,
        message: str,
        category: str,
        user: Optional[User] = None,
        status_code: int = 200,
        is_clean: bool = False,
        has_existing_data: bool = False,
        verification_failed: bool = False,
    ):
        self.success = success
        self.message = message
        self.category = category  # 'success', 'warning', 'error'
        self.user = user
        self.status_code = status_code
        self.is_clean = is_clean
        self.has_existing_data = has_existing_data
        self.verification_failed = verification_failed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "category": self.category,
            "is_clean": self.is_clean,
            "has_existing_data": self.has_existing_data,
            "verification_failed": self.verification_failed,
            "user": (
                {
                    "id": self.user.id,
                    "username": self.user.username,
                    "email": self.user.email,
                    "role": self.user.role,
                }
                if self.user
                else None
            ),
        }


def check_user_existing_data(user_id: int) -> int:
    """
    Counts existing records strictly associated with the given user_id
    across all user-owned domain models.
    """
    count = 0
    count += Tournament.query.filter_by(user_id=user_id).count()
    count += Player.query.filter_by(user_id=user_id).count()
    count += Registration.query.filter_by(user_id=user_id).count()
    count += TournamentStaff.query.filter_by(user_id=user_id).count()
    count += AcademyMember.query.filter_by(user_id=user_id).count()
    count += Academy.query.filter_by(owner_id=user_id).count()
    return count


def admin_create_user(
    username: str,
    email: str,
    password: str,
    role: str = "user",
    full_name: Optional[str] = None,
    simulate_verification_failure: bool = False,
) -> UserCreationResult:
    """
    Creates a new user as an administrator, initializes their workspace environment,
    and verifies persistence and data isolation.

    Returns:
        UserCreationResult with exact status message, toast category, and verification state.
    """
    username = (username or "").strip()
    email = (email or "").strip().lower()
    role = (role or "user").strip().lower()

    if not username or not email or not password:
        return UserCreationResult(
            success=False,
            message="Username, email, and password are required.",
            category="error",
            status_code=400,
        )

    if role not in ("admin", "user", "player"):
        role = "user"

    # Check for existing user account to prevent duplicate usernames/emails
    existing_by_username = User.query.filter_by(username=username).first()
    if existing_by_username:
        return UserCreationResult(
            success=False,
            message="Username already exists.",
            category="error",
            status_code=400,
        )

    existing_by_email = User.query.filter_by(email=email).first()
    if existing_by_email:
        return UserCreationResult(
            success=False,
            message="Email already exists.",
            category="error",
            status_code=400,
        )

    try:
        # Step 1: Create the User record
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        # Flush to obtain database-generated user.id
        db.session.flush()

        actual_user_id = user.id

        # Step 2: Determine data existence using the actual user ID
        existing_record_count = check_user_existing_data(actual_user_id)

        # Check if an unassigned player profile previously existed for this email
        # that should be preserved and linked to this newly created user ID
        unassigned_player = Player.query.filter(
            Player.user_id.is_(None),
            Player.email.ilike(email)
        ).first()

        if unassigned_player:
            unassigned_player.user_id = actual_user_id
            existing_record_count += 1

        has_existing_data = existing_record_count > 0

        # Step 3: Workspace Environment Initialization
        if has_existing_data:
            # PRESERVE existing records: do not overwrite, reset, or delete.
            # Ensure notification preferences exist if missing
            prefs = UserNotificationPreferences.query.filter_by(user_id=actual_user_id).first()
            if not prefs:
                db.session.add(UserNotificationPreferences(user_id=actual_user_id))
            db.session.commit()
        else:
            # CLEAN DATA: Initialize an isolated fresh workspace for the user
            prefs = UserNotificationPreferences(user_id=actual_user_id)
            db.session.add(prefs)

            # Initialize fresh player profile if standard user role
            if role in ("user", "player"):
                display_name = full_name.strip() if full_name else username
                current_date = date.today()
                reg_no = f"TP-{current_date.year}-{random.randint(0x1000, 0xFFFF):X}"

                new_player = Player(
                    user_id=actual_user_id,
                    name=display_name,
                    email=email,
                    gender="Male",
                    age_category="Open",
                    registration_no=reg_no,
                    registration_date=current_date,
                    registration_validity=current_date + timedelta(days=365),
                    current_status="Active",
                )
                db.session.add(new_player)

            db.session.commit()

        # Step 4: Verification of Data Persistence and Strict Isolation
        verification_passed = False
        try:
            if simulate_verification_failure:
                raise RuntimeError("Simulated verification failure for testing/diagnostics")

            # Verify User persists in database by user_id
            reloaded_user = db.session.get(User, actual_user_id)
            if not reloaded_user:
                raise ValueError("User record not found in database during post-creation verification")

            # Verify notification preferences exist and are strictly bound to user_id
            reloaded_prefs = UserNotificationPreferences.query.filter_by(user_id=actual_user_id).first()
            if not reloaded_prefs or reloaded_prefs.user_id != actual_user_id:
                raise ValueError("Notification preferences missing or not strictly associated with user_id")

            if not has_existing_data:
                # Verify strict isolation for clean workspace:
                # No tournaments, registrations, or staff assignments should exist
                t_count = Tournament.query.filter_by(user_id=actual_user_id).count()
                r_count = Registration.query.filter_by(user_id=actual_user_id).count()
                s_count = TournamentStaff.query.filter_by(user_id=actual_user_id).count()

                if t_count != 0 or r_count != 0 or s_count != 0:
                    raise ValueError("Unintended foreign data detected in freshly initialized workspace")

                if role in ("user", "player"):
                    reloaded_player = Player.query.filter_by(user_id=actual_user_id).first()
                    if not reloaded_player or reloaded_player.user_id != actual_user_id:
                        raise ValueError("Initialized player profile not verified")
            else:
                # Verify existing data was strictly preserved
                rechecked_count = check_user_existing_data(actual_user_id)
                if rechecked_count < existing_record_count:
                    raise ValueError("Existing user data appears to have been lost or overwritten")

            verification_passed = True
        except Exception:
            verification_passed = False

        # Step 5: Deliver appropriate notification based on verified result
        if not verification_passed:
            return UserCreationResult(
                success=True,
                message=MSG_VERIFICATION_FAILED,
                category="warning",
                user=user,
                status_code=200,
                verification_failed=True,
            )
        elif has_existing_data:
            return UserCreationResult(
                success=True,
                message=MSG_EXISTING_DATA_RETAINED,
                category="success",
                user=user,
                status_code=201,
                has_existing_data=True,
            )
        else:
            return UserCreationResult(
                success=True,
                message=MSG_CLEAN_WORKSPACE,
                category="success",
                user=user,
                status_code=201,
                is_clean=True,
            )

    except Exception as e:
        db.session.rollback()
        return UserCreationResult(
            success=False,
            message=f"Error creating user: {str(e)}",
            category="error",
            status_code=500,
        )


def ensure_user_profile(user_id: int) -> Optional[Player]:
    """
    Ensures that a user has an associated Player profile.
    If missing, securely initializes a clean profile shell for this user_id.
    """
    user = db.session.get(User, user_id)
    if not user:
        return None

    player = Player.query.filter_by(user_id=user.id).first()
    if player:
        return player

    # Check if an unassigned player profile exists with user's email
    unassigned = Player.query.filter(
        Player.user_id.is_(None),
        Player.email.ilike(user.email)
    ).first()
    if unassigned:
        unassigned.user_id = user.id
        db.session.commit()
        return unassigned

    # Initialize a clean, unpopulated player profile shell
    current_date = date.today()
    reg_no = f"TP-{current_date.year}-{random.randint(0x1000, 0xFFFF):X}"
    new_player = Player(
        user_id=user.id,
        name=user.full_name or user.username,
        email=user.email,
        registration_no=reg_no,
        registration_date=current_date,
        registration_validity=current_date + timedelta(days=365),
        current_status="Active",
        profile_status="complete" if user.profile_completed else "incomplete",
        total_points=0.0,
        matches_played=0,
        matches_won=0,
        matches_lost=0
    )
    db.session.add(new_player)
    db.session.commit()
    return new_player
    db.session.add(new_player)

    prefs = UserNotificationPreferences.query.filter_by(user_id=user.id).first()
    if not prefs:
        db.session.add(UserNotificationPreferences(user_id=user.id))

    db.session.commit()
    return new_player


def register_user(
    username: str,
    email: str,
    password: str,
    password_confirm: Optional[str] = None,
    full_name: Optional[str] = None,
    registration_intent: str = "user",
    gender: Optional[str] = None,
    dob: Optional[date] = None,
    contact_number: Optional[str] = None,
    nationality: Optional[str] = None,
    height: Optional[str] = None,
    weight: Optional[str] = None,
    blood_group: Optional[str] = None,
    address: Optional[str] = None,
    coach: Optional[str] = None,
    academy: Optional[str] = None,
    avatar_url: Optional[str] = None,
    primary_sport: Optional[str] = "Tennis",
    skill_level: Optional[str] = None,
    emergency_contact_name: Optional[str] = None,
    emergency_contact_phone: Optional[str] = None,
    simulate_init_failure: bool = False,
) -> UserCreationResult:
    """
    Registers a new public user into Baseline Society with explicit intent (User vs Player),
    initializes their personal workspace, supports two-stage onboarding, and enforces strict data isolation.
    """
    import secrets
    from app.domain.constants import (
        calculate_canonical_age_category,
        calculate_profile_completion_percentage,
    )
    from app.services.utils.validation import (
        validate_username, validate_email, validate_password
    )

    username = (username or "").strip()
    email = (email or "").strip().lower()
    intent = (registration_intent or "user").strip().lower()
    if intent not in ("user", "player"):
        intent = "user"

    # 1. Mandatory Fields & Username Validation
    ok, u_clean = validate_username(username)
    if not ok:
        return UserCreationResult(
            success=False,
            message=u_clean or "Invalid username.",
            category="error",
            status_code=400,
        )
    username = u_clean

    # 2. Email Validation
    ok, e_clean = validate_email(email, required=True)
    if not ok:
        return UserCreationResult(
            success=False,
            message=e_clean or "Invalid email address.",
            category="error",
            status_code=400,
        )
    email = e_clean

    # 3. Password Validation & Complexity
    ok, p_clean = validate_password(password, min_length=8)
    if not ok:
        return UserCreationResult(
            success=False,
            message=p_clean or "Password does not meet requirements.",
            category="error",
            status_code=400,
        )

    # 4. Password Confirmation
    if password_confirm is not None:
        if password != password_confirm:
            return UserCreationResult(
                success=False,
                message="Passwords do not match. Please verify your password.",
                category="error",
                status_code=400,
            )

    # 5. Prevent Duplicate Registrations
    if User.query.filter_by(username=username).first():
        return UserCreationResult(
            success=False,
            message="Username already exists.",
            category="error",
            status_code=400,
        )

    if User.query.filter_by(email=email).first():
        return UserCreationResult(
            success=False,
            message="Email already exists.",
            category="error",
            status_code=400,
        )

    # 6. Atomic User & Profile Creation
    try:
        # User account created with explicit intent (default: 'user')
        user = User(
            username=username,
            email=email,
            role=intent,
            registration_intent=intent,
            full_name=full_name.strip() if full_name else None,
            phone_number=contact_number.strip() if contact_number else None,
            email_verification_token=secrets.token_urlsafe(32),
            account_status="ACTIVE",
            profile_completed=False,
            completion_percentage=0,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        actual_user_id = user.id

        # Check for unassigned records with this email or existing data
        unassigned_player = Player.query.filter(
            Player.user_id.is_(None),
            Player.email.ilike(email)
        ).first()

        existing_record_count = check_user_existing_data(actual_user_id)
        if unassigned_player:
            unassigned_player.user_id = actual_user_id
            if full_name:
                unassigned_player.name = full_name.strip()
            if contact_number:
                unassigned_player.contact_number = contact_number.strip()
            existing_record_count += 1

        has_existing_data = existing_record_count > 0

        # Notification Preferences
        prefs = UserNotificationPreferences.query.filter_by(user_id=actual_user_id).first()
        if not prefs:
            prefs = UserNotificationPreferences(user_id=actual_user_id)
            db.session.add(prefs)

        if has_existing_data:
            existing_player = Player.query.filter_by(user_id=actual_user_id).first()
            if existing_player:
                pct_calc = calculate_profile_completion_percentage(
                    user_name=existing_player.name,
                    email=existing_player.email,
                    contact_number=existing_player.contact_number,
                    dob=existing_player.dob,
                    gender=existing_player.gender,
                    primary_sport=existing_player.primary_sport,
                    skill_level=existing_player.skill_level,
                    emergency_contact_name=existing_player.emergency_contact_name,
                    emergency_contact_phone=existing_player.emergency_contact_phone,
                    avatar_url=existing_player.avatar_url,
                    bio=existing_player.bio,
                )
                user.completion_percentage = pct_calc["percentage"]
                user.profile_completed = pct_calc["is_complete"]
                existing_player.profile_status = "complete" if pct_calc["is_complete"] else "incomplete"
        else:
            display_name = full_name.strip() if full_name else username
            current_date = date.today()
            reg_no = f"TP-{current_date.year}-{random.randint(0x1000, 0xFFFF):X}"

            # Calculate canonical age category if dob provided
            canonical_age = calculate_canonical_age_category(dob) if dob else None

            pct_calc = calculate_profile_completion_percentage(
                user_name=display_name,
                email=email,
                contact_number=contact_number,
                dob=dob,
                gender=gender,
                primary_sport=primary_sport,
                skill_level=skill_level,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone,
                avatar_url=avatar_url,
            )

            new_player = Player(
                user_id=actual_user_id,
                name=display_name,
                gender=gender if gender in ('Male', 'Female', 'Other') else None,
                dob=dob,
                email=email,
                contact_number=contact_number.strip() if contact_number else None,
                nationality=nationality.strip() if nationality else None,
                height=height.strip() if height else None,
                weight=weight.strip() if weight else None,
                blood_group=blood_group if blood_group else None,
                address=address.strip() if address else None,
                coach=coach.strip() if coach else None,
                academy=academy.strip() if academy else None,
                avatar_url=avatar_url if avatar_url else None,
                registration_no=reg_no,
                registration_date=current_date,
                registration_validity=current_date + timedelta(days=365),
                current_status="Active",
                age_category=canonical_age,
                profile_status="complete" if pct_calc["is_complete"] else "incomplete",
                primary_sport=primary_sport or "Tennis",
                skill_level=skill_level,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone,
                total_points=0.0,
                matches_played=0,
                matches_won=0,
                matches_lost=0
            )
            db.session.add(new_player)
            user.completion_percentage = pct_calc["percentage"]
            user.profile_completed = pct_calc["is_complete"]

        if simulate_init_failure:
            raise RuntimeError("Simulated profile initialization failure")

        db.session.commit()

        # Verification of Persistence
        reloaded_user = db.session.get(User, actual_user_id)
        if not reloaded_user:
            raise ValueError("User persistence verification failed")

        if has_existing_data:
            return UserCreationResult(
                success=True,
                message=MSG_REGISTRATION_EXISTING_DATA,
                category="success",
                user=user,
                status_code=201,
                has_existing_data=True,
            )
        else:
            return UserCreationResult(
                success=True,
                message=MSG_REGISTRATION_CLEAN_WORKSPACE,
                category="success",
                user=user,
                status_code=201,
                is_clean=True,
            )

    except Exception:
        db.session.rollback()
        return UserCreationResult(
            success=False,
            message=MSG_REGISTRATION_INIT_FAILED,
            category="error",
            status_code=500,
            verification_failed=True,
        )


def complete_player_profile(
    user_id: int,
    full_name: Optional[str] = None,
    dob: Optional[date] = None,
    gender: Optional[str] = None,
    contact_number: Optional[str] = None,
    primary_sport: Optional[str] = "Tennis",
    skill_level: Optional[str] = None,
    emergency_contact_name: Optional[str] = None,
    emergency_contact_phone: Optional[str] = None,
    preferred_competition_category: Optional[str] = None,
    avatar_url: Optional[str] = None,
    bio: Optional[str] = None,
    address: Optional[str] = None,
    height: Optional[str] = None,
    weight: Optional[str] = None,
    blood_group: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Completes or updates a player's profile (Stage 2 onboarding), calculating canonical age
    category, completion score, and updating eligibility flags atomically.
    """
    from app.domain.constants import (
        calculate_canonical_age_category,
        calculate_profile_completion_percentage,
    )

    user = db.session.get(User, user_id)
    if not user:
        return {"success": False, "message": "User not found.", "status_code": 404}

    player = Player.query.filter_by(user_id=user_id).first()
    current_date = date.today()

    if not player:
        # Create player record linked to user
        reg_no = f"TP-{current_date.year}-{random.randint(0x1000, 0xFFFF):X}"
        player = Player(
            user_id=user.id,
            name=(full_name or user.full_name or user.username).strip(),
            email=user.email,
            registration_no=reg_no,
            registration_date=current_date,
            registration_validity=current_date + timedelta(days=365),
            current_status="Active",
        )
        db.session.add(player)

    # Update player profile fields
    if full_name:
        player.name = full_name.strip()
        user.full_name = full_name.strip()

    if contact_number:
        player.contact_number = contact_number.strip()
        user.phone_number = contact_number.strip()

    if dob:
        player.dob = dob
        player.age_category = calculate_canonical_age_category(dob)

    if gender:
        player.gender = gender.strip()

    if primary_sport:
        player.primary_sport = primary_sport.strip()

    if skill_level:
        player.skill_level = skill_level.strip()

    if emergency_contact_name:
        player.emergency_contact_name = emergency_contact_name.strip()

    if emergency_contact_phone:
        player.emergency_contact_phone = emergency_contact_phone.strip()

    if preferred_competition_category:
        player.preferred_competition_category = preferred_competition_category.strip()

    if avatar_url:
        player.avatar_url = avatar_url.strip()

    if bio:
        player.bio = bio.strip()

    if address:
        player.address = address.strip()

    if height:
        player.height = height.strip()

    if weight:
        player.weight = weight.strip()

    if blood_group:
        player.blood_group = blood_group.strip()

    # Calculate completion percentage
    pct_info = calculate_profile_completion_percentage(
        user_name=player.name,
        email=player.email,
        contact_number=player.contact_number,
        dob=player.dob,
        gender=player.gender,
        primary_sport=player.primary_sport,
        skill_level=player.skill_level,
        emergency_contact_name=player.emergency_contact_name,
        emergency_contact_phone=player.emergency_contact_phone,
        avatar_url=player.avatar_url,
        bio=player.bio,
    )

    user.completion_percentage = pct_info["percentage"]
    user.profile_completed = pct_info["is_complete"]
    user.role = "player"  # Upgraded/confirmed as active player
    player.profile_status = "complete" if pct_info["is_complete"] else "incomplete"

    db.session.commit()

    return {
        "success": True,
        "message": "Profile updated successfully.",
        "percentage": pct_info["percentage"],
        "completion_percentage": pct_info["percentage"],
        "is_complete": pct_info["is_complete"],
        "missing_fields": pct_info["missing_fields"],
        "age_category": player.age_category,
        "player": player,
        "user": user,
    }


def verify_user_email(token: str) -> Dict[str, Any]:
    """Verifies a user's email via the verification token."""
    from datetime import datetime
    if not token or not str(token).strip():
        return {"success": False, "message": "Invalid verification token.", "status_code": 400}

    user = User.query.filter_by(email_verification_token=token.strip()).first()
    if not user:
        return {"success": False, "message": "Verification token expired or invalid.", "status_code": 404}

    user.is_email_verified = True
    user.email_verified_at = datetime.utcnow()
    user.email_verification_token = None
    db.session.commit()

    return {"success": True, "message": "Email verified successfully!", "user": user}


def request_password_reset(email: str) -> Dict[str, Any]:
    """Generates a secure password reset token with 1-hour expiration."""
    import secrets
    from datetime import datetime, timedelta

    email = (email or "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        # Prevent user enumeration: Return generic success message
        return {
            "success": True,
            "message": "If an account exists with that email, a password reset link has been dispatched.",
            "token": None
        }

    token = secrets.token_urlsafe(32)
    user.password_reset_token = token
    user.password_reset_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()

    return {
        "success": True,
        "message": "Password reset token generated.",
        "token": token,
        "user": user
    }


def reset_password_with_token(
    token: str,
    new_password: str,
    password_confirm: Optional[str] = None
) -> Dict[str, Any]:
    """Resets user password with token validation and expiration checking."""
    from datetime import datetime
    from app.services.utils.validation import validate_password

    if not token or not str(token).strip():
        return {"success": False, "message": "Invalid reset token.", "status_code": 400}

    if password_confirm is not None and new_password != password_confirm:
        return {"success": False, "message": "Passwords do not match.", "status_code": 400}

    ok, msg = validate_password(new_password, min_length=8)
    if not ok:
        return {"success": False, "message": msg or "Password does not meet complexity requirements.", "status_code": 400}

    user = User.query.filter_by(password_reset_token=token.strip()).first()
    if not user or not user.password_reset_expires_at or user.password_reset_expires_at < datetime.utcnow():
        return {"success": False, "message": "Password reset token has expired or is invalid.", "status_code": 400}

    user.set_password(new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    db.session.commit()

    return {"success": True, "message": "Password has been reset successfully. Please log in.", "user": user}



