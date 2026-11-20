"""
Canonical Constants and Domain Enums for Baseline Society
"""

from datetime import date
from typing import Optional, Tuple, Dict, Any

COMPETITION_CATEGORIES: Tuple[str, ...] = (
    "Men's Singles",
    "Women's Singles",
    "Boys' Singles",
    "Girls' Singles",
    "Men's Doubles",
    "Women's Doubles",
    "Mixed Doubles",
    "Boys' Doubles",
    "Girls' Doubles",
    "Team Event",
)

AGE_CATEGORIES: Tuple[str, ...] = (
    "Under 8",
    "Under 10",
    "Under 12",
    "Under 14",
    "Under 16",
    "Under 18",
    "Under 21",
    "Open",
    "Veterans 35+",
    "Veterans 40+",
    "Veterans 45+",
    "Veterans 50+",
    "Veterans 55+",
    "Veterans 60+",
)

VALID_GENDERS: Tuple[str, ...] = (
    "Male",
    "Female",
    "Other",
)

VALID_SPORTS: Tuple[str, ...] = (
    "Tennis",
    "Pickleball",
    "Badminton",
    "Padel",
    "Table Tennis",
    "Squash",
)

VALID_SKILL_LEVELS: Tuple[str, ...] = (
    "Beginner",
    "Intermediate",
    "Advanced",
    "Pro",
)

# ---------------------------------------------------------------------------
# Playing Format Statuses & Tournament Registration Statuses
# ---------------------------------------------------------------------------
FORMAT_STATUS_NOT_DECIDED = "NOT_DECIDED"
FORMAT_STATUS_FINALIZED = "FINALIZED"

FORMAT_STATUSES: Tuple[str, ...] = (
    FORMAT_STATUS_NOT_DECIDED,
    FORMAT_STATUS_FINALIZED,
)

REGISTRATION_STATUS_DRAFT = "DRAFT"
REGISTRATION_STATUS_UPCOMING = "UPCOMING"
REGISTRATION_STATUS_OPEN = "OPEN"
REGISTRATION_STATUS_CLOSED = "CLOSED"

REGISTRATION_STATUSES: Tuple[str, ...] = (
    REGISTRATION_STATUS_DRAFT,
    REGISTRATION_STATUS_UPCOMING,
    REGISTRATION_STATUS_OPEN,
    REGISTRATION_STATUS_CLOSED,
)

IMPORT_STATUS_PENDING = "PENDING_CONFIRMATION"
IMPORT_STATUS_COMPLETED = "COMPLETED"
IMPORT_STATUS_FAILED = "FAILED"
IMPORT_STATUS_PARTIAL = "PARTIAL"

# ---------------------------------------------------------------------------
# Platform, Academy & Tournament Roles and Permissions
# ---------------------------------------------------------------------------

# 1. Platform Roles
PLATFORM_ROLE_SUPERADMIN = "superadmin"
PLATFORM_ROLE_SUPPORT = "support"
PLATFORM_ROLE_USER = "user"

PLATFORM_ROLES: Tuple[str, ...] = (
    PLATFORM_ROLE_SUPERADMIN,
    PLATFORM_ROLE_SUPPORT,
    PLATFORM_ROLE_USER,
)

# 2. Academy Roles
ACADEMY_ROLE_OWNER = "owner"
ACADEMY_ROLE_ADMIN = "admin"
ACADEMY_ROLE_HEAD_COACH = "head_coach"
ACADEMY_ROLE_COACH = "coach"
ACADEMY_ROLE_MEMBER = "member"

ACADEMY_ROLES: Tuple[str, ...] = (
    ACADEMY_ROLE_OWNER,
    ACADEMY_ROLE_ADMIN,
    ACADEMY_ROLE_HEAD_COACH,
    ACADEMY_ROLE_COACH,
    ACADEMY_ROLE_MEMBER,
)

# 3. Tournament Roles
TOURNAMENT_ROLE_OWNER = "owner"
TOURNAMENT_ROLE_DIRECTOR = "director"
TOURNAMENT_ROLE_MANAGER = "manager"
TOURNAMENT_ROLE_DRAW_ADMIN = "draw_admin"
TOURNAMENT_ROLE_REFEREE = "referee"
TOURNAMENT_ROLE_SCORER = "scorer"
TOURNAMENT_ROLE_PARTICIPANT = "participant"
TOURNAMENT_ROLE_VIEWER = "viewer"

TOURNAMENT_ROLES: Tuple[str, ...] = (
    TOURNAMENT_ROLE_OWNER,
    TOURNAMENT_ROLE_DIRECTOR,
    TOURNAMENT_ROLE_MANAGER,
    TOURNAMENT_ROLE_DRAW_ADMIN,
    TOURNAMENT_ROLE_REFEREE,
    TOURNAMENT_ROLE_SCORER,
    TOURNAMENT_ROLE_PARTICIPANT,
    TOURNAMENT_ROLE_VIEWER,
)

# Standard Scoped Permission Strings
PERM_PLATFORM_ACADEMIES_VERIFY = "platform.academies.verify"
PERM_PLATFORM_ACADEMIES_VIEW = "platform.academies.view"
PERM_PLATFORM_USERS_VIEW = "platform.users.view"
PERM_PLATFORM_USERS_MANAGE = "platform.users.manage"
PERM_PLATFORM_AUDIT_VIEW = "platform.audit.view"
PERM_PLATFORM_CONFIG_MANAGE = "platform.config.manage"

PERM_ACADEMY_VIEW = "academy.view"
PERM_ACADEMY_MANAGE = "academy.manage"
PERM_ACADEMY_MEMBERS_VIEW = "academy.members.view"
PERM_ACADEMY_MEMBERS_MANAGE = "academy.members.manage"
PERM_ACADEMY_COACHES_ASSIGN = "academy.coaches.assign"

PERM_TOURNAMENT_CREATE = "tournament.create"
PERM_TOURNAMENT_VIEW = "tournament.view"
PERM_TOURNAMENT_MANAGE = "tournament.manage"
PERM_TOURNAMENT_DRAW_MANAGE = "tournament.draw.manage"
PERM_TOURNAMENT_REGISTRATION_REVIEW = "tournament.registration.review"
PERM_TOURNAMENT_SCORE_SUBMIT = "tournament.score.submit"
PERM_TOURNAMENT_RESULTS_PUBLISH = "tournament.results.publish"
PERM_TOURNAMENT_PARTICIPANTS_IMPORT = "tournament.participants.import"


def calculate_canonical_age_category(
    dob: Optional[date],
    reference_year: Optional[int] = None,
    tournament_year: Optional[int] = None
) -> str:
    """
    Calculates the player's canonical age category based on the December 31st calendar
    year cutoff convention: (reference_year - birth_year), matching ITF/Olympic standards.
    """
    if not dob:
        return "Open"

    ref_year = reference_year or tournament_year
    if ref_year is None:
        ref_year = date.today().year

    age = ref_year - dob.year

    if age <= 8:
        return "Under 8"
    elif age <= 10:
        return "Under 10"
    elif age <= 12:
        return "Under 12"
    elif age <= 14:
        return "Under 14"
    elif age <= 16:
        return "Under 16"
    elif age <= 18:
        return "Under 18"
    elif age <= 21:
        return "Under 21"
    elif age < 35:
        return "Open"
    elif age < 40:
        return "Veterans 35+"
    elif age < 45:
        return "Veterans 40+"
    elif age < 50:
        return "Veterans 45+"
    elif age < 55:
        return "Veterans 50+"
    elif age < 60:
        return "Veterans 55+"
    else:
        return "Veterans 60+"


def get_eligible_age_categories(dob: Optional[date], reference_year: Optional[int] = None) -> Tuple[str, ...]:
    """
    Returns all canonical age categories a player is eligible to compete in.
    Juniors can play in their natural bracket and play up into older brackets & Open.
    Veterans can play in their bracket and down into younger Veteran brackets & Open.
    """
    if not dob:
        return ("Open",)

    if reference_year is None:
        reference_year = date.today().year

    age = reference_year - dob.year
    eligible = []

    # Junior age brackets: eligible if age < max_age
    junior_limits = [
        ("Under 8", 8),
        ("Under 10", 10),
        ("Under 12", 12),
        ("Under 14", 14),
        ("Under 16", 16),
        ("Under 18", 18),
        ("Under 21", 21),
    ]
    for cat_name, limit in junior_limits:
        if age < limit:
            eligible.append(cat_name)

    # Open category is always open to anyone of eligible playing age
    eligible.append("Open")

    # Veterans categories: eligible if age >= min_age
    veteran_limits = [
        ("Veterans 35+", 35),
        ("Veterans 40+", 40),
        ("Veterans 45+", 45),
        ("Veterans 50+", 50),
        ("Veterans 55+", 55),
        ("Veterans 60+", 60),
    ]
    for cat_name, min_age in veteran_limits:
        if age >= min_age:
            eligible.append(cat_name)

    return tuple(eligible)


def calculate_profile_completion_percentage(
    user_name: Optional[str] = None,
    email: Optional[str] = None,
    contact_number: Optional[str] = None,
    dob: Optional[date] = None,
    gender: Optional[str] = None,
    primary_sport: Optional[str] = None,
    skill_level: Optional[str] = None,
    emergency_contact_name: Optional[str] = None,
    emergency_contact_phone: Optional[str] = None,
    avatar_url: Optional[str] = None,
    bio: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculates weighted profile completion percentage (0-100%) and returns breakdown:
    - Core Account Details (30%): Name (10%), Email (10%), Phone (10%)
    - Athletic Eligibility (35%): Verified DOB (20%), Gender (15%)
    - Sport & Skill Details (20%): Primary Sport (10%), Skill Level (10%)
    - Profile Enrichment (15%): Emergency Contact (10%), Bio/Avatar (5%)
    """
    score = 0
    missing_fields = []

    # Core (30%)
    if user_name and str(user_name).strip():
        score += 10
    else:
        missing_fields.append("Full Name")

    if email and str(email).strip():
        score += 10
    else:
        missing_fields.append("Email Address")

    if contact_number and str(contact_number).strip():
        score += 10
    else:
        missing_fields.append("Contact Phone Number")

    # Eligibility (35%)
    if dob:
        score += 20
    else:
        missing_fields.append("Date of Birth")

    if gender and str(gender).strip() in VALID_GENDERS:
        score += 15
    else:
        missing_fields.append("Gender")

    # Sport & Skill (20%)
    if primary_sport and str(primary_sport).strip():
        score += 10
    else:
        missing_fields.append("Primary Sport")

    if skill_level and str(skill_level).strip() in VALID_SKILL_LEVELS:
        score += 10
    else:
        missing_fields.append("Skill Level")

    # Emergency & Safety Contact (15%)
    if emergency_contact_name and emergency_contact_phone:
        score += 15
    elif emergency_contact_name or emergency_contact_phone:
        score += 8
        missing_fields.append("Emergency Contact Phone" if not emergency_contact_phone else "Emergency Contact Name")
    else:
        missing_fields.append("Emergency Contact")

    if (avatar_url and str(avatar_url).strip()) or (bio and str(bio).strip()):
        score += 5

    # Required competitor eligibility criteria:
    # Full Name, Email, Phone, DOB, Gender, Primary Sport, Emergency Contact
    is_competitor_ready = (
        bool(user_name and str(user_name).strip()) and
        bool(email and str(email).strip()) and
        bool(contact_number and str(contact_number).strip()) and
        bool(dob) and
        bool(gender and str(gender).strip() in VALID_GENDERS) and
        bool(primary_sport and str(primary_sport).strip()) and
        bool(emergency_contact_name and str(emergency_contact_name).strip()) and
        bool(emergency_contact_phone and str(emergency_contact_phone).strip())
    )

    return {
        "percentage": min(score, 100),
        "is_complete": is_competitor_ready,
        "missing_fields": missing_fields,
    }
