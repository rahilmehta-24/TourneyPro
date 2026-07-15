"""Live score polling API endpoint."""
from flask import jsonify
from app.models import Match, Tournament
from app.api import api_bp


@api_bp.route('/live/<slug>/scores')
def live_scores(slug):
    """
    Returns current scores for all matches in a tournament as JSON.
    Called by the frontend every 5 seconds for live score updates.
    """
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    matches = Match.query.filter_by(tournament_id=tournament.id).all()

    data = []
    for m in matches:
        data.append({
            "id": m.id,
            "status": m.status,
            "score1": m.score1 or "",
            "score2": m.score2 or "",
            "winner_id": m.winner_id,
            "p1": m.participant1.name if m.participant1 else "TBD",
            "p2": m.participant2.name if m.participant2 else "TBD",
            "court": m.court_name or "",
            "scheduled_time": m.scheduled_time.strftime("%H:%M") if m.scheduled_time else "",
        })

    return jsonify({"matches": data, "tournament": slug})
