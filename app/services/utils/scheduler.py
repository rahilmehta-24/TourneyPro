"""
Tournament Multi-Day Scheduling, Anti-Clash & Order of Play Engine for TourneyPro.

Features:
 1. Multi-Day Calendar Distribution:
    - Respects Tournament start_date & end_date.
    - Daily Operating Windows (e.g. 09:00 AM to 07:00 PM).
    - When day's operating hours end, matches automatically roll over to the next tournament day at daily_start_time.
 2. Multi-Category Player Anti-Clash Protection:
    - Detects players participating in multiple categories (via player_id or participant matching).
    - Enforces a mandatory rest buffer (e.g. 30-45 minutes) between a player's matches.
    - Eliminates simultaneous match conflicts across different courts.
 3. Intelligent Match Ordering:
    - Singles matches prioritized before Doubles matches for shared players.
    - Preliminary / Group stage matches scheduled on Day 1 / earlier days.
    - Category Finals pinned to the concluding tournament day if enabled.
 4. Tennis "Followed By" (Not Before) Scheduling:
    - First match of the day has a fixed start time (e.g., 09:00).
    - Subsequent matches designated as "Not Before" (NB) or "Followed By" with estimated start times.
 5. Rain Delay / Time Shift utility:
    - Shifts all pending matches by +X minutes seamlessly.
 6. Reassignment utility:
    - Allows moving a match to an open court immediately.
"""

import json
from datetime import datetime, date, time, timedelta
from app.domain.models import db, Match, Category, Tournament, Participant, Group, Player


def parse_time_str(time_str: str, default: time = time(9, 0)) -> time:
    """Parse 'HH:MM' string to time object."""
    if not time_str:
        return default
    try:
        parts = time_str.strip().split(':')
        return time(int(parts[0]), int(parts[1]))
    except Exception:
        return default


def get_court_names_list(source_courts_text: str | None, num_courts: int) -> list[str]:
    """Parse court names string or generate Court 1..N."""
    if source_courts_text:
        # Check comma-separated or json-style
        cleaned = source_courts_text.replace('[', '').replace(']', '').replace('"', '').replace("'", "")
        names = [n.strip() for n in cleaned.split(',') if n.strip()]
        if len(names) >= num_courts:
            return names[:num_courts]
        elif names:
            # Fill remaining
            for i in range(len(names) + 1, num_courts + 1):
                names.append(f"Court {i}")
            return names
    return [f"Court {i + 1}" for i in range(max(num_courts, 1))]


def get_tournament_daily_schedule(tournament: Tournament, tournament_days: list[date]) -> dict[date, dict[str, time]]:
    """
    Returns a mapping for each day in tournament_days:
    {
        d: {
            "start": time(H, M),
            "end": time(H, M)
        }
    }
    Falling back to tournament.court_operating_start & tournament.court_operating_end.
    """
    default_start = parse_time_str(tournament.court_operating_start, default=time(9, 0))
    default_end = parse_time_str(tournament.court_operating_end, default=time(19, 0))

    custom_hours = {}
    if getattr(tournament, 'daily_operating_hours', None):
        try:
            raw = tournament.daily_operating_hours
            custom_hours = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except Exception:
            custom_hours = {}

    schedule = {}
    for d in tournament_days:
        d_str = d.strftime("%Y-%m-%d")
        if d_str in custom_hours and isinstance(custom_hours[d_str], dict):
            s_val = custom_hours[d_str].get('start')
            e_val = custom_hours[d_str].get('end')
            d_start = parse_time_str(s_val, default=default_start) if s_val else default_start
            d_end = parse_time_str(e_val, default=default_end) if e_val else default_end
        else:
            d_start = default_start
            d_end = default_end
        schedule[d] = {"start": d_start, "end": d_end}
    return schedule


def get_participant_player_keys(p: Participant | None) -> set:
    """Return unique player identifiers for a participant (supports Singles and Doubles)."""
    if not p:
        return set()
    keys = set()
    if p.player_id:
        keys.add(f"player_{p.player_id}")
    if getattr(p, 'player2_id', None):
        keys.add(f"player_{p.player2_id}")
    # Also fallback to normalized name if player_id is missing
    norm_name = p.name.strip().lower()
    if '/' in norm_name:
        for sub in norm_name.split('/'):
            sub_clean = sub.strip()
            if sub_clean:
                keys.add(f"name_{sub_clean}")
    else:
        keys.add(f"name_{norm_name}")
    return keys


def get_earliest_day_index(round_num: int, max_rounds: int, num_days: int) -> int:
    """
    Returns the target day index (0-indexed) where round_num should ideally start.
    Ensures multi-day distribution across available tournament days:
      - Finals always target concluding day.
      - Semifinals target concluding day (morning) or penultimate day.
      - Earlier rounds staged proportionally across earlier days.
    """
    if num_days <= 1 or max_rounds <= 1:
        return 0

    # Finals always on the concluding day if multi-day
    if round_num >= max_rounds:
        return num_days - 1

    # In a 2-day tournament:
    if num_days == 2:
        if round_num >= max_rounds - 1 and max_rounds > 2:
            return 1
        return 0

    # In a 3-day tournament:
    if num_days == 3:
        if max_rounds <= 3:
            return min(round_num - 1, 2)
        elif max_rounds == 4:
            if round_num == 1:
                return 0
            elif round_num == 2:
                return 1
            else:
                return 2
        else:
            if round_num == 1:
                return 0
            elif round_num in (2, 3):
                return 1
            else:
                return 2

    # In 4+ day tournaments:
    day_span = num_days - 1
    step = day_span / max(max_rounds - 1, 1)
    return min(int((round_num - 1) * step), num_days - 1)


def get_target_session(round_num: int, max_rounds: int, num_days: int) -> str:
    """
    Returns 'day' or 'evening' target session for the round in multi-day events.
    - If multiple rounds occur on the same day:
      Earlier round -> 'day'
      Later marquee round (Quarter-Finals on Day 2, Grand Finals on Day 3) -> 'evening'
    """
    if num_days >= 3:
        # On Day 2 (rounds 2 & 3 for 5-round brackets): QF targets evening
        if max_rounds >= 4 and round_num == max_rounds - 2:
            return 'evening'
        # On Day 3 (SF & Finals): Grand Finals target evening
        if round_num >= max_rounds and max_rounds >= 3:
            return 'evening'
    elif num_days == 2:
        # On Day 2: Finals target evening
        if round_num >= max_rounds and max_rounds >= 2:
            return 'evening'
    return 'day'


class CourtSchedule(list):
    """
    List of matches on a court that also provides session subdivisions:
    day_matches, evening_matches, day_count, evening_count, etc.
    Inherits from list for complete backward compatibility.
    """
    def __init__(self, matches=(), day_matches=(), evening_matches=()):
        super().__init__(matches)
        self.matches = list(matches)
        self.day_matches = list(day_matches)
        self.evening_matches = list(evening_matches)
        self.day_count = len(day_matches)
        self.evening_count = len(evening_matches)
        self.total_matches = len(matches)


def auto_schedule_tournament(tournament_id: int) -> dict:
    """
    Globally schedule all categories in a tournament across all days and courts
    with multi-category anti-clash, rest buffers, and daily operating windows.
    """
    tournament = Tournament.query.get_or_404(tournament_id)
    categories = Category.query.filter_by(tournament_id=tournament_id).all()
    if not categories and tournament.has_categories:
        return {"scheduled": 0, "message": "No categories found"}

    # 1. Determine Tournament Calendar Days
    start_d = tournament.start_date or (tournament.created_at.date() if tournament.created_at else date.today())
    end_d = tournament.end_date or start_d
    if end_d < start_d:
        end_d = start_d

    num_days = (end_d - start_d).days + 1
    tournament_days = [start_d + timedelta(days=i) for i in range(num_days)]
    last_day = tournament_days[-1]

    # 2. Operating hours & court setup
    daily_schedules = get_tournament_daily_schedule(tournament, tournament_days)
    
    # Determine overall court count & names
    max_courts = tournament.num_courts or 1
    for cat in categories:
        if (cat.num_courts or 1) > max_courts:
            max_courts = cat.num_courts or 1
    courts = get_court_names_list(tournament.court_names, max_courts)

    court_buffer = timedelta(minutes=tournament.court_buffer_minutes if tournament.court_buffer_minutes is not None else 10)
    player_rest_buffer = timedelta(minutes=tournament.min_rest_minutes if tournament.min_rest_minutes is not None else 0)
    max_daily_matches = tournament.max_matches_per_player_day  # Can be None (no limit) or integer

    # 3. Gather all pending/in-progress matches across all categories
    all_matches = (
        Match.query.filter_by(tournament_id=tournament_id)
        .filter(Match.status != "completed")
        .all()
    )
    if not all_matches:
        return {"scheduled": 0, "message": "No uncompleted matches to schedule"}

    # 4. Sort and prioritize matches for smart scheduling:
    cat_map = {c.id: c for c in categories}
    max_rounds_by_cat: dict[int | None, int] = {}
    for om in all_matches:
        cid = om.category_id
        if cid not in max_rounds_by_cat or om.round > max_rounds_by_cat[cid]:
            max_rounds_by_cat[cid] = om.round

    def match_priority_key(m: Match):
        cat = cat_map.get(m.category_id)
        pref_day = getattr(cat, 'preferred_start_day', 1) or 1
        is_doubles = 1 if (cat and 'doubles' in (cat.format or '')) else 0
        
        max_round = max_rounds_by_cat.get(m.category_id, 1)
        target_day_idx = get_earliest_day_index(m.round, max_round, len(tournament_days))
        target_session = get_target_session(m.round, max_round, len(tournament_days))
        target_session_idx = 1 if target_session == 'evening' else 0

        # Match type priority (group stage before knockout)
        type_priority = 0 if m.match_type in ('group_stage', 'round_robin') else 1

        return (target_day_idx, target_session_idx, pref_day, type_priority, m.round, is_doubles, m.match_number)

    sorted_matches = sorted(all_matches, key=match_priority_key)

    # 5. Scheduling State Tracking
    # court_next_available[day_idx][court_name] = datetime
    court_next_available: dict[date, dict[str, datetime]] = {}
    for d in tournament_days:
        court_next_available[d] = {}
        d_start = daily_schedules[d]["start"]
        for c in courts:
            court_next_available[d][c] = datetime.combine(d, d_start)

    # player_next_available[player_key] = datetime (player cannot play until this time)
    player_next_available: dict[str, datetime] = {}
    # player_daily_count[d][player_key] = count
    player_daily_count: dict[date, dict[str, int]] = {d: {} for d in tournament_days}

    # Match earliest start time per category round (Round N cannot start before Round N-1 ends)
    round_ready_at: dict[tuple[int, int], datetime] = {} # (category_id, round) -> earliest datetime

    scheduled_count = 0

    for match in sorted_matches:
        cat = cat_map.get(match.category_id)
        duration_minutes = cat.avg_match_duration or tournament.avg_match_duration or 60
        match_duration = timedelta(minutes=duration_minutes)

        # Participants & player keys
        p1 = match.participant1
        p2 = match.participant2
        p_keys = get_participant_player_keys(p1).union(get_participant_player_keys(p2))

        # Multi-day round distribution across tournament calendar
        max_round = max_rounds_by_cat.get(match.category_id, 1)
        if len(tournament_days) > 1 and match.match_type not in ('group_stage', 'round_robin'):
            min_day_idx = get_earliest_day_index(match.round, max_round, len(tournament_days))
            target_days = tournament_days[min_day_idx:]
        elif len(tournament_days) > 1 and match.match_type in ('group_stage', 'round_robin'):
            min_day_idx = min(max(match.round - 1, 0), len(tournament_days) - 1)
            target_days = tournament_days[min_day_idx:]
        else:
            target_days = tournament_days

        # Determine earliest possible start from category settings or previous round
        earliest_time = datetime.min
        if cat and cat.start_date_time:
            earliest_time = max(earliest_time, cat.start_date_time)
        if (match.category_id, match.round - 1) in round_ready_at:
            prev_round_end = round_ready_at[(match.category_id, match.round - 1)]
            same_day_round_rest = max(player_rest_buffer, timedelta(minutes=45))
            earliest_time = max(earliest_time, prev_round_end + same_day_round_rest)

        # Session targeting (Day Session vs Evening Session)
        target_session = get_target_session(match.round, max_round, len(tournament_days))
        evening_start_time = parse_time_str(getattr(tournament, 'evening_session_start', '16:00'), default=time(16, 0))

        # Search for best available (day, court, slot) that respects:
        # - Daily closing time (dynamically per day)
        # - Court availability
        # - Player anti-clash & rest buffer
        # - Player daily match cap
        assigned = False

        for current_day in target_days:
            # Check player daily match cap for this day (only if organizer set a limit)
            if max_daily_matches is not None and p_keys and any(player_daily_count[current_day].get(pk, 0) >= max_daily_matches for pk in p_keys):
                continue  # Try next day

            current_day_start = daily_schedules[current_day]["start"]
            current_day_end = daily_schedules[current_day]["end"]
            day_end_dt = datetime.combine(current_day, current_day_end)

            # Find court with earliest available slot
            sorted_courts = sorted(courts, key=lambda c: court_next_available[current_day][c])

            # 1. If round targets evening session, attempt scheduling in the evening session first
            evening_start_dt = datetime.combine(current_day, evening_start_time)
            prefer_evening = (target_session == 'evening' and earliest_time <= evening_start_dt)

            if prefer_evening:
                for court_name in sorted_courts:
                    court_ready = court_next_available[current_day][court_name]
                    tentative_start = max(court_ready, evening_start_dt)
                    if earliest_time.date() == current_day:
                        tentative_start = max(tentative_start, earliest_time)
                    elif earliest_time.date() > current_day:
                        continue

                    for pk in p_keys:
                        if pk in player_next_available and player_next_available[pk].date() == current_day:
                            tentative_start = max(tentative_start, player_next_available[pk])

                    tentative_end = tentative_start + match_duration
                    if tentative_end <= day_end_dt:
                        # Found valid evening slot!
                        match.scheduled_time = tentative_start
                        match.scheduled_date = current_day
                        match.scheduled_end_time = tentative_end
                        match.court_name = court_name
                        match.is_not_before = True

                        court_next_available[current_day][court_name] = tentative_end + court_buffer
                        player_free_time = tentative_end + player_rest_buffer
                        for pk in p_keys:
                            player_next_available[pk] = player_free_time
                            player_daily_count[current_day][pk] = player_daily_count[current_day].get(pk, 0) + 1

                        curr_round_max = round_ready_at.get((match.category_id, match.round), datetime.min)
                        round_ready_at[(match.category_id, match.round)] = max(curr_round_max, tentative_end)

                        scheduled_count += 1
                        assigned = True
                        break

            if assigned:
                break

            # 2. Standard slot search (day session or fallback)
            for court_name in sorted_courts:
                court_ready = court_next_available[current_day][court_name]
                
                # The match cannot start before court_ready, earliest_time, or any player's next_available time
                tentative_start = max(court_ready, datetime.combine(current_day, current_day_start))
                if earliest_time.date() == current_day:
                    tentative_start = max(tentative_start, earliest_time)
                elif earliest_time.date() > current_day:
                    continue  # Can't play on a day before the category even begins

                # Check player anti-clash & rest buffer
                for pk in p_keys:
                    if pk in player_next_available and player_next_available[pk].date() == current_day:
                        tentative_start = max(tentative_start, player_next_available[pk])

                tentative_end = tentative_start + match_duration

                # Check if this exceeds court closing time for the day
                if tentative_end > day_end_dt:
                    continue  # Cannot fit on this court today

                # Found valid slot!
                is_first_match_of_day = (tentative_start.time() == current_day_start)
                
                match.scheduled_time = tentative_start
                match.scheduled_date = current_day
                match.scheduled_end_time = tentative_end
                match.court_name = court_name
                match.is_not_before = not is_first_match_of_day

                # Update court availability
                court_next_available[current_day][court_name] = tentative_end + court_buffer

                # Update player availability with rest buffer
                player_free_time = tentative_end + player_rest_buffer
                for pk in p_keys:
                    player_next_available[pk] = player_free_time
                    player_daily_count[current_day][pk] = player_daily_count[current_day].get(pk, 0) + 1

                # Update category round progress time
                curr_round_max = round_ready_at.get((match.category_id, match.round), datetime.min)
                round_ready_at[(match.category_id, match.round)] = max(curr_round_max, tentative_end)

                scheduled_count += 1
                assigned = True
                break

            if assigned:
                break

        if not assigned:
            fallback_day = target_days[-1]
            fallback_day_start = daily_schedules[fallback_day]["start"]
            best_court = min(courts, key=lambda c: court_next_available[fallback_day][c])
            f_start = max(court_next_available[fallback_day][best_court], datetime.combine(fallback_day, fallback_day_start))
            f_end = f_start + match_duration
            
            match.scheduled_time = f_start
            match.scheduled_date = fallback_day
            match.scheduled_end_time = f_end
            match.court_name = best_court
            match.is_not_before = True
            
            court_next_available[fallback_day][best_court] = f_end + court_buffer
            scheduled_count += 1

    db.session.commit()
    return {
        "scheduled": scheduled_count,
        "days": len(tournament_days),
        "courts": courts,
        "message": f"Successfully scheduled {scheduled_count} matches across {len(tournament_days)} day(s) with anti-clash protection."
    }


def auto_schedule_category(category_id: int) -> dict:
    """
    Schedule a single category or trigger global tournament scheduling.
    """
    category = Category.query.get_or_404(category_id)
    return auto_schedule_tournament(category.tournament_id)


def apply_weather_delay(tournament_id: int, delay_minutes: int, court_filter: str | None = None) -> int:
    """
    Shifts all pending matches in a tournament by +delay_minutes.
    Useful for rain delays or prolonged matches.
    """
    shift = timedelta(minutes=delay_minutes)
    query = Match.query.filter_by(tournament_id=tournament_id).filter(Match.status == 'pending', Match.scheduled_time.isnot(None))
    if court_filter:
        query = query.filter_by(court_name=court_filter)
        
    matches = query.all()
    for m in matches:
        m.scheduled_time = m.scheduled_time + shift
        if m.scheduled_end_time:
            m.scheduled_end_time = m.scheduled_end_time + shift
        m.scheduled_date = m.scheduled_time.date()
        m.is_not_before = True

    db.session.commit()
    return len(matches)


def reassign_match_court(match_id: int, new_court_name: str, new_time: datetime | None = None) -> bool:
    """
    Move a match to another court immediately (e.g. quick call to available court).
    """
    match = Match.query.get(match_id)
    if not match:
        return False
    match.court_name = new_court_name
    if new_time:
        match.scheduled_time = new_time
        match.scheduled_date = new_time.date()
    db.session.commit()
    return True


def extract_participant_players(participant: Participant | None) -> list[dict]:
    """
    Extracts individual players for singles or doubles pairs.
    Returns list of dicts: [{'name': 'Player Name', 'player_id': int | None}, ...]
    Handles ' / ', '/', ' & ', ' and ', and partner_name attribute.
    """
    if not participant:
        return [{"name": "TBD", "player_id": None}]

    raw_name = (participant.name or "TBD").strip()
    if raw_name in ("TBD", "Bye", ""):
        return [{"name": raw_name or "TBD", "player_id": None}]

    p1_name, p2_name = None, None

    # Check for doubles pair separators
    if " / " in raw_name:
        parts = [part.strip() for part in raw_name.split(" / ", 1)]
        p1_name, p2_name = parts[0], parts[1]
    elif "/" in raw_name:
        parts = [part.strip() for part in raw_name.split("/", 1)]
        p1_name, p2_name = parts[0], parts[1]
    elif " & " in raw_name:
        parts = [part.strip() for part in raw_name.split(" & ", 1)]
        p1_name, p2_name = parts[0], parts[1]
    elif participant.partner_name:
        p1_name = raw_name
        p2_name = participant.partner_name.strip()

    if p1_name and p2_name:
        p1_id = participant.player_id
        p2_id = participant.player2_id

        if not p1_id and p1_name:
            matched1 = Player.query.filter_by(name=p1_name).first()
            if matched1:
                p1_id = matched1.id

        if not p2_id and p2_name:
            matched2 = Player.query.filter_by(name=p2_name).first()
            if matched2:
                p2_id = matched2.id

        return [
            {"name": p1_name, "player_id": p1_id},
            {"name": p2_name, "player_id": p2_id}
        ]

    # Singles participant
    p_id = participant.player_id
    if not p_id and raw_name:
        matched = Player.query.filter_by(name=raw_name).first()
        if matched:
            p_id = matched.id

    return [{"name": raw_name, "player_id": p_id}]


def get_order_of_play(tournament_slug: str, filter_date: date | None = None) -> dict:
    """
    Returns structured Order of Play for tournament with day filtering,
    'Not Before' indicators, and court schedules.
    """
    tournament = Tournament.query.filter_by(url_slug=tournament_slug).first_or_404()

    # Query all matches with court assignment
    query = (
        Match.query.filter_by(tournament_id=tournament.id)
        .filter(Match.scheduled_time.isnot(None), Match.court_name.isnot(None))
    )

    all_matches = query.order_by(Match.scheduled_time).all()

    # Discover all operating tournament dates:
    # Include all calendar dates between tournament.start_date and tournament.end_date, plus any match dates
    calendar_dates = set()
    if tournament.start_date and tournament.end_date and tournament.start_date <= tournament.end_date:
        num_calendar_days = (tournament.end_date - tournament.start_date).days + 1
        calendar_dates = {tournament.start_date + timedelta(days=i) for i in range(num_calendar_days)}

    match_dates = {m.scheduled_time.date() for m in all_matches if m.scheduled_time}
    all_dates_set = calendar_dates.union(match_dates)
    unique_dates = sorted(list(all_dates_set)) if all_dates_set else sorted(list(match_dates))

    # If filter_date is not specified, default to first date with matches or first calendar day
    active_date = filter_date
    if not active_date and unique_dates:
        dates_with_matches = sorted(list(match_dates))
        active_date = dates_with_matches[0] if dates_with_matches else unique_dates[0]

    # Filter matches by active date
    if active_date:
        matches = [m for m in all_matches if m.scheduled_time.date() == active_date]
    else:
        matches = all_matches

    # Map max round per category (or overall tournament) for knockout round naming
    # so that round names match the brackets exactly: Final, Semi-Final, Quarter-Final, Round X
    max_rounds_by_cat: dict[int | None, int] = {}
    for m in all_matches:
        if m.match_type not in ('group_stage', 'round_robin'):
            cid = m.category_id
            if cid not in max_rounds_by_cat or m.round > max_rounds_by_cat[cid]:
                max_rounds_by_cat[cid] = m.round

    def get_match_round_name(m: Match) -> str:
        # Check special bracket types first
        b_type = getattr(m, 'bracket_type', None)
        if b_type in ('grand_finals', 'grand_final'):
            return "Grand Final"
        elif b_type == 'third_place':
            return "3rd Place"

        if m.match_type == 'group_stage':
            if m.group_id:
                grp = Group.query.get(m.group_id)
                if grp:
                    return grp.name
            return f"Group Stage (R{m.round})"
        elif m.match_type == 'round_robin':
            return f"Round {m.round}"
        else:
            # Knockout matches: exactly mirror the brackets
            max_r = max_rounds_by_cat.get(m.category_id, 1)
            if m.round == max_r:
                return "Final"
            elif m.round == max_r - 1 and max_r >= 2:
                return "Semi-Final"
            elif m.round == max_r - 2 and max_r >= 3:
                return "Quarter-Final"
            else:
                return f"Round {m.round}"

    # Evening session cutoff configuration (default: 16:00 / 4:00 PM)
    evening_start_str = getattr(tournament, 'evening_session_start', None) or '16:00'
    evening_cutoff = parse_time_str(evening_start_str, default=time(16, 0))

    # Group by court
    order: dict[str, list] = {}
    for match in matches:
        court = match.court_name
        if court not in order:
            order[court] = []

        cat = Category.query.get(match.category_id)
        cat_name = cat.name if cat else "Tournament Match"

        p1 = match.participant1.name if match.participant1 else "TBD"
        p2 = match.participant2.name if match.participant2 else "TBD"

        p1_player_id = match.participant1.player_id if match.participant1 else None
        p2_player_id = match.participant2.player_id if match.participant2 else None

        p1_players = extract_participant_players(match.participant1)
        p2_players = extract_participant_players(match.participant2)

        time_str = match.scheduled_time.strftime("%H:%M") if match.scheduled_time else "TBD"
        is_nb = getattr(match, 'is_not_before', False)
        is_evening = bool(match.scheduled_time and match.scheduled_time.time() >= evening_cutoff)
        session_type = 'evening' if is_evening else 'day'
        session_label = 'Evening Session' if is_evening else 'Day Session'
        session_icon = '🌙' if is_evening else '☀️'

        order[court].append({
            "match": match,
            "category_name": cat_name,
            "category_id": match.category_id,
            "time": time_str,
            "is_not_before": is_nb,
            "time_display": f"NB {time_str}" if is_nb else time_str,
            "session": session_type,
            "session_label": session_label,
            "session_icon": session_icon,
            "is_evening": is_evening,
            "date": match.scheduled_time.strftime("%d %b %Y") if match.scheduled_time else "",
            "raw_date": match.scheduled_time.date() if match.scheduled_time else None,
            "p1": p1,
            "p2": p2,
            "p1_player_id": p1_player_id,
            "p2_player_id": p2_player_id,
            "p1_players": p1_players,
            "p2_players": p2_players,
            "round": match.round,
            "round_name": get_match_round_name(match),
            "match_number": match.match_number,
            "status": match.status,
            "court": court,
        })

    # Naturally sort courts (Court 1, Court 2, ...) and wrap in CourtSchedule
    sorted_order = {}
    for court, c_matches in sorted(order.items()):
        day_m = [m for m in c_matches if m.get("session") == "day"]
        eve_m = [m for m in c_matches if m.get("session") == "evening"]
        sorted_order[court] = CourtSchedule(c_matches, day_m, eve_m)

    # Build days metadata list for UI tabs
    days_meta = []
    matches_per_date: dict[date, int] = {}
    day_matches_per_date: dict[date, int] = {}
    eve_matches_per_date: dict[date, int] = {}
    for m in all_matches:
        if m.scheduled_time:
            d = m.scheduled_time.date()
            matches_per_date[d] = matches_per_date.get(d, 0) + 1
            if m.scheduled_time.time() < evening_cutoff:
                day_matches_per_date[d] = day_matches_per_date.get(d, 0) + 1
            else:
                eve_matches_per_date[d] = eve_matches_per_date.get(d, 0) + 1

    for idx, d in enumerate(unique_dates):
        count = matches_per_date.get(d, 0)
        day_cnt = day_matches_per_date.get(d, 0)
        eve_cnt = eve_matches_per_date.get(d, 0)
        label = f"Day {idx + 1} ({d.strftime('%d %b')})"
        days_meta.append({
            "date": d,
            "date_str": d.strftime("%Y-%m-%d"),
            "label": label,
            "match_count": count,
            "day_session_count": day_cnt,
            "evening_session_count": eve_cnt,
            "is_active": (d == active_date)
        })

    # Discover active day's operating hours
    active_day_start = tournament.court_operating_start or "09:00"
    active_day_end = tournament.court_operating_end or "19:00"
    if active_date:
        act_sched = get_tournament_daily_schedule(tournament, [active_date]).get(active_date)
        if act_sched:
            active_day_start = act_sched["start"].strftime("%H:%M")
            active_day_end = act_sched["end"].strftime("%H:%M")

    # Active day session totals across all courts
    active_day_matches = [m for m in matches if m.scheduled_time and m.scheduled_time.date() == active_date] if active_date else matches
    total_day_session = sum(1 for m in active_day_matches if m.scheduled_time and m.scheduled_time.time() < evening_cutoff)
    total_evening_session = sum(1 for m in active_day_matches if m.scheduled_time and m.scheduled_time.time() >= evening_cutoff)

    return {
        "courts": sorted_order,
        "tournament": tournament,
        "unique_dates": unique_dates,
        "active_date": active_date,
        "active_day_start": active_day_start,
        "active_day_end": active_day_end,
        "evening_session_start": evening_start_str,
        "day_session_count": total_day_session,
        "evening_session_count": total_evening_session,
        "days_meta": days_meta,
        "total_matches_scheduled": len(all_matches)
    }
