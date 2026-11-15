"""
User Service — User Creation, Workspace Initialization & Persistence Verification
The Baseline Society
"""

import random
from datetime import date, datetime, timedelta
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

    if role not in ("superadmin", "admin", "user", "player"):
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

