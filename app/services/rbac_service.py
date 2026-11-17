"""
Role-Based Access Control (RBAC) & Scoped Permission Evaluator
The Baseline Society
"""

from typing import Optional, Dict, Any, Callable
from functools import wraps
from flask import abort, session, has_request_context
from app import db
from app.domain.models import User, Tournament, TournamentStaff, Academy, AcademyMember, Match, Player
from app.domain.constants import (
    PLATFORM_ROLE_SUPERADMIN,
    PLATFORM_ROLE_SUPPORT,
    PERM_PLATFORM_ACADEMIES_VIEW,
    PERM_PLATFORM_USERS_VIEW,
    PERM_ACADEMY_VIEW,
    PERM_ACADEMY_MEMBERS_VIEW,
    PERM_ACADEMY_COACHES_ASSIGN,
    PERM_TOURNAMENT_CREATE,
    PERM_TOURNAMENT_VIEW,
    PERM_TOURNAMENT_DRAW_MANAGE,
    PERM_TOURNAMENT_SCORE_SUBMIT,
)


def has_permission(
    user: Optional[User],
    permission: str,
    scope: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Evaluates whether the given user has the requested permission within the given resource scope.
    Enforces strict layer isolation: Platform != Academy != Tournament.
    """
    scope = scope or {}

    # Public permissions
    if permission in (PERM_TOURNAMENT_VIEW, PERM_ACADEMY_VIEW):
        return True

    if not user:
        return False

    # 1. Platform Superadmin: Universal platform governance
    if user.role == PLATFORM_ROLE_SUPERADMIN:
        return True

    # 2. Platform Support: Purpose-limited platform assistance
    if user.role == PLATFORM_ROLE_SUPPORT:
        allowed_support_perms = {
            PERM_PLATFORM_USERS_VIEW,
            PERM_PLATFORM_ACADEMIES_VIEW,
            PERM_TOURNAMENT_VIEW,
            PERM_ACADEMY_VIEW,
        }
        # Explicit boundary: Support CANNOT verify academies, override scores, or delete users
        return permission in allowed_support_perms

    # 3. Platform-level permissions for standard users
    if permission.startswith("platform."):
        # Standard users and academy roles have 0 platform permissions
        return False

    # 4. Tournament Creation: Superadmin, Academy Owner/Admin, or activated organizer
    if permission == PERM_TOURNAMENT_CREATE:
        if user.role in ("admin", "superadmin"):
            return True
        # Check if user owns or admins an active academy
        academy = Academy.query.filter_by(owner_id=user.id).first()
        if academy and academy.status == "ACTIVE":
            return True
        membership = AcademyMember.query.filter_by(user_id=user.id).first()
        if membership and membership.role in ("owner", "admin"):
            return True
        return False

    # 5. Academy Scope Evaluation
    if permission.startswith("academy."):
        academy_id = scope.get("academy_id")
        academy = scope.get("academy")
        if not academy and academy_id:
            academy = db.session.get(Academy, academy_id)

        if not academy:
            # If no specific academy scope provided, check if user has role in ANY academy
            if permission in (PERM_ACADEMY_MEMBERS_VIEW, PERM_ACADEMY_VIEW):
                return True
            return False

        # Owner has full academy permissions
        if academy.owner_id == user.id:
            return True

        membership = AcademyMember.query.filter_by(
            academy_id=academy.id,
            user_id=user.id
        ).first()

        if not membership or getattr(membership, 'membership_status', 'ACTIVE') != 'ACTIVE':
            return False

        if membership.role in ("owner", "admin"):
            return True

        if membership.role in ("head_coach", "coach"):
            if permission in (PERM_ACADEMY_MEMBERS_VIEW, PERM_ACADEMY_VIEW):
                return True
            if permission == PERM_ACADEMY_COACHES_ASSIGN and membership.role == "head_coach":
                return True
            return False

        if membership.role == "member":
            return permission in (PERM_ACADEMY_MEMBERS_VIEW, PERM_ACADEMY_VIEW)

        return False

    # 6. Tournament Scope Evaluation
    if permission.startswith("tournament."):
        tournament_id = scope.get("tournament_id")
        tournament = scope.get("tournament")
        if not tournament and tournament_id:
            tournament = db.session.get(Tournament, tournament_id)

        if not tournament:
            return False

        # Tournament Owner has full management access
        if tournament.user_id == user.id:
            return True

        # Check TournamentStaff role
        staff = TournamentStaff.query.filter_by(
            tournament_id=tournament.id,
            user_id=user.id
        ).first()

        if not staff:
            return False

        staff_role = staff.role.lower()

        # Manager / Director
        if staff_role in ("director", "manager", "tournament_admin"):
            return True

        # Draw Administrator
        if staff_role == "draw_admin":
            return permission in (PERM_TOURNAMENT_DRAW_MANAGE, PERM_TOURNAMENT_VIEW)

        # Referee / Scorer / Umpire
        if staff_role in ("official", "scorer", "referee", "desk", "umpire"):
            return permission in (PERM_TOURNAMENT_SCORE_SUBMIT, PERM_TOURNAMENT_VIEW)

        return False

    return False


def check_scoring_conflict_of_interest(match: Match, user: Optional[User]) -> None:
    """
    Anti-Conflict-of-Interest Defense:
    Strictly forbids any user who is an active participant in a match (or child rubber)
    from scoring, updating, or finalizing that match, EVEN IF they are the tournament owner,
    admin, or official.
    """
    if not user:
        return  # Court PIN sessions are not linked to a personal player account

    player_user_ids = set()

    def add_participant_user_ids(part):
        if not part:
            return
        for pid in (getattr(part, 'player_id', None), getattr(part, 'player2_id', None)):
            if pid:
                p = db.session.get(Player, pid)
                if p and p.user_id:
                    player_user_ids.add(p.user_id)
        if hasattr(part, 'team_members') and part.team_members:
            for tm in part.team_members:
                tm_pid = getattr(tm, 'player_id', None) or (tm.player.id if getattr(tm, 'player', None) else None)
                if tm_pid:
                    p = db.session.get(Player, tm_pid)
                    if p and p.user_id:
                        player_user_ids.add(p.user_id)

    add_participant_user_ids(match.participant1)
    add_participant_user_ids(match.participant2)

    for pid_attr in ('p1_player1_id', 'p1_player2_id', 'p2_player1_id', 'p2_player2_id'):
        pid = getattr(match, pid_attr, None)
        if pid:
            p = db.session.get(Player, pid)
            if p and p.user_id:
                player_user_ids.add(p.user_id)

    if user.id in player_user_ids:
        raise PermissionError(
            "Conflict of interest: You are an active participant in this match. "
            "Scores must be entered by an impartial official, court umpire, or tournament organizer."
        )


def check_scoring_authorization(
    match: Match,
    user: Optional[User] = None,
    tournament: Optional[Tournament] = None
) -> bool:
    """
    Verifies full authorization to record or alter scores:
    1. Caller must have tournament.score.submit permission (or active Court PIN session).
    2. Caller must NOT have a conflict of interest in this match.
    """
    tourney = tournament or match.tournament

    # 1. Check temporary Court PIN session
    if has_request_context():
        pin_session_key = f"court_pin_staff_{tourney.id}"
        if pin_session_key in session:
            pin_data = session[pin_session_key]
            staff = db.session.get(TournamentStaff, pin_data.get("staff_id"))
            if staff and staff.tournament_id == tourney.id:
                from datetime import datetime
                if not staff.pin_expires_at or staff.pin_expires_at > datetime.utcnow():
                    # Neutral umpire session - conflict check unnecessary as not a user account
                    return True
                else:
                    session.pop(pin_session_key, None)

    # 2. Check user permission
    if not user:
        abort(401)

    scope = {"tournament": tourney, "tournament_id": tourney.id}
    if not has_permission(user, PERM_TOURNAMENT_SCORE_SUBMIT, scope=scope):
        abort(403)

    # 3. Check conflict of interest
    check_scoring_conflict_of_interest(match, user)

    return True


def require_permission(permission: str, scope_getter: Optional[Callable] = None):
    """
    Decorator for Flask route handlers to enforce fine-grained permissions.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app.web.controllers.auth import get_current_user
            user = get_current_user()
            if not user:
                abort(401)

            scope = scope_getter(*args, **kwargs) if scope_getter else {}
            if not has_permission(user, permission, scope=scope):
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator
