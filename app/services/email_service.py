import logging
import os
import smtplib
import threading
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from typing import List, Optional, Union
from flask import current_app, render_template, has_request_context

logger = logging.getLogger(__name__)


def _render_email_template(template_name: str, **context) -> str:
    """
    Renders an HTML email template safely whether inside an HTTP request
    or from a background thread/task.
    """
    if has_request_context():
        return render_template(template_name, **context)
    with current_app.test_request_context():
        return render_template(template_name, **context)


def _get_base_url() -> str:
    """
    Returns the public base URL for links in email notifications.
    Falls back gracefully from config/env to request.host_url or https://the-baseline-society.vercel.app.
    """
    config_base = current_app.config.get("BASE_URL") if current_app else None
    if config_base:
        return config_base.rstrip("/")
    env_base = os.environ.get("BASE_URL") or os.environ.get("APP_URL")
    if env_base:
        return env_base.rstrip("/")
    if has_request_context():
        from flask import request

        proto = request.headers.get("X-Forwarded-Proto") or request.scheme
        return f"{proto}://{request.host}".rstrip("/")
    return "https://the-baseline-society.vercel.app"


def _send_smtp_message(
    to_emails: List[str],
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    reply_to: Optional[str] = None,
    from_sender: Optional[str] = None,
    config: Optional[dict] = None,
    instance_path: Optional[str] = None,
):
    """
    Worker function to send an email via SMTP or save to dev previews.
    Designed to safely execute in a background thread or synchronously.
    """
    config = config or {}
    mail_server = config.get("MAIL_SERVER")
    mail_port = int(config.get("MAIL_PORT") or 587)
    mail_use_tls = config.get("MAIL_USE_TLS", True)
    mail_use_ssl = config.get("MAIL_USE_SSL", False)
    mail_username = (config.get("MAIL_USERNAME") or "").strip() or None
    mail_password = (config.get("MAIL_PASSWORD") or "").strip() or None
    if mail_password and " " in mail_password and mail_server and "gmail" in mail_server.lower():
        mail_password = mail_password.replace(" ", "")
    default_sender = config.get("MAIL_DEFAULT_SENDER") or "The Baseline Society <confirmation@thebaselinesociety.com>"
    mail_sender = from_sender or default_sender
    suppress_send = config.get("MAIL_SUPPRESS_SEND", False)

    # Clean recipients
    valid_recipients = [e.strip() for e in to_emails if e and e.strip()]
    if not valid_recipients:
        logger.warning("[EmailService] No valid recipient addresses provided. Skipping send.")
        return False

    # Development fallback or Suppressed: Save preview file and log
    if suppress_send or not mail_server or mail_server in ["localhost", "127.0.0.1", "none"]:
        logger.info(
            "[EmailService] Dev Mode / Suppress Send active. Simulating email to: %s | Subject: %s",
            valid_recipients,
            subject,
        )
        try:
            if instance_path:
                preview_dir = os.path.join(instance_path, "email_previews")
                os.makedirs(preview_dir, exist_ok=True)
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                safe_recip = valid_recipients[0].replace("@", "_at_").replace(".", "_")
                filename = f"{timestamp}_{safe_recip}.html"
                preview_file = os.path.join(preview_dir, filename)
                with open(preview_file, "w", encoding="utf-8") as f:
                    f.write(html_body)
                logger.info("[EmailService] Saved email HTML preview to: %s", preview_file)
        except Exception as e:
            logger.warning("[EmailService] Could not write preview file: %s", e)
        return True

    # Real SMTP Delivery
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = mail_sender
        msg["To"] = ", ".join(valid_recipients)
        if reply_to:
            msg["Reply-To"] = reply_to

        # Plain text alternative
        plain_text = text_body or f"{subject}\n\nPlease view this email with an HTML-capable email viewer."
        msg.set_content(plain_text)
        msg.add_alternative(html_body, subtype="html")

        if mail_use_ssl:
            with smtplib.SMTP_SSL(mail_server, mail_port, timeout=15) as server:
                if mail_username and mail_password:
                    server.login(mail_username, mail_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(mail_server, mail_port, timeout=15) as server:
                if mail_use_tls:
                    server.starttls()
                if mail_username and mail_password:
                    server.login(mail_username, mail_password)
                server.send_message(msg)

        logger.info("[EmailService] Successfully dispatched email to %s (Subject: %s)", valid_recipients, subject)
        return True
    except Exception as e:
        logger.error("[EmailService] Failed to send email to %s: %s", valid_recipients, e, exc_info=True)
        return False


def send_email(
    to_email: Union[str, List[str]],
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    reply_to: Optional[str] = None,
    from_sender: Optional[str] = None,
    async_send: bool = True,
) -> bool:
    """
    Sends an HTML email to one or more recipients with proper error isolation and async support.
    """
    if isinstance(to_email, str):
        to_emails = [to_email]
    else:
        to_emails = list(to_email)

    config_dict = {
        "MAIL_SERVER": current_app.config.get("MAIL_SERVER"),
        "MAIL_PORT": current_app.config.get("MAIL_PORT"),
        "MAIL_USE_TLS": current_app.config.get("MAIL_USE_TLS"),
        "MAIL_USE_SSL": current_app.config.get("MAIL_USE_SSL"),
        "MAIL_USERNAME": current_app.config.get("MAIL_USERNAME"),
        "MAIL_PASSWORD": current_app.config.get("MAIL_PASSWORD"),
        "MAIL_DEFAULT_SENDER": current_app.config.get("MAIL_DEFAULT_SENDER"),
        "MAIL_SUPPRESS_SEND": current_app.config.get("MAIL_SUPPRESS_SEND"),
    }
    instance_path = current_app.instance_path

    if async_send:
        thread = threading.Thread(
            target=_send_smtp_message,
            args=(to_emails, subject, html_body, text_body, reply_to, from_sender, config_dict, instance_path),
            daemon=True,
        )
        thread.start()
        return True
    else:
        return _send_smtp_message(
            to_emails=to_emails,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            reply_to=reply_to,
            from_sender=from_sender,
            config=config_dict,
            instance_path=instance_path,
        )


def notify_registration_created(registration_id: int, async_send: bool = True) -> dict:
    """
    Dispatches 3 targeted notifications upon tournament registration:
    1. Player Confirmation (with Organizer's direct contact as Reply-To)
    2. Organizer Alert (with Player's direct contact as Reply-To to connect)
    3. Superadmin Audit Alert (platform-wide monitoring)
    """
    from app.domain.models import db, Registration, User

    reg = db.session.get(Registration, registration_id)
    if not reg:
        logger.error("[EmailService] Registration ID %s not found for email notification", registration_id)
        return {"status": "error", "message": "Registration not found"}

    tournament = reg.tournament
    category = reg.category
    player = reg.player
    user = reg.user

    # Resolve Player details
    player_name = player.name if player else (user.full_name or user.username if user else "Competitor")
    player_email = player.email if (player and player.email) else (user.email if user else None)
    player_phone = (
        player.contact_number
        if (player and player.contact_number)
        else (getattr(user, "phone_number", None) if user else "")
    )

    # Resolve Organizer details
    organizer = db.session.get(User, tournament.user_id) if tournament.user_id else None
    organizer_name = organizer.full_name or organizer.username or tournament.creator_name or "Tournament Organizer"
    organizer_email = organizer.email if (organizer and organizer.email) else None
    organizer_phone = getattr(organizer, "phone_number", "") if organizer else ""

    # Resolve Superadmin emails
    superadmins = User.query.filter_by(role="superadmin").all()
    superadmin_emails = [s.email for s in superadmins if s.email]
    env_superadmin = current_app.config.get("SUPERADMIN_EMAIL") or "rahilmehta.ict19@gmail.com"
    if env_superadmin and env_superadmin not in superadmin_emails:
        superadmin_emails.append(env_superadmin)

    results = {"player": False, "organizer": False, "superadmin": False}

    # Safe URL construction pointing to the live tournament page
    base_url = _get_base_url()
    tournament_url = f"{base_url}/tournaments/{tournament.url_slug}"
    manage_url = f"{base_url}/tournaments/{tournament.url_slug}/manage"
    admin_url = f"{base_url}/admin"

    # Context shared across templates
    base_context = {
        "tournament": tournament,
        "category": category,
        "registration": reg,
        "player_name": player_name,
        "player_email": player_email,
        "player_phone": player_phone,
        "partner_name": reg.partner_name,
        "partner_mobile": reg.partner_mobile,
        "organizer_name": organizer_name,
        "organizer_email": organizer_email,
        "organizer_phone": organizer_phone,
        "amount_due": reg.amount_due,
        "payment_status": reg.payment_status or "pending",
        "payment_method": reg.payment_method or "online",
        "registration_status": reg.status or "pending",
        "registered_at": reg.created_at.strftime("%b %d, %Y, %I:%M %p") if reg.created_at else "",
        "tournament_url": tournament_url,
        "manage_url": manage_url,
        "admin_url": admin_url,
    }

    # Masked sender: Organizer Name as display name under confirmation@thebaselinesociety.com
    confirmation_email_addr = (
        current_app.config.get("MAIL_CONFIRMATION_EMAIL") or "confirmation@thebaselinesociety.com"
    )
    organizer_masked_sender = formataddr((f"{organizer_name}", confirmation_email_addr))

    # 1. Send Player Confirmation
    if player_email:
        try:
            player_html = _render_email_template("emails/player_registration_confirmation.html", **base_context)
            results["player"] = send_email(
                to_email=player_email,
                subject=f"Registration Confirmed: {tournament.name} 🎾",
                html_body=player_html,
                reply_to=organizer_email,
                from_sender=organizer_masked_sender,
                async_send=async_send,
            )
        except Exception as e:
            logger.error("[EmailService] Failed rendering/sending player confirmation email: %s", e)

    # 2. Send Organizer Alert
    if organizer_email:
        try:
            organizer_html = _render_email_template("emails/organizer_registration_alert.html", **base_context)
            results["organizer"] = send_email(
                to_email=organizer_email,
                subject=f"New Registration: {tournament.name} ({player_name})",
                html_body=organizer_html,
                reply_to=player_email,
                async_send=async_send,
            )
        except Exception as e:
            logger.error("[EmailService] Failed rendering/sending organizer alert email: %s", e)

    # 3. Send Superadmin Platform Alert
    if superadmin_emails:
        try:
            superadmin_html = _render_email_template("emails/superadmin_registration_alert.html", **base_context)
            results["superadmin"] = send_email(
                to_email=superadmin_emails,
                subject=f"[System Audit] New Registration: {tournament.name} - {player_name}",
                html_body=superadmin_html,
                async_send=async_send,
            )
        except Exception as e:
            logger.error("[EmailService] Failed rendering/sending superadmin alert email: %s", e)

    return {"status": "success", "results": results}


def notify_registration_status_update(
    registration_id: int, status: str, reason: Optional[str] = None, async_send: bool = True
) -> bool:
    """
    Sends an email update to the player when their registration is approved, rejected, or updated.
    """
    from app.domain.models import db, Registration, User

    reg = db.session.get(Registration, registration_id)
    if not reg:
        return False

    player = reg.player
    user = reg.user
    player_email = player.email if (player and player.email) else (user.email if user else None)
    if not player_email:
        return False

    tournament = reg.tournament
    category = reg.category
    player_name = player.name if player else (user.full_name or "Competitor")

    organizer = db.session.get(User, tournament.user_id) if tournament.user_id else None
    organizer_email = organizer.email if (organizer and organizer.email) else None
    organizer_name = organizer.full_name or organizer.username or "Tournament Director"

    status_lower = status.strip().lower()
    if status_lower in ("approved", "accepted"):
        status_title = "Registration Approved! 🏆"
        subtitle = f"Great news! Your entry for {tournament.name} ({category.name if category else 'General'}) has been approved."
        status_color = "#047857"
    elif status_lower in ("rejected", "declined"):
        status_title = "Registration Update"
        subtitle = f"Your entry for {tournament.name} was not accepted: {reason or 'Category capacity or criteria not met.'}"
        status_color = "#DC2626"
    else:
        status_title = f"Registration Status: {status}"
        subtitle = f"Your entry status for {tournament.name} has been updated to: {status}."
        status_color = "#C9A55C"

    base_url = _get_base_url()
    tournament_url = f"{base_url}/tournaments/{tournament.url_slug}"

    context = {
        "tournament": tournament,
        "category": category,
        "registration": reg,
        "player_name": player_name,
        "organizer_name": organizer_name,
        "organizer_email": organizer_email,
        "status_title": status_title,
        "subtitle": subtitle,
        "status_color": status_color,
        "status_badge": status.upper(),
        "amount_due": reg.amount_due,
        "payment_status": reg.payment_status or "pending",
        "reason": reason,
        "tournament_url": tournament_url,
    }

    confirmation_email_addr = (
        current_app.config.get("MAIL_CONFIRMATION_EMAIL") or "confirmation@thebaselinesociety.com"
    )
    organizer_masked_sender = formataddr((f"{organizer_name}", confirmation_email_addr))

    try:
        html = _render_email_template("emails/player_registration_confirmation.html", **context)
        return send_email(
            to_email=player_email,
            subject=f"{status_title} - {tournament.name}",
            html_body=html,
            reply_to=organizer_email,
            from_sender=organizer_masked_sender,
            async_send=async_send,
        )
    except Exception as e:
        logger.error("[EmailService] Failed sending status update email: %s", e)
        return False

