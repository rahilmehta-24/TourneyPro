"""
Court Scheduling Engine for TourneyPro.

auto_schedule_category(category_id, start_dt, num_courts, court_names_list, avg_duration_minutes)

Algorithm:
 - Groups matches by round number.
 - Processes rounds sequentially (round N cannot start until round N-1 is estimated done).
 - Within a round, assigns courts in round-robin order.
 - Assigns scheduled_time to each match and saves court_name.
"""

from datetime import datetime, timedelta
from app.models import db, Match, Category, Tournament


def _get_court_names(tournament: Tournament, num_courts: int, custom_names: list | None) -> list:
    """Return a list of court name strings."""
    if custom_names and len(custom_names) >= num_courts:
        return custom_names[:num_courts]
    # Generate generic names
    return [f"Court {i + 1}" for i in range(num_courts)]


def auto_schedule_category(category_id: int) -> dict:
    """
    Schedule all pending matches in a category across its configured courts.

    Returns a dict: {"scheduled": int, "courts": list[str], "end_time": datetime}
    """
    category = Category.query.get_or_404(category_id)
    tournament = Tournament.query.get_or_404(category.tournament_id)
    
    start_dt = category.start_date_time or tournament.started_at or datetime.utcnow()
    num_courts = category.num_courts or 1
    
    court_names_list = None
    if category.court_names:
        court_names_list = [name.strip() for name in category.court_names.split(',') if name.strip()]

    courts = _get_court_names(tournament, num_courts, court_names_list)
    duration = timedelta(minutes=category.avg_match_duration or 60)

    # Fetch all matches for this category that are not yet completed
    matches = (
        Match.query.filter_by(category_id=category_id)
        .filter(Match.status != "completed")
        .order_by(Match.round, Match.match_number)
        .all()
    )

    if not matches:
        return {"scheduled": 0, "courts": courts, "end_time": start_dt}

    # Group matches by round
    rounds: dict[int, list[Match]] = {}
    for m in matches:
        rounds.setdefault(m.round, []).append(m)

    # court_free_at[i] = the datetime when court i is next free
    court_free_at = [start_dt] * len(courts)

    # round_ready_at = earliest time any match in the next round can start
    # (all matches in the previous round must be estimated done)
    round_ready_at = start_dt
    scheduled_count = 0

    for round_num in sorted(rounds.keys()):
        round_matches = rounds[round_num]

        # This round cannot start before round_ready_at
        for i in range(len(courts)):
            if court_free_at[i] < round_ready_at:
                court_free_at[i] = round_ready_at

        for idx, match in enumerate(round_matches):
            court_idx = idx % len(courts)

            match_start = court_free_at[court_idx]
            match.scheduled_time = match_start
            match.court_name = courts[court_idx]

            # Advance this court's free time
            court_free_at[court_idx] = match_start + duration
            scheduled_count += 1

        # Round is considered done when the last match on any court ends
        round_ready_at = max(court_free_at)

    # Persist match assignments
    db.session.commit()

    return {
        "scheduled": scheduled_count,
        "courts": courts,
        "end_time": max(court_free_at),
    }


def get_order_of_play(tournament_slug: str) -> dict:
    """
    Returns a structured Order of Play dict for all scheduled matches in a tournament.

    Structure:
    {
      "Court 1": [
          {"match": Match, "category_name": str, "time": str, "p1": str, "p2": str},
          ...
      ],
      ...
    }
    Sorted by scheduled_time within each court.
    """
    from app.models import Tournament as TournamentModel

    tournament = TournamentModel.query.filter_by(url_slug=tournament_slug).first_or_404()

    # All matches with a scheduled time and court
    matches = (
        Match.query.filter_by(tournament_id=tournament.id)
        .filter(Match.scheduled_time.isnot(None), Match.court_name.isnot(None))
        .order_by(Match.court_name, Match.scheduled_time)
        .all()
    )

    order: dict[str, list] = {}
    for match in matches:
        court = match.court_name
        if court not in order:
            order[court] = []

        cat = Category.query.get(match.category_id)
        cat_name = cat.name if cat else "Unknown Category"

        p1 = match.participant1.name if match.participant1 else "TBD"
        p2 = match.participant2.name if match.participant2 else "TBD"

        order[court].append({
            "match": match,
            "category_name": cat_name,
            "time": match.scheduled_time.strftime("%H:%M") if match.scheduled_time else "TBD",
            "date": match.scheduled_time.strftime("%d %b %Y") if match.scheduled_time else "",
            "p1": p1,
            "p2": p2,
            "round": match.round,
            "match_number": match.match_number,
            "status": match.status,
            "court": court,
        })

    # Sort courts naturally (Court 1, Court 2, ...)
    sorted_order = dict(sorted(order.items()))
    return {"courts": sorted_order, "tournament": tournament}
