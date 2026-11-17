"""
Academy Management & Verification Service
The Baseline Society
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import and_
from app import db
from app.domain.models import Academy, AcademyMember, AcademyApplication, User, AuditLog, Registration
from app.domain.constants import (
    PERM_PLATFORM_ACADEMIES_VERIFY,
    PERM_ACADEMY_MEMBERS_MANAGE,
    ACADEMY_ROLE_OWNER,
    ACADEMY_ROLE_ADMIN,
    ACADEMY_ROLE_MEMBER,
)
from app.services.rbac_service import has_permission


def _generate_academy_slug(name: str) -> str:
    """Generates a URL-safe, collision-free slug for an academy."""
    base_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    if not base_slug:
        base_slug = "academy"
    slug = base_slug
    counter = 1
    while Academy.query.filter_by(url_slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def submit_academy_application(user_id: int, data: Dict[str, Any]) -> AcademyApplication:
    """
    Submits a new academy application for platform superadmin review.
    Enforces that applicant cannot have an existing pending application or active academy ownership.
    """
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError("Authenticated applicant user not found.")

    # 1. Check for pending application
    existing_pending = AcademyApplication.query.filter_by(
        applicant_id=user_id,
        status="PENDING"
    ).first()
    if existing_pending:
        raise ValueError("You already have an academy application pending review.")

    # 2. Check if user already owns an active academy
    existing_owned = Academy.query.filter_by(
        owner_id=user_id,
        status="ACTIVE"
    ).first()
    if existing_owned:
        raise ValueError(f"You already own an active academy ({existing_owned.name}).")

    name = (data.get("name") or "").strip()
    if not name or len(name) < 3:
        raise ValueError("Academy name must be at least 3 characters long.")

    contact_email = (data.get("contact_email") or user.email or "").strip().lower()
    if not contact_email or "@" not in contact_email:
        raise ValueError("A valid contact email is required.")

    application = AcademyApplication(
        applicant_id=user_id,
        name=name,
        description=data.get("description", "").strip(),
        address=data.get("address", "").strip(),
        city=data.get("city", "").strip(),
        state=data.get("state", "").strip(),
        country=data.get("country", "").strip(),
        contact_email=contact_email,
        contact_phone=data.get("contact_phone", "").strip(),
        sports_offered=data.get("sports_offered", "").strip(),
        website_url=data.get("website_url", "").strip(),
        status="PENDING",
        created_at=datetime.utcnow()
    )
    db.session.add(application)
    db.session.flush()

    audit = AuditLog(
        user_id=user_id,
        action_type="ACADEMY_APPLICATION_SUBMITTED",
        target_id=application.id,
        target_name=application.name,
        reason="Academy verification application submitted",
        explanation=f"Applicant {user.username} submitted academy application for '{name}'"
    )
    db.session.add(audit)
    db.session.commit()

    return application


def review_academy_application(
    application_id: int,
    reviewer_user: User,
    decision: str,
    rejection_reason: Optional[str] = None
) -> Tuple[AcademyApplication, Optional[Academy]]:
    """
    Platform Superadmin reviews an academy application.
    - If APPROVED: Creates active Academy and appoints applicant as Academy Owner.
    - If REJECTED: Mandatory rejection reason stored, applicant receives no admin rights.
    """
    if not has_permission(reviewer_user, PERM_PLATFORM_ACADEMIES_VERIFY):
        raise PermissionError("Only Platform Superadmins can verify academy applications.")

    decision_norm = decision.strip().upper()
    if decision_norm not in ("APPROVED", "REJECTED"):
        raise ValueError("Decision must be either 'APPROVED' or 'REJECTED'.")

    app_record = db.session.get(AcademyApplication, application_id)
    if not app_record:
        raise ValueError("Academy application not found.")

    if app_record.status != "PENDING":
        raise ValueError(f"Application has already been reviewed (current status: {app_record.status}).")

    if decision_norm == "REJECTED":
        reason = (rejection_reason or "").strip()
        if not reason:
            raise ValueError("A rejection reason is mandatory when declining an application.")

        app_record.status = "REJECTED"
        app_record.rejection_reason = reason
        app_record.reviewed_by_id = reviewer_user.id
        app_record.reviewed_at = datetime.utcnow()

        audit = AuditLog(
            user_id=reviewer_user.id,
            action_type="ACADEMY_APPLICATION_REJECTED",
            target_id=app_record.id,
            target_name=app_record.name,
            reason="Platform Superadmin rejected application",
            explanation=f"Rejection reason: {reason}"
        )
        db.session.add(audit)

        # Notify applicant
        try:
            from app.services.notification_service import notify_academy_application_status
            notify_academy_application_status(app_record, "REJECTED", reason)
        except Exception:
            pass

        db.session.commit()
        return app_record, None

    # APPROVED Branch
    slug = _generate_academy_slug(app_record.name)
    academy = Academy(
        name=app_record.name,
        url_slug=slug,
        description=app_record.description,
        owner_id=app_record.applicant_id,
        status="ACTIVE",
        address=app_record.address,
        city=app_record.city,
        state=app_record.state,
        country=app_record.country,
        contact_email=app_record.contact_email,
        contact_phone=app_record.contact_phone,
        sports_offered=app_record.sports_offered,
        website_url=app_record.website_url,
        verified_at=datetime.utcnow(),
        verified_by_id=reviewer_user.id,
        created_at=datetime.utcnow()
    )
    db.session.add(academy)
    db.session.flush()

    # Enforce Single Active Membership rule: de-activate any existing active membership for applicant
    existing_memberships = AcademyMember.query.filter_by(
        user_id=app_record.applicant_id,
        membership_status="ACTIVE"
    ).all()
    for em in existing_memberships:
        em.membership_status = "TRANSFERRED"
        em.left_at = datetime.utcnow()

    # Create Owner membership in the new verified academy
    owner_member = AcademyMember(
        academy_id=academy.id,
        user_id=app_record.applicant_id,
        role=ACADEMY_ROLE_OWNER,
        membership_status="ACTIVE",
        joined_at=datetime.utcnow()
    )
    db.session.add(owner_member)

    # Update application
    app_record.status = "APPROVED"
    app_record.academy_id = academy.id
    app_record.reviewed_by_id = reviewer_user.id
    app_record.reviewed_at = datetime.utcnow()

    audit = AuditLog(
        user_id=reviewer_user.id,
        action_type="ACADEMY_APPLICATION_APPROVED",
        target_id=academy.id,
        target_name=academy.name,
        reason="Platform Superadmin approved application",
        explanation=f"Academy '{academy.name}' activated with slug '{slug}' for owner {app_record.applicant.username}"
    )
    db.session.add(audit)

    # Notify applicant
    try:
        from app.services.notification_service import notify_academy_application_status
        notify_academy_application_status(app_record, "APPROVED")
    except Exception:
        pass

    db.session.commit()

    return app_record, academy


def get_user_active_academy_membership(user_id: int) -> Optional[AcademyMember]:
    """Retrieves the single active academy membership for the user, if one exists."""
    return AcademyMember.query.filter_by(
        user_id=user_id,
        membership_status="ACTIVE"
    ).first()


def add_academy_member(
    academy_id: int,
    user_id: int,
    role: str = ACADEMY_ROLE_MEMBER,
    acting_user: Optional[User] = None
) -> AcademyMember:
    """
    Enrolls a user into an academy.
    Strictly enforces Single Active Academy Membership:
    If user already has an ACTIVE membership in ANY academy, the operation is blocked.
    """
    academy = db.session.get(Academy, academy_id)
    if not academy or academy.status != "ACTIVE":
        raise ValueError("Target academy does not exist or is not active.")

    if acting_user:
        scope = {"academy_id": academy.id, "academy": academy}
        if not has_permission(acting_user, PERM_ACADEMY_MEMBERS_MANAGE, scope=scope):
            raise PermissionError("You do not have permission to manage members for this academy.")

    user = db.session.get(User, user_id)
    if not user:
        raise ValueError("User not found.")

    # 1. Check existing active membership across ALL academies
    active_membership = get_user_active_academy_membership(user_id)
    if active_membership:
        if active_membership.academy_id == academy_id:
            # Already active in this academy
            return active_membership
        other_academy = db.session.get(Academy, active_membership.academy_id)
        other_name = other_academy.name if other_academy else f"Academy #{active_membership.academy_id}"
        raise ValueError(
            f"User '{user.username}' is already an active member of '{other_name}'. "
            "A formal transfer or departure is required before joining another academy."
        )

    # 2. Check if user previously had an inactive membership in this academy
    existing_in_target = AcademyMember.query.filter_by(
        academy_id=academy_id,
        user_id=user_id
    ).first()

    if existing_in_target:
        existing_in_target.membership_status = "ACTIVE"
        existing_in_target.role = role
        existing_in_target.left_at = None
        db.session.commit()
        return existing_in_target

    # 3. Create fresh active membership
    new_member = AcademyMember(
        academy_id=academy_id,
        user_id=user_id,
        role=role,
        membership_status="ACTIVE",
        joined_at=datetime.utcnow()
    )
    db.session.add(new_member)

    if acting_user:
        audit = AuditLog(
            user_id=acting_user.id,
            action_type="ACADEMY_MEMBER_ADDED",
            target_id=academy_id,
            target_name=academy.name,
            reason="Added member to academy",
            explanation=f"Added {user.username} as {role}"
        )
        db.session.add(audit)

    db.session.commit()
    return new_member


def transfer_user_academy_membership(
    user_id: int,
    target_academy_id: int,
    acting_user: Optional[User] = None,
    new_role: str = ACADEMY_ROLE_MEMBER,
    reason: str = "Player requested transfer"
) -> AcademyMember:
    """
    Transactionally transfers a user from their current active academy to a target active academy.
    Historical tournament registrations remain intact and retain their historical academy snapshot.
    """
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError("User not found.")

    target_academy = db.session.get(Academy, target_academy_id)
    if not target_academy or target_academy.status != "ACTIVE":
        raise ValueError("Target academy does not exist or is not active.")

    current_membership = get_user_active_academy_membership(user_id)
    if current_membership and current_membership.academy_id == target_academy_id:
        return current_membership

    # 1. Deactivate current active membership
    source_name = "None"
    if current_membership:
        source_academy = db.session.get(Academy, current_membership.academy_id)
        source_name = source_academy.name if source_academy else f"Academy #{current_membership.academy_id}"
        current_membership.membership_status = "TRANSFERRED"
        current_membership.left_at = datetime.utcnow()

    # 2. Activate in target academy
    existing_in_target = AcademyMember.query.filter_by(
        academy_id=target_academy_id,
        user_id=user_id
    ).first()

    if existing_in_target:
        existing_in_target.membership_status = "ACTIVE"
        existing_in_target.role = new_role
        existing_in_target.left_at = None
        new_membership = existing_in_target
    else:
        new_membership = AcademyMember(
            academy_id=target_academy_id,
            user_id=user_id,
            role=new_role,
            membership_status="ACTIVE",
            joined_at=datetime.utcnow()
        )
        db.session.add(new_membership)

    audit_user_id = acting_user.id if acting_user else user_id
    audit = AuditLog(
        user_id=audit_user_id,
        action_type="ACADEMY_MEMBERSHIP_TRANSFERRED",
        target_id=target_academy_id,
        target_name=target_academy.name,
        reason=reason,
        explanation=f"Transferred user '{user.username}' from '{source_name}' to '{target_academy.name}'"
    )
    db.session.add(audit)
    db.session.commit()

    return new_membership


def leave_academy_membership(user_id: int, academy_id: int) -> None:
    """Sets the user's active membership in the specified academy to INACTIVE."""
    membership = AcademyMember.query.filter_by(
        academy_id=academy_id,
        user_id=user_id,
        membership_status="ACTIVE"
    ).first()
    if not membership:
        raise ValueError("No active membership found in this academy.")

    membership.membership_status = "INACTIVE"
    membership.left_at = datetime.utcnow()

    audit = AuditLog(
        user_id=user_id,
        action_type="ACADEMY_MEMBERSHIP_LEFT",
        target_id=academy_id,
        target_name=membership.academy.name if membership.academy else "Academy",
        reason="User left academy",
        explanation=f"User ID {user_id} left academy ID {academy_id}"
    )
    db.session.add(audit)
    db.session.commit()
