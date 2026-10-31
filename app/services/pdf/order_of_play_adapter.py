"""Order of Play Presentation Adapter for TourneyPro PDF Export.

Transforms structured scheduler data into a clean, normalized, presentation-ready
format for static Jinja2 PDF templates.
Read-only: Performs zero database writes or mutations.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.domain.models import Tournament, Match
from app.services.utils.scheduler import get_order_of_play


class OrderOfPlayExportAdapter:
    """Adapter to prepare Order of Play data for high-density, professional PDF rendering."""

    @classmethod
    def format_match_score(cls, match_obj: Any) -> Optional[str]:
        """Format the match score string."""
        if not match_obj:
            return None

        # Check direct score string
        score_attr = getattr(match_obj, "score", None)
        if score_attr and str(score_attr).strip():
            return str(score_attr).strip()

        s1 = getattr(match_obj, "score1", None)
        s2 = getattr(match_obj, "score2", None)
        s1_str = str(s1).strip() if s1 is not None else ""
        s2_str = str(s2).strip() if s2 is not None else ""

        if not s1_str and not s2_str:
            return None

        if s1_str and s2_str and "-" not in s1_str and "-" not in s2_str:
            return f"{s1_str} – {s2_str}"
        elif s1_str and s2_str:
            return f"{s1_str} – {s2_str}"
        return s1_str or s2_str

    @classmethod
    def format_participant_display(
        cls, participant: Any, player_list: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Format participant name with seeds and doubles partner handling."""
        if not participant:
            return {"name": "TBD", "seed": None, "is_team": False}

        seed = getattr(participant, "manual_seed", None) or getattr(participant, "seed", None)
        p_name = getattr(participant, "name", "") or "TBD"
        is_team = getattr(participant, "participant_type", None) == "team"

        # If individual players are provided for doubles
        if not is_team and player_list and len(player_list) > 1:
            names = [p.get("name") for p in player_list if p.get("name")]
            if names:
                p_name = " & ".join(names)

        return {"name": p_name, "seed": seed, "is_team": is_team}

    @classmethod
    def adapt(
        cls,
        tournament: Tournament,
        filter_date: Optional[date] = None,
        selected_court: Optional[str] = None,
        session_filter: str = "all",
    ) -> Dict[str, Any]:
        """
        Produce a presentation structure for the Order of Play PDF.
        """
        raw_oop = get_order_of_play(tournament.url_slug, filter_date=filter_date)

        active_date = raw_oop.get("active_date")
        if isinstance(active_date, str):
            try:
                active_date = datetime.strptime(active_date, "%Y-%m-%d").date()
            except ValueError:
                active_date = None

        active_date_str = (
            active_date.strftime("%A, %d %B %Y") if active_date else "Tournament Schedule"
        )
        day_number = raw_oop.get("current_day_number", 1)
        total_days = len(raw_oop.get("unique_dates", [])) or 1
        day_label = f"Day {day_number} of {total_days}" if total_days > 1 else f"Day {day_number}"

        venue = None
        if tournament.academy and tournament.academy.name:
            venue = tournament.academy.name
        elif tournament.game_info:
            venue = tournament.game_info

        courts_dict = raw_oop.get("courts", {})
        processed_courts: List[Dict[str, Any]] = []

        total_matches_in_pdf = 0
        total_day_matches = 0
        total_eve_matches = 0

        # Sort courts naturally
        sorted_court_names = sorted(courts_dict.keys())

        for c_name in sorted_court_names:
            if selected_court and selected_court != c_name:
                continue

            court_schedule = courts_dict[c_name]
            # court_schedule has .day_matches, .evening_matches, .matches
            if session_filter == "day":
                target_matches = court_schedule.day_matches
            elif session_filter == "evening":
                target_matches = court_schedule.evening_matches
            else:
                target_matches = court_schedule.matches

            match_rows: List[Dict[str, Any]] = []
            for order_idx, m_dict in enumerate(target_matches, start=1):
                match_obj: Match = m_dict.get("match")

                # Format matchup
                p1_info = cls.format_participant_display(
                    getattr(match_obj, "participant1", None), m_dict.get("p1_players")
                )
                p2_info = cls.format_participant_display(
                    getattr(match_obj, "participant2", None), m_dict.get("p2_players")
                )

                # Format score
                score_str = cls.format_match_score(match_obj)
                status = getattr(match_obj, "status", "pending")
                winner_id = getattr(match_obj, "winner_id", None)

                p1_is_winner = bool(
                    status == "completed" and winner_id and match_obj.participant1_id == winner_id
                )
                p2_is_winner = bool(
                    status == "completed" and winner_id and match_obj.participant2_id == winner_id
                )

                # Child rubbers (for team league fixtures)
                rubbers: List[Dict[str, Any]] = []
                if match_obj and m_dict.get("has_rubbers") and match_obj.sub_matches:
                    for sub in sorted(
                        match_obj.sub_matches, key=lambda s: getattr(s, "rubber_number", 0)
                    ):
                        r_lbl = (
                            "Singles"
                            if sub.rubber_type == "singles"
                            else ("Doubles 1" if sub.rubber_type == "doubles_1" else "Doubles 2")
                        )
                        r_p1 = [p for p in [sub.p1_player1, sub.p1_player2] if p]
                        r_p2 = [p for p in [sub.p2_player1, sub.p2_player2] if p]
                        r_p1_name = (
                            " & ".join(p.name for p in r_p1)
                            if r_p1
                            else (match_obj.participant1.name if match_obj.participant1 else "TBD")
                        )
                        r_p2_name = (
                            " & ".join(p.name for p in r_p2)
                            if r_p2
                            else (match_obj.participant2.name if match_obj.participant2 else "TBD")
                        )
                        r_score = cls.format_match_score(sub)
                        r_w1 = bool(
                            sub.status == "completed"
                            and sub.winner_id
                            and sub.winner_id == sub.participant1_id
                        )
                        r_w2 = bool(
                            sub.status == "completed"
                            and sub.winner_id
                            and sub.winner_id == sub.participant2_id
                        )

                        rubbers.append(
                            {
                                "label": r_lbl,
                                "p1_name": r_p1_name,
                                "p2_name": r_p2_name,
                                "p1_winner": r_w1,
                                "p2_winner": r_w2,
                                "score": r_score,
                                "status": sub.status,
                            }
                        )

                is_eve = m_dict.get("session") == "evening"
                if is_eve:
                    total_eve_matches += 1
                else:
                    total_day_matches += 1
                total_matches_in_pdf += 1

                match_rows.append(
                    {
                        "order_number": order_idx,
                        "time": m_dict.get("time", "TBD"),
                        "is_not_before": m_dict.get("is_not_before", False),
                        "session": m_dict.get("session", "day"),
                        "category_name": m_dict.get("category_name", "Category"),
                        "round_name": m_dict.get("round_name", "Match"),
                        "group_name": m_dict.get("group_name"),
                        "p1": p1_info,
                        "p2": p2_info,
                        "p1_is_winner": p1_is_winner,
                        "p2_is_winner": p2_is_winner,
                        "score": score_str,
                        "status": status,
                        "is_team": m_dict.get("is_team", False),
                        "rubbers": rubbers,
                    }
                )

            processed_courts.append(
                {
                    "court_name": c_name,
                    "matches": match_rows,
                    "total_count": len(match_rows),
                    "day_count": sum(1 for m in match_rows if m["session"] == "day"),
                    "evening_count": sum(1 for m in match_rows if m["session"] == "evening"),
                }
            )

        return {
            "tournament_name": tournament.name,
            "tournament_slug": tournament.url_slug,
            "venue": venue,
            "active_date": active_date,
            "active_date_str": active_date_str,
            "day_number": day_number,
            "day_label": day_label,
            "operating_hours": f"{raw_oop.get('active_day_start', '09:00')} – {raw_oop.get('active_day_end', '19:00')}",
            "day_session_start": raw_oop.get("active_day_start", "09:00"),
            "evening_session_start": raw_oop.get("evening_session_start", "16:00"),
            "is_provisional": raw_oop.get("is_provisional", False),
            "earlier_pending_count": raw_oop.get("earlier_pending_count", 0),
            "previous_day_label": raw_oop.get("previous_day_label", "Day 1"),
            "selected_court": selected_court,
            "session_filter": session_filter,
            "courts": processed_courts,
            "total_matches": total_matches_in_pdf,
            "total_day_matches": total_day_matches,
            "total_evening_matches": total_eve_matches,
            "generated_at": datetime.now().strftime("%d %b %Y, %H:%M"),
        }
