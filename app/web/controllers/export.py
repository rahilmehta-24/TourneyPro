import csv
import io
import logging
from datetime import datetime
from flask import Blueprint, make_response, abort, redirect, url_for, flash, request
from slugify import slugify

from app.domain.models import Tournament, Category, Match, Group
from app.web.controllers.auth import login_required, role_required, check_tournament_ownership
from app.services.pdf.draw_adapter import DrawExportAdapter
from app.services.pdf.order_of_play_adapter import OrderOfPlayExportAdapter
from app.services.pdf.pdf_generator import DrawPdfService

logger = logging.getLogger(__name__)

export_bp = Blueprint("export", __name__)


def get_category_winners(category):
    winners = []
    if category.status != "completed":
        return winners

    if category.format in ["round_robin", "group_stage"]:
        if category.format == "group_stage":
            return []
        else:
            standings = category.get_standings()
            if len(standings) > 0:
                winners.append({"place": "1st", "name": standings[0].name})
            if len(standings) > 1:
                winners.append({"place": "2nd", "name": standings[1].name})
            if len(standings) > 2:
                winners.append({"place": "3rd", "name": standings[2].name})
    else:
        matches = Match.query.filter_by(category_id=category.id).all()
        if not matches:
            return winners

        max_round = max([m.round for m in matches])
        final_matches = [m for m in matches if m.round == max_round]
        final_match = sorted(final_matches, key=lambda m: m.match_number, reverse=True)[0]

        if final_match and final_match.winner_id:
            p1 = final_match.participant1
            p2 = final_match.participant2

            if final_match.winner_id == p1.id:
                winners.append({"place": "1st", "name": p1.name})
                winners.append({"place": "2nd", "name": p2.name if p2 else "Unknown"})
            else:
                winners.append({"place": "1st", "name": p2.name if p2 else "Unknown"})
                winners.append({"place": "2nd", "name": p1.name})

    return winners


@export_bp.route("/tournaments/<slug>/category/<int:category_id>/export_pdf")
@export_bp.route("/tournaments/<slug>/category/<int:category_id>/export_draw_pdf")
@export_bp.route("/tournaments/<slug>/categories/<int:category_id>/export_pdf")
@export_bp.route("/tournaments/<slug>/categories/<int:category_id>/export_draw_pdf")
@export_bp.route("/t/<slug>/categories/<int:category_id>/export_pdf")
@export_bp.route("/t/<slug>/categories/<int:category_id>/export_draw_pdf")
@login_required
@role_required("admin", "superadmin")
def export_category_pdf(slug, category_id):
    """
    Retrieve the existing saved Single Elimination draw, populate the template,
    and return a downloadable PDF.
    Read-only: Never regenerates, reseeds, advances, or mutates database state.
    """
    slug = slug.strip()
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)

    # Validate tournament/category association
    if category.tournament_id != tournament.id:
        abort(404)

    # Enforce strict authorization and tournament ownership
    check_tournament_ownership(tournament)

    # Verify that a saved draw exists in the database
    matches = Match.query.filter(
        Match.category_id == category.id,
        Match.match_type == "knockout",
        Match.parent_match_id.is_(None),
    ).all()

    if not matches or category.status == "setup":
        flash(
            "The tournament draw has not been generated yet. "
            "Please start the category to generate the draw before exporting.",
            "warning",
        )
        return redirect(url_for("category.view_category", slug=slug, category_id=category_id))

    try:
        # Load and adapt the existing saved draw (read-only)
        draw_data = DrawExportAdapter.adapt(tournament, category)
        pdf_buffer = DrawPdfService.render_draw_pdf(draw_data)
    except Exception as e:
        logger.error(f"Error exporting draw PDF for category {category_id}: {e}", exc_info=True)
        flash("An error occurred while generating the draw PDF.", "danger")
        return redirect(url_for("category.view_category", slug=slug, category_id=category_id))

    # Sanitize filename to prevent path traversal or invalid characters
    safe_tournament = slugify(tournament.name, separator="_") or f"tournament_{tournament.id}"
    safe_category = slugify(category.name, separator="_") or f"category_{category.id}"
    filename = f"tourneypro_{safe_tournament}_{safe_category}_draw.pdf"

    response = make_response(pdf_buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@export_bp.route("/t/<slug>/order-of-play/export_pdf")
@export_bp.route("/tournaments/<slug>/order-of-play/export_pdf")
def export_order_of_play_pdf(slug):
    """
    Retrieve and format the existing Order of Play schedule for a tournament,
    render the static template, and return a downloadable PDF.
    Read-only: Never regenerates, reschedules, or mutates database state.
    """
    slug = slug.strip()
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    # Parse optional filter arguments
    date_param = request.args.get("date")
    filter_date = None
    if date_param:
        try:
            filter_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            pass

    selected_court = request.args.get("court") or None
    session_filter = request.args.get("session", "all")
    if session_filter not in ("all", "day", "evening"):
        session_filter = "all"

    try:
        oop_data = OrderOfPlayExportAdapter.adapt(
            tournament=tournament,
            filter_date=filter_date,
            selected_court=selected_court,
            session_filter=session_filter,
        )
        pdf_buffer = DrawPdfService.render_order_of_play_pdf(oop_data)
    except Exception as e:
        logger.error(f"Error exporting Order of Play PDF for tournament {slug}: {e}", exc_info=True)
        flash("An error occurred while generating the Order of Play PDF.", "danger")
        return redirect(url_for("tournament.order_of_play", slug=slug, date=date_param or ""))

    # Build safe, sanitized download filename
    safe_tournament = slugify(tournament.name, separator="_") or f"tournament_{tournament.id}"
    date_suffix = filter_date.strftime("%Y%m%d") if filter_date else "full"
    court_suffix = f"_{slugify(selected_court, separator='_')}" if selected_court else ""
    session_suffix = f"_{session_filter}" if session_filter in ("day", "evening") else ""
    filename = f"tourneypro_{safe_tournament}_order_of_play_{date_suffix}{court_suffix}{session_suffix}.pdf"

    response = make_response(pdf_buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@export_bp.route("/tournaments/<slug>/category/<int:category_id>/export_matches_csv")
@export_bp.route("/tournaments/<slug>/categories/<int:category_id>/export_matches_csv")
@export_bp.route("/t/<slug>/categories/<int:category_id>/export_matches_csv")
def export_matches_csv(slug, category_id):
    slug = slug.strip()
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)

    if category.tournament_id != tournament.id:
        abort(404)

    si = io.StringIO()
    writer = csv.writer(si)

    writer.writerow(["Round", "Match Number", "Status", "Player 1", "Player 2", "Score", "Winner"])

    matches = (
        Match.query.filter_by(category_id=category.id)
        .order_by(Match.round, Match.match_number)
        .all()
    )
    for match in matches:
        p1_name = match.participant1.name if match.participant1 else "TBD"
        p2_name = match.participant2.name if match.participant2 else "TBD"

        score = ""
        if match.score1 or match.score2:
            score = f"{match.score1 or '0'} - {match.score2 or '0'}"

        winner_name = ""
        if match.winner_id:
            if match.winner_id == match.participant1_id:
                winner_name = p1_name
            elif match.winner_id == match.participant2_id:
                winner_name = p2_name

        writer.writerow(
            [match.round, match.match_number, match.status, p1_name, p2_name, score, winner_name]
        )

    safe_tournament = slugify(tournament.name, separator="_") or f"tournament_{tournament.id}"
    safe_category = slugify(category.name, separator="_") or f"category_{category.id}"
    filename = f"{safe_tournament}_{safe_category}_Matches.csv"

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    output.headers["Content-type"] = "text/csv"
    return output


@export_bp.route("/tournaments/<slug>/category/<int:category_id>/export_standings_csv")
@export_bp.route("/tournaments/<slug>/categories/<int:category_id>/export_standings_csv")
@export_bp.route("/t/<slug>/categories/<int:category_id>/export_standings_csv")
def export_standings_csv(slug, category_id):
    slug = slug.strip()
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)

    if category.tournament_id != tournament.id:
        abort(404)

    if category.format not in ["round_robin", "group_stage"]:
        abort(400, "Standings export is only available for Round Robin and Group Stage formats.")

    si = io.StringIO()
    writer = csv.writer(si)

    groups_data = []
    if category.format == "group_stage":
        groups = Group.query.filter_by(category_id=category.id).order_by(Group.name).all()
        for group in groups:
            groups_data.append({"name": group.name, "standings": group.get_standings()})
    else:
        groups_data.append({"name": "Standings", "standings": category.get_standings()})

    for group in groups_data:
        writer.writerow([f"--- {group['name']} ---"])
        writer.writerow(
            [
                "Rank",
                "Player",
                "Played",
                "Won",
                "Lost",
                "Points For",
                "Points Against",
                "Points Diff",
            ]
        )

        for idx, p in enumerate(group["standings"]):
            writer.writerow(
                [
                    idx + 1,
                    p.name,
                    p.matches_played,
                    p.matches_won,
                    p.matches_lost,
                    p.points_for,
                    p.points_against,
                    p.points_difference,
                ]
            )
        writer.writerow([])

    safe_tournament = slugify(tournament.name, separator="_") or f"tournament_{tournament.id}"
    safe_category = slugify(category.name, separator="_") or f"category_{category.id}"
    filename = f"{safe_tournament}_{safe_category}_Standings.csv"

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    output.headers["Content-type"] = "text/csv"
    return output
