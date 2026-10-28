"""Participants Presentation Adapter for TourneyPro PDF Export.

Transforms tournament participants and registration data into a clean, normalized,
presentation-ready format for static Jinja2 PDF templates.
Read-only: Performs zero database writes or mutations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from app.domain.models import db, Tournament, Category, Participant, Registration


class ParticipantsExportAdapter:
    """Adapter to prepare Tournament Participants data for high-density, professional PDF rendering."""

    TAG_PALETTES = [
        {"bg": "#e0f2fe", "text": "#0369a1", "border": "#7dd3fc"},  # Sky Blue
        {"bg": "#dcfce7", "text": "#15803d", "border": "#86efac"},  # Emerald Green
        {"bg": "#fef3c7", "text": "#b45309", "border": "#fcd34d"},  # Amber / Orange
        {"bg": "#f3e8ff", "text": "#7e22ce", "border": "#d8b4fe"},  # Purple
        {"bg": "#ffe4e6", "text": "#be123c", "border": "#fda4af"},  # Rose / Coral
        {"bg": "#e0e7ff", "text": "#4338ca", "border": "#a5b4fc"},  # Indigo
        {"bg": "#ccfbf1", "text": "#0f766e", "border": "#5eead4"},  # Teal
        {"bg": "#fae8ff", "text": "#a21caf", "border": "#f0abfc"},  # Fuchsia
    ]

    FORMAT_DISPLAY_MAP = {
        "single_elimination": "Knockout (Single Elimination)",
        "doubles_elimination": "Doubles Knockout",
        "double_elimination": "Double Elimination",
        "group_stage": "Group Stage + Knockouts League",
        "round_robin": "Round Robin (League)",
        "doubles_round_robin": "Doubles Round Robin (League)",
    }

    @classmethod
    def format_dates(cls, tournament: Tournament) -> str:
        """Format tournament start and end dates nicely."""
        if not tournament.start_date:
            return "Dates: TBD"
        s_str = tournament.start_date.strftime("%d %b %Y")
        if not tournament.end_date or tournament.start_date == tournament.end_date:
            return s_str
        e_str = tournament.end_date.strftime("%d %b %Y")
        return f"{s_str} – {e_str}"

    @classmethod
    def resolve_payment_badge(
        cls,
        participant: Optional[Participant],
        registration: Optional[Registration],
        entry_fee: Optional[float] = None,
    ) -> Dict[str, str]:
        """
        Format payment method strictly as 'Online' or 'Cash' (or 'Free') with appropriate status.
        Explicitly excludes all transaction IDs and bank reference codes.
        """
        method_raw = ""
        status_raw = ""

        if participant:
            method_raw = (participant.payment_method or "").strip().lower()
            status_raw = (participant.payment_status or "").strip().lower()

        if not method_raw and registration:
            method_raw = (registration.payment_method or "").strip().lower()
            if not status_raw:
                status_raw = (registration.payment_status or "").strip().lower()

        # Check for free / zero entry fee
        if method_raw in ["free", "complimentary"] or (entry_fee is not None and entry_fee == 0.0):
            return {
                "label": "Free",
                "badge_class": "badge-free",
                "is_paid": True,
            }

        if method_raw == "online":
            if status_raw == "paid":
                return {
                    "label": "Online - Paid",
                    "badge_class": "badge-online",
                    "is_paid": True,
                }
            elif status_raw == "pending":
                return {
                    "label": "Online - Pending",
                    "badge_class": "badge-pending",
                    "is_paid": False,
                }
            return {
                "label": "Online",
                "badge_class": "badge-online",
                "is_paid": True,
            }

        if method_raw == "cash":
            if status_raw == "paid":
                return {
                    "label": "Cash - Paid",
                    "badge_class": "badge-cash",
                    "is_paid": True,
                }
            elif status_raw == "pending":
                return {
                    "label": "Cash - Pending",
                    "badge_class": "badge-pending",
                    "is_paid": False,
                }
            return {
                "label": "Cash",
                "badge_class": "badge-cash",
                "is_paid": True,
            }

        # Default fallback
        if status_raw == "paid":
            return {
                "label": "Cash - Paid",
                "badge_class": "badge-cash",
                "is_paid": True,
            }
        return {
            "label": "Pending",
            "badge_class": "badge-pending",
            "is_paid": False,
        }

    @classmethod
    def adapt(cls, tournament: Tournament) -> Dict[str, Any]:
        """
        Query and format tournament participants, payment methods, and multi-category tags.
        """
        # Fetch categories in consistent order
        categories = (
            Category.query.filter_by(tournament_id=tournament.id).order_by(Category.id).all()
        )

        # Build consistent color palette map per category
        cat_palette_map: Dict[int, Dict[str, str]] = {}
        category_by_id: Dict[int, Category] = {}
        for idx, cat in enumerate(categories):
            category_by_id[cat.id] = cat
            palette = cls.TAG_PALETTES[idx % len(cls.TAG_PALETTES)]
            cat_palette_map[cat.id] = palette

        # Fetch all registrations for this tournament with player joined to avoid N+1 queries
        registrations = (
            Registration.query.options(db.joinedload(Registration.player))
            .filter_by(tournament_id=tournament.id)
            .all()
        )
        reg_by_cat_and_player: Dict[tuple, Registration] = {}
        for reg in registrations:
            if reg.category_id:
                reg_by_cat_and_player[(reg.category_id, reg.player_id)] = reg
                if reg.partner_mobile:
                    reg_by_cat_and_player[(reg.category_id, reg.partner_mobile.strip())] = reg

        # Step 1: Build multi-category index across the tournament
        # We identify players by player_id, contact mobile, or normalized name
        player_to_category_ids: Dict[str, Set[int]] = {}

        def register_player_category(player_key: str, cat_id: int):
            if not player_key:
                return
            if player_key not in player_to_category_ids:
                player_to_category_ids[player_key] = set()
            player_to_category_ids[player_key].add(cat_id)

        all_participants = (
            Participant.query.options(
                db.joinedload(Participant.player), db.joinedload(Participant.group)
            )
            .filter_by(tournament_id=tournament.id)
            .order_by(Participant.category_id, Participant.seed, Participant.id)
            .all()
        )

        for p in all_participants:
            if not p.category_id:
                continue
            if p.player_id:
                register_player_category(f"pid_{p.player_id}", p.category_id)
            if p.mobile:
                clean_m = p.mobile.strip()
                if clean_m:
                    register_player_category(f"mob_{clean_m}", p.category_id)
            if p.name:
                clean_n = p.name.strip().lower()
                register_player_category(f"name_{clean_n}", p.category_id)

        # Also index registrations so cross-registered categories appear even if pending
        for reg in registrations:
            if not reg.category_id:
                continue
            if reg.player_id:
                register_player_category(f"pid_{reg.player_id}", reg.category_id)
            if reg.player and reg.player.contact_number:
                register_player_category(
                    f"mob_{reg.player.contact_number.strip()}", reg.category_id
                )

        # Step 2: Build structured category sections
        processed_categories: List[Dict[str, Any]] = []
        unique_player_keys: Set[str] = set()

        for cat in categories:
            cat_participants = [p for p in all_participants if p.category_id == cat.id]
            participant_rows: List[Dict[str, Any]] = []

            for idx, p in enumerate(cat_participants):
                # Unique player tracking for header metrics
                p_key = (
                    f"pid_{p.player_id}"
                    if p.player_id
                    else (
                        f"mob_{p.mobile.strip()}" if p.mobile else f"name_{p.name.strip().lower()}"
                    )
                )
                unique_player_keys.add(p_key)

                # Find all categories this participant is registered for
                associated_cat_ids: Set[int] = set()
                associated_cat_ids.add(cat.id)  # Ensure current category is present

                if p.player_id and f"pid_{p.player_id}" in player_to_category_ids:
                    associated_cat_ids.update(player_to_category_ids[f"pid_{p.player_id}"])
                if p.mobile and f"mob_{p.mobile.strip()}" in player_to_category_ids:
                    associated_cat_ids.update(player_to_category_ids[f"mob_{p.mobile.strip()}"])
                if p.name and f"name_{p.name.strip().lower()}" in player_to_category_ids:
                    associated_cat_ids.update(
                        player_to_category_ids[f"name_{p.name.strip().lower()}"]
                    )

                # Build category badge list
                category_tags: List[Dict[str, Any]] = []
                # Keep current category first, followed by others sorted by category ID
                sorted_cat_ids = sorted(
                    associated_cat_ids,
                    key=lambda cid: (0 if cid == cat.id else 1, cid),
                )

                for cid in sorted_cat_ids:
                    cat_obj = category_by_id.get(cid)
                    if cat_obj:
                        pal = cat_palette_map.get(cid, cls.TAG_PALETTES[0])
                        category_tags.append(
                            {
                                "id": cid,
                                "name": cat_obj.name,
                                "bg": pal["bg"],
                                "text": pal["text"],
                                "border": pal["border"],
                                "is_current": (cid == cat.id),
                            }
                        )

                # Match registration for payment details if available
                matching_reg = reg_by_cat_and_player.get((cat.id, p.player_id))
                payment_badge = cls.resolve_payment_badge(p, matching_reg, cat.entry_fee)

                # Format display seed
                seed_val = p.manual_seed or p.seed
                seed_str = str(seed_val) if seed_val else ""
                seed_display = f"#{seed_str}" if seed_str else ""

                # Doubles / partner handling
                is_doubles = bool(
                    p.partner_name
                    or p.player2_id
                    or "doubles" in (cat.format or "").lower()
                    or "doubles" in cat.name.lower()
                )
                partner_display = p.partner_name or ""
                if not partner_display and "/" in p.name:
                    parts = p.name.split("/", 1)
                    partner_display = parts[1].strip()

                # Contact info
                contact_mobile = p.mobile or (p.player.contact_number if p.player else "")
                contact_email = p.email or (p.player.email if p.player else "")

                participant_rows.append(
                    {
                        "serial_number": idx + 1,
                        "id": p.id,
                        "name": p.name,
                        "partner_name": partner_display,
                        "is_doubles": is_doubles,
                        "seed": seed_str,
                        "seed_display": seed_display,
                        "mobile": contact_mobile,
                        "email": contact_email,
                        "gender": p.gender or (p.player.gender if p.player else ""),
                        "age": p.player.age if (p.player and hasattr(p.player, "age")) else None,
                        "payment_label": payment_badge["label"],
                        "payment_badge_class": payment_badge["badge_class"],
                        "payment_is_paid": payment_badge["is_paid"],
                        "category_tags": category_tags,
                        "total_tags_count": len(category_tags),
                        "group_name": (p.group.name if getattr(p, "group", None) else ""),
                        "checked_in": bool(p.checked_in),
                    }
                )

            cat_palette = cat_palette_map.get(cat.id, cls.TAG_PALETTES[0])
            format_key = (cat.format or "single_elimination").lower()
            format_label = cls.FORMAT_DISPLAY_MAP.get(
                format_key, (cat.format or "Single Elimination").replace("_", " ").title()
            )

            group_summary = ""
            if cat.format == "group_stage" or cat.has_group_stage:
                if cat.num_groups and cat.qualifiers_per_group:
                    group_summary = (
                        f"{cat.num_groups} Groups · Top {cat.qualifiers_per_group} to Knockouts"
                    )
                elif cat.num_groups:
                    group_summary = f"{cat.num_groups} Groups"

            processed_categories.append(
                {
                    "id": cat.id,
                    "name": cat.name,
                    "format_display": format_label,
                    "group_summary": group_summary,
                    "entry_fee": cat.entry_fee,
                    "entry_fee_display": f"₹{int(cat.entry_fee)}" if cat.entry_fee else "Free",
                    "participants": participant_rows,
                    "count": len(participant_rows),
                    "palette": cat_palette,
                }
            )

        # Build metric boxes for top of PDF
        metric_boxes: List[Dict[str, Any]] = [
            {
                "label": "Total Participants",
                "value": str(len(unique_player_keys)),
                "color": "#0f172a",
                "bg": "#f8fafc",
                "border": "#cbd5e1",
            }
        ]

        for cat_info in processed_categories:
            metric_boxes.append(
                {
                    "label": cat_info["name"],
                    "value": str(cat_info["count"]),
                    "color": cat_info["palette"]["text"],
                    "bg": cat_info["palette"]["bg"],
                    "border": cat_info["palette"]["border"],
                }
            )

        venue_display = (
            (tournament.academy.name if tournament.academy else "")
            or (tournament.game_info if tournament.game_info else "")
            or "Official Tournament Venue"
        )

        return {
            "tournament_name": tournament.name,
            "tournament_slug": tournament.url_slug,
            "dates_str": cls.format_dates(tournament),
            "venue": venue_display,
            "categories": processed_categories,
            "metric_boxes": metric_boxes,
            "total_categories": len(processed_categories),
            "total_unique_participants": len(unique_player_keys),
            "generated_at": datetime.now().strftime("%d %b %Y, %H:%M"),
        }
