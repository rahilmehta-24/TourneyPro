import logging
from datetime import datetime
from typing import Optional, List
from app.domain.models import db, InAppNotification, UserNotificationPreferences, User, Registration, Category, Match, Participant, Player

logger = logging.getLogger(__name__)

NOTIFICATION_TYPE_MATCH_CALL = "match_call"
NOTIFICATION_TYPE_DRAW_PUBLISHED = "draw_published"
NOTIFICATION_TYPE_REGISTRATION_UPDATE = "registration_update"
NOTIFICATION_TYPE_MATCH_RESULT = "match_result"
NOTIFICATION_TYPE_ACADEMY_ANNOUNCEMENT = "academy_announcement"


def send_notification(
    user_id: int,
    title: str,
    body: str,
    notification_type: str,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None
) -> Optional[InAppNotification]:
    """
    Creates an InAppNotification for user_id respecting their UserNotificationPreferences.
    Returns the created InAppNotification, or None if suppressed by preferences or user not found.
    """
    if not user_id:
        return None

    user = User.query.get(user_id)
    if not user:
        return None

    # Check notification preferences if configured
    prefs = UserNotificationPreferences.query.filter_by(user_id=user_id).first()
    if prefs:
        if notification_type == NOTIFICATION_TYPE_MATCH_CALL and not prefs.notify_match_called:
            logger.info("Notification suppressed by user preference: match_call for user %s", user_id)
            return None
        elif notification_type == NOTIFICATION_TYPE_DRAW_PUBLISHED and not prefs.notify_draw_published:
            logger.info("Notification suppressed by user preference: draw_published for user %s", user_id)
            return None
        elif notification_type == NOTIFICATION_TYPE_REGISTRATION_UPDATE and not prefs.notify_registration_updates:
            logger.info("Notification suppressed by user preference: registration_update for user %s", user_id)
            return None
        elif notification_type == NOTIFICATION_TYPE_MATCH_RESULT and not prefs.notify_match_results:
            logger.info("Notification suppressed by user preference: match_result for user %s", user_id)
            return None
        elif notification_type == NOTIFICATION_TYPE_ACADEMY_ANNOUNCEMENT and not prefs.notify_academy_announcements:
            logger.info("Notification suppressed by user preference: academy_announcement for user %s", user_id)
            return None

    notification = InAppNotification(
        user_id=user_id,
        title=title,
        body=body,
        notification_type=notification_type,
        reference_type=reference_type,
        reference_id=reference_id,
        created_at=datetime.utcnow()
    )
    db.session.add(notification)
    return notification


def notify_registration_status(
    registration: Registration,
    status: str,
    reason: Optional[str] = None
) -> Optional[InAppNotification]:
    """
    Dispatches in-app notification when a tournament registration is approved, rejected, or waitlisted.
    """
    if not registration or not registration.user_id:
        return None

    status_lower = status.strip().lower()
    t_name = registration.tournament.name if registration.tournament else "Tournament"
    c_name = registration.category.name if registration.category else "General"

    if status_lower in ("approved", "accepted"):
        title = "Registration Approved! 🎾"
        body = f"Your entry for {t_name} ({c_name}) has been approved."
    elif status_lower in ("rejected", "declined"):
        title = "Registration Update"
        body = f"Your entry for {t_name} ({c_name}) was not accepted: {reason or 'Does not meet category requirements'}"
    elif status_lower == "waitlisted":
        title = "Registration Waitlisted 📋"
        body = f"You are currently on the waitlist for {t_name} ({c_name}). You will be notified if a spot opens."
    else:
        title = "Registration Status Updated"
        body = f"Your entry for {t_name} ({c_name}) status is now: {status}."

    return send_notification(
        user_id=registration.user_id,
        title=title,
        body=body,
        notification_type=NOTIFICATION_TYPE_REGISTRATION_UPDATE,
        reference_type="tournament",
        reference_id=registration.tournament_id
    )


def notify_academy_application_status(
    application,
    status: str,
    reason: Optional[str] = None
) -> Optional[InAppNotification]:
    """
    Dispatches in-app notification when an academy application is reviewed (APPROVED or REJECTED).
    """
    if not application or not application.applicant_id:
        return None

    status_upper = status.strip().upper()
    academy_name = application.name

    if status_upper == "APPROVED":
        title = "Academy Application Approved! 🏛️"
        body = f"Congratulations! Your academy application for '{academy_name}' has been approved and is now active on Baseline."
    elif status_upper == "REJECTED":
        title = "Academy Application Update"
        body = f"Your application for '{academy_name}' was not approved: {reason or 'Does not meet platform requirements'}"
    else:
        title = "Academy Application Status"
        body = f"Your application for '{academy_name}' is currently {status}."

    return send_notification(
        user_id=application.applicant_id,
        title=title,
        body=body,
        notification_type=NOTIFICATION_TYPE_ACADEMY_ANNOUNCEMENT,
        reference_type="academy_application",
        reference_id=application.id
    )


def notify_draw_published(category: Category) -> List[InAppNotification]:
    """
    Dispatches notifications to all approved registrants in a category when draws are published.
    """
    if not category:
        return []

    t_name = category.tournament.name if category.tournament else "Tournament"
    notifications = []

    registrations = Registration.query.filter_by(
        category_id=category.id,
        status="approved"
    ).all()

    for reg in registrations:
        if reg.user_id:
            notif = send_notification(
                user_id=reg.user_id,
                title="Draws Published! 🏆",
                body=f"Draws for {category.name} in {t_name} are now live. View your schedule on Baseline.",
                notification_type=NOTIFICATION_TYPE_DRAW_PUBLISHED,
                reference_type="category",
                reference_id=category.id
            )
            if notif:
                notifications.append(notif)

    return notifications


def notify_match_called(match: Match, court_name: Optional[str] = None) -> List[InAppNotification]:
    """
    Dispatches notifications to competitors when their match is called to a court.
    """
    if not match:
        return []

    notifications = []
    court_str = f" to {court_name}" if court_name else (f" to {match.court_name}" if match.court_name else "")
    c_name = match.category.name if match.category else "your event"

    for p_id in [match.participant1_id, match.participant2_id]:
        if not p_id:
            continue
        participant = Participant.query.get(p_id)
        if not participant:
            continue

        player_ids = [participant.player_id]
        if participant.player2_id:
            player_ids.append(participant.player2_id)

        for pl_id in player_ids:
            if not pl_id:
                continue
            player = Player.query.get(pl_id)
            if player and player.user_id:
                notif = send_notification(
                    user_id=player.user_id,
                    title="Match Called! 🎾",
                    body=f"Your match in {c_name} has been called{court_str}. Please report to the court promptly.",
                    notification_type=NOTIFICATION_TYPE_MATCH_CALL,
                    reference_type="match",
                    reference_id=match.id
                )
                if notif:
                    notifications.append(notif)

    return notifications
