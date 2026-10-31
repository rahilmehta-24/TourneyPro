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
from app.domain.models import db, Match, Category, Tournament, Participant, Group, Player, TeamMember


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


def enforce_order_of_play_day_progression(tournament_id: int) -> int:
    """
    Ensures that matches on Day N cannot be marked completed or in_progress
    if Day N-1 (or any earlier day) matches have not been completed.
    Also ensures that within each category, Round R+1 cannot be completed
    if Round R matches have not been completed.
    
    If any downstream match on a future day/round was prematurely marked completed
    while earlier matches are pending/unstarted, this function resets the premature match
    to 'pending', clears premature scores, and clears unearned downstream bracket participant
    slots so that the Order of Play strictly reflects valid tournament progression.
    Returns the count of sanitized matches.
    """
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return 0

    all_matches = (
        Match.query.filter_by(tournament_id=tournament_id)
        .filter(Match.scheduled_time.isnot(None))
        .order_by(Match.scheduled_time)
        .all()
    )
    if not all_matches:
        return 0

    unique_dates = sorted(list({m.scheduled_time.date() for m in all_matches}))
    sanitized = 0

    def clear_downstream(m: Match):
        if not m.category_id or not m.round:
            return
        next_round = m.round + 1
        next_match_num = (m.match_number + 1) // 2
        next_m = Match.query.filter_by(
            category_id=m.category_id,
            round=next_round,
            match_number=next_match_num,
            bracket_type=m.bracket_type or 'main'
        ).first()
        if next_m:
            if m.match_number % 2 == 1:
                next_m.participant1_id = None
            else:
                next_m.participant2_id = None
            if next_m.status != 'pending':
                next_m.status = 'pending'
                next_m.score1 = None
                next_m.score2 = None
                next_m.winner_id = None
                next_m.completed_at = None
            clear_downstream(next_m)

    # 1. Day-to-Day Progression: Find earliest date with pending matches
    if len(unique_dates) > 1:
        first_incomplete_date = None
        for d in unique_dates:
            day_matches = [m for m in all_matches if m.scheduled_time.date() == d]
            if any(m.status != 'completed' for m in day_matches):
                first_incomplete_date = d
                break

        if first_incomplete_date:
            future_premature = [
                m for m in all_matches
                if m.scheduled_time.date() > first_incomplete_date and m.status in ('completed', 'in_progress')
            ]
            for fm in future_premature:
                fm.status = 'pending'
                fm.score1 = None
                fm.score2 = None
                fm.winner_id = None
                fm.completed_at = None
                clear_downstream(fm)
                sanitized += 1

    # 2. Bracket Round Progression per category: Round R+1 cannot be completed if Round R is pending
    for cat_id in {m.category_id for m in all_matches if m.category_id}:
        cat_matches = [m for m in all_matches if m.category_id == cat_id]
        cat_rounds = sorted(list({m.round for m in cat_matches}))
        earliest_incomplete_round = None
        for r in cat_rounds:
            r_matches = [m for m in cat_matches if m.round == r]
            if any(m.status != 'completed' for m in r_matches):
                earliest_incomplete_round = r
                break
        if earliest_incomplete_round is not None:
            for m in cat_matches:
                if m.round > earliest_incomplete_round and m.status in ('completed', 'in_progress'):
                    m.status = 'pending'
                    m.score1 = None
                    m.score2 = None
                    m.winner_id = None
                    m.completed_at = None
                    clear_downstream(m)
                    sanitized += 1

    if sanitized > 0:
        db.session.commit()

    return sanitized


def check_match_progression_allowed(match: Match) -> tuple[bool, str | None]:
    """
    Checks if a match is legally allowed to start (in_progress) or complete (completed)
    based on:
    1. Day-to-Day tournament progression: Matches on Day D cannot start if Day < D matches are incomplete.
    2. Category bracket round progression: Matches in Round R cannot start if Round < R matches in the category are incomplete.
    
    Returns (True, None) if allowed, or (False, error_message) if locked/premature.
    """
    if not match:
        return True, None

    # 1. Day-to-Day progression check
    if match.scheduled_time and match.tournament_id:
        match_date = match.scheduled_time.date()
        earlier_day_pending = (
            Match.query.filter(
                Match.tournament_id == match.tournament_id,
                Match.scheduled_time.isnot(None),
                Match.scheduled_time < datetime.combine(match_date, time.min),
                Match.status != 'completed'
            )
            .order_by(Match.scheduled_time)
            .first()
        )
        if earlier_day_pending and earlier_day_pending.scheduled_time:
            earlier_d_str = earlier_day_pending.scheduled_time.strftime('%d %b')
            return False, f"Matches on {earlier_d_str} must be completed before starting this match."

    # 2. Category Round progression check
    if match.category_id and match.round and match.round > 1:
        earlier_round_pending = (
            Match.query.filter(
                Match.category_id == match.category_id,
                Match.round < match.round,
                Match.status != 'completed'
            )
            .order_by(Match.round)
            .first()
        )
        if earlier_round_pending:
            return False, f"Round {earlier_round_pending.round} matches in this category must be completed first."

    return True, None


def auto_schedule_tournament(tournament_id: int) -> dict:
    """
    Globally schedule all categories in a tournament across all days and courts
    with multi-category anti-clash, rest buffers, and daily operating windows.
    """
    # Enforce chronological progression before scheduling
    enforce_order_of_play_day_progression(tournament_id)

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

    # 3. Gather all pending/in-progress matches across all categories (only top-level matches)
    # Pre-fetch all groups in this tournament to avoid N+1 queries in the loop
    groups = {g.id: g for g in Group.query.join(Category).filter(Category.tournament_id == tournament_id).all()}

    all_matches = (
        Match.query.filter_by(tournament_id=tournament_id)
        .filter(Match.status != "completed", Match.parent_match_id.is_(None))
        .options(
            db.joinedload(Match.participant1),
            db.joinedload(Match.participant2),
            db.selectinload(Match.sub_matches),
        )
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

        # Interleave groups across available courts: sort by round first, then group
        group_priority = m.group_id or 0

        return (target_day_idx, target_session_idx, pref_day, type_priority, m.round, group_priority, is_doubles, m.match_number)

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
    match_updates: list[dict] = []

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

        # Restrict target_days to category's start_date and end_date if defined
        if cat and cat.start_date:
            cat_end = cat.end_date or cat.start_date
            cat_days = [d for d in target_days if cat.start_date <= d <= cat_end]
            if cat_days:
                target_days = cat_days
            elif cat.start_date in tournament_days:
                target_days = [cat.start_date]

        # Determine earliest possible start from category settings or previous round
        earliest_time = datetime.min
        if cat and cat.start_date_time:
            earliest_time = max(earliest_time, cat.start_date_time)
        if (match.category_id, match.round - 1) in round_ready_at:
            prev_round_end = round_ready_at[(match.category_id, match.round - 1)]
            same_day_round_rest = max(player_rest_buffer, timedelta(minutes=45))
            earliest_time = max(earliest_time, prev_round_end + same_day_round_rest)

        # Respect Group Session Start Timing (e.g. Group A @ 09:00 AM, Group B @ 11:30 AM)
        grp = groups.get(match.group_id) if match.group_id else None
        if grp and grp.start_time:
            grp_time = parse_time_str(grp.start_time, default=None)
            if grp_time and target_days:
                grp_start_dt = datetime.combine(target_days[0], grp_time)
                earliest_time = max(earliest_time, grp_start_dt)

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

            # If category has its own daily schedule or start/end time, respect it
            if cat and cat.daily_schedule:
                try:
                    import json
                    cat_sched = json.loads(cat.daily_schedule)
                    d_key = current_day.strftime('%Y-%m-%d')
                    if d_key in cat_sched:
                        cs_start = parse_time_str(cat_sched[d_key].get('start'), default=None)
                        cs_end = parse_time_str(cat_sched[d_key].get('end'), default=None)
                        if cs_start:
                            current_day_start = max(current_day_start, cs_start)
                        if cs_end:
                            current_day_end = min(current_day_end, cs_end)
                except Exception:
                    pass
            elif cat and (cat.start_time or cat.end_time):
                if cat.start_time:
                    cs_start = parse_time_str(cat.start_time, default=None)
                    if cs_start:
                        current_day_start = max(current_day_start, cs_start)
                if cat.end_time:
                    cs_end = parse_time_str(cat.end_time, default=None)
                    if cs_end:
                        current_day_end = min(current_day_end, cs_end)

            day_end_dt = datetime.combine(current_day, current_day_end)

            # Find court with earliest available slot (prioritizing group's assigned courts)
            if grp and grp.assigned_courts:
                assigned_c_set = set(c.strip() for c in grp.assigned_courts.split(',') if c.strip())
                sorted_courts = sorted(courts, key=lambda c: (0 if c in assigned_c_set else 1, court_next_available[current_day][c]))
            else:
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
            court_next_available[fallback_day][best_court] = f_end + court_buffer
            scheduled_count += 1

        match_updates.append({
            "id": match.id,
            "scheduled_time": match.scheduled_time,
            "scheduled_date": match.scheduled_date,
            "scheduled_end_time": match.scheduled_end_time,
            "court_name": match.court_name,
            "is_not_before": match.is_not_before,
        })

        # Synchronize child rubbers with parent fixture
        if match.sub_matches:
            grp = groups.get(match.group_id) if match.group_id else None
            assigned_c_list = [c.strip() for c in (grp.assigned_courts or '').split(',') if c.strip()] if grp else []
            sub_courts = assigned_c_list if len(assigned_c_list) >= len(match.sub_matches) else courts
            for idx, r in enumerate(match.sub_matches):
                r.scheduled_time = match.scheduled_time
                r.scheduled_date = match.scheduled_date
                r.scheduled_end_time = match.scheduled_end_time
                r.is_not_before = match.is_not_before
                if sub_courts:
                    r.court_name = sub_courts[idx % len(sub_courts)]
                else:
                    r.court_name = match.court_name
                match_updates.append({
                    "id": r.id,
                    "scheduled_time": r.scheduled_time,
                    "scheduled_date": r.scheduled_date,
                    "scheduled_end_time": r.scheduled_end_time,
                    "court_name": r.court_name,
                    "is_not_before": r.is_not_before,
                })

    if match_updates:
        db.session.bulk_update_mappings(Match, match_updates)
    db.session.expire_all()
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


def extract_participant_players(participant: Participant | None, player_cache: dict[str, int | None] | None = None) -> list[dict]:
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

    def _lookup(name: str | None) -> int | None:
        if not name:
            return None
        if player_cache is not None:
            if name not in player_cache:
                matched = Player.query.filter_by(name=name).first()
                player_cache[name] = matched.id if matched else None
            return player_cache[name]
        matched = Player.query.filter_by(name=name).first()
        return matched.id if matched else None

    if p1_name and p2_name:
        p1_id = participant.player_id
        p2_id = participant.player2_id

        if not p1_id and p1_name:
            p1_id = _lookup(p1_name)

        if not p2_id and p2_name:
            p2_id = _lookup(p2_name)

        return [
            {"name": p1_name, "player_id": p1_id},
            {"name": p2_name, "player_id": p2_id}
        ]

    # Singles participant
    p_id = participant.player_id
    if not p_id and raw_name:
        p_id = _lookup(raw_name)

    return [{"name": raw_name, "player_id": p_id}]


def get_order_of_play(tournament_slug: str, filter_date: date | None = None) -> dict:
    """
    Returns structured Order of Play for tournament with day filtering,
    'Not Before' indicators, court schedules, and day progression enforcement.
    """
    tournament = Tournament.query.filter_by(url_slug=tournament_slug).first_or_404()

    # Pre-fetch categories and groups for tournament into in-memory dictionaries to avoid N+1 queries
    categories = {c.id: c for c in Category.query.filter_by(tournament_id=tournament.id).all()}
    groups = {
        g.id: g
        for g in Group.query.join(Category).filter(Category.tournament_id == tournament.id).all()
    }

    # Pre-fetch sub-matches counts in a single fast aggregate query
    sub_counts = dict(
        db.session.query(Match.parent_match_id, db.func.count(Match.id))
        .filter(Match.tournament_id == tournament.id, Match.parent_match_id.isnot(None))
        .group_by(Match.parent_match_id)
        .all()
    )

    evening_start_str = getattr(tournament, 'evening_session_start', None) or '16:00'
    evening_cutoff = parse_time_str(evening_start_str, default=time(16, 0))

    # 1. Fast lightweight summary query (no relationship joins) to discover dates, tab counts, and progress
    summary_rows = (
        db.session.query(
            Match.id,
            Match.scheduled_date,
            Match.scheduled_time,
            Match.parent_match_id,
            Match.status,
            Match.category_id,
            Match.round,
            Match.match_type,
            Match.court_name,
        )
        .filter(
            Match.tournament_id == tournament.id,
            Match.scheduled_time.isnot(None),
            Match.court_name.isnot(None),
        )
        .order_by(Match.scheduled_time)
        .all()
    )

    # Discover all operating tournament dates:
    calendar_dates = set()
    if tournament.start_date and tournament.end_date and tournament.start_date <= tournament.end_date:
        num_calendar_days = (tournament.end_date - tournament.start_date).days + 1
        calendar_dates = {tournament.start_date + timedelta(days=i) for i in range(num_calendar_days)}

    match_dates = {r.scheduled_date or r.scheduled_time.date() for r in summary_rows if r.scheduled_time}
    all_dates_set = calendar_dates.union(match_dates)
    unique_dates = sorted(list(all_dates_set)) if all_dates_set else sorted(list(match_dates))

    # If filter_date is not specified, default to first date with matches or first calendar day
    active_date = filter_date
    if not active_date and unique_dates:
        dates_with_matches = sorted(list(match_dates))
        active_date = dates_with_matches[0] if dates_with_matches else unique_dates[0]

    filtered_all = [r for r in summary_rows if r.parent_match_id is None]

    # Progression & Provisional Check using in-memory summary rows (0 extra queries)
    incomplete_dates = {
        r.scheduled_date or r.scheduled_time.date()
        for r in summary_rows
        if r.scheduled_time and r.status != 'completed'
    }
    earlier_pending = [
        r
        for r in summary_rows
        if r.scheduled_time
        and active_date
        and (r.scheduled_date or r.scheduled_time.date()) < active_date
        and r.status != 'completed'
    ]
    earlier_pending_count = len(earlier_pending)
    is_provisional = earlier_pending_count > 0

    current_day_number = (
        (unique_dates.index(active_date) + 1)
        if (active_date and active_date in unique_dates)
        else 1
    )
    previous_day_number = max(1, current_day_number - 1)
    previous_day_label = f"Day {previous_day_number}"

    # Map max round per category for knockout round naming from summary rows
    max_rounds_by_cat: dict[int | None, int] = {}
    for r in summary_rows:
        if r.match_type not in ('group_stage', 'round_robin'):
            cid = r.category_id
            if cid not in max_rounds_by_cat or r.round > max_rounds_by_cat[cid]:
                max_rounds_by_cat[cid] = r.round

    # 2. FULL HYDRATION ONLY FOR ACTIVE DATE MATCHES (~27 matches instead of all 689)
    active_query = (
        Match.query.options(
            db.joinedload(Match.participant1),
            db.joinedload(Match.participant2),
            db.joinedload(Match.p1_player1),
            db.joinedload(Match.p1_player2),
            db.joinedload(Match.p2_player1),
            db.joinedload(Match.p2_player2),
        )
        .filter_by(tournament_id=tournament.id)
        .filter(
            Match.parent_match_id.is_(None),
            Match.scheduled_time.isnot(None),
            Match.court_name.isnot(None),
        )
    )
    if active_date:
        active_query = active_query.filter(
            db.or_(
                Match.scheduled_date == active_date,
                db.and_(
                    Match.scheduled_date.is_(None),
                    db.func.date(Match.scheduled_time) == active_date,
                ),
            )
        )
    matches = active_query.order_by(Match.scheduled_time).all()

    # Pre-fetch player lookup cache SCOPED strictly to active matches (prevents global player table dump)
    active_player_names = set()
    active_participant_ids = set()
    for m in matches:
        for p in [m.participant1, m.participant2]:
            if p:
                active_participant_ids.add(p.id)
                if p.name and p.name not in ('TBD', 'Bye', '') and not p.player_id:
                    for sep in [' / ', '/', ' & ']:
                        if sep in p.name:
                            parts = [x.strip() for x in p.name.split(sep, 1)]
                            active_player_names.update(parts)
                            break
                    else:
                        active_player_names.add(p.name.strip())
                if p.partner_name and not getattr(p, 'player2_id', None):
                    active_player_names.add(p.partner_name.strip())

    player_cache: dict[str, int | None] = {name: None for name in active_player_names}
    if active_player_names:
        for pid, name in (
            db.session.query(Player.id, Player.name)
            .filter(Player.name.in_(active_player_names))
            .all()
        ):
            player_cache[name] = pid

    # Pre-fetch team participant IDs in a single query to eliminate N+1 queries on team_members
    team_participant_ids = set()
    if active_participant_ids:
        team_participant_ids = {
            pid
            for (pid,) in db.session.query(TeamMember.participant_id)
            .filter(TeamMember.participant_id.in_(active_participant_ids))
            .distinct()
            .all()
        }

    def get_match_round_name(m: Match) -> str:
        b_type = getattr(m, 'bracket_type', None)
        if b_type in ('grand_finals', 'grand_final'):
            return "Grand Final"
        elif b_type == 'third_place':
            return "3rd Place"

        if getattr(m, 'rubber_type', None):
            rubber_lbl = (
                "Singles"
                if m.rubber_type == 'singles'
                else ("Doubles 1" if m.rubber_type == 'doubles_1' else "Doubles 2")
            )
            if m.group_id and m.group_id in groups:
                return f"{groups[m.group_id].name} ({rubber_lbl})"
            return f"Rubber ({rubber_lbl})"

        if m.group_id and m.group_id in groups:
            return groups[m.group_id].name

        if m.match_type == 'group_stage':
            return f"Group Stage (R{m.round})"
        elif m.match_type == 'round_robin':
            return f"Round {m.round}"
        else:
            max_r = max_rounds_by_cat.get(m.category_id, 1)
            if m.round == max_r:
                return "Final"
            elif m.round == max_r - 1 and max_r >= 2:
                return "Semi-Final"
            elif m.round == max_r - 2 and max_r >= 3:
                return "Quarter-Final"
            else:
                return f"Round {m.round}"

    # Group active matches by court
    order: dict[str, list] = {}
    for match in matches:
        court = match.court_name
        if court not in order:
            order[court] = []

        cat = categories.get(match.category_id)
        cat_name = cat.name if cat else "Tournament Match"

        p1 = match.participant1.name if match.participant1 else "TBD"
        p2 = match.participant2.name if match.participant2 else "TBD"

        p1_player_id = match.participant1.player_id if match.participant1 else None
        p2_player_id = match.participant2.player_id if match.participant2 else None

        sub_count = sub_counts.get(match.id, 0)
        is_team = bool(
            sub_count > 0
            or (cat and cat.format == 'group_stage')
            or (match.participant1 and getattr(match.participant1, 'participant_type', None) == 'team')
            or (match.participant1 and match.participant1.id in team_participant_ids)
        )

        if is_team:
            p1_players = [{"name": p1, "player_id": None, "is_team": True}]
            p2_players = [{"name": p2, "player_id": None, "is_team": True}]
        else:
            p1_players = extract_participant_players(match.participant1, player_cache=player_cache)
            p2_players = extract_participant_players(match.participant2, player_cache=player_cache)

        if getattr(match, 'rubber_type', None):
            p1_assigned = [p for p in [match.p1_player1, match.p1_player2] if p]
            p2_assigned = [p for p in [match.p2_player1, match.p2_player2] if p]
            if p1_assigned:
                p1_players = [{"id": p.id, "name": p.name} for p in p1_assigned]
            if p2_assigned:
                p2_players = [{"id": p.id, "name": p.name} for p in p2_assigned]

        time_str = match.scheduled_time.strftime("%H:%M") if match.scheduled_time else "TBD"
        is_nb = getattr(match, 'is_not_before', False)
        is_evening = bool(match.scheduled_time and match.scheduled_time.time() >= evening_cutoff)
        session_type = 'evening' if is_evening else 'day'
        session_label = 'Evening Session' if is_evening else 'Day Session'
        session_icon = '🌙' if is_evening else '☀️'
        is_locked = bool(is_provisional and match.status != 'completed')

        grp_name = (
            groups[match.group_id].name
            if (match.group_id and match.group_id in groups)
            else None
        )

        order[court].append(
            {
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
                "is_locked": is_locked,
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
                "group_name": grp_name,
                "match_number": match.match_number,
                "status": match.status,
                "court": court,
                "is_team": is_team,
                "has_rubbers": (sub_count > 0),
                "sub_matches_count": sub_count,
            }
        )

    # Naturally sort courts (Court 1, Court 2, ...) and wrap in CourtSchedule
    sorted_order = {}
    for court, c_matches in sorted(order.items()):
        day_m = [m for m in c_matches if m.get("session") == "day"]
        eve_m = [m for m in c_matches if m.get("session") == "evening"]
        sorted_order[court] = CourtSchedule(c_matches, day_m, eve_m)

    # Build days metadata list for UI tabs: count displayed fixtures and child rubbers from summary
    fixtures_per_date: dict[date, int] = {}
    rubbers_per_date: dict[date, int] = {}
    day_matches_per_date: dict[date, int] = {}
    eve_matches_per_date: dict[date, int] = {}

    for r in filtered_all:
        if r.scheduled_time:
            d = r.scheduled_date or r.scheduled_time.date()
            fixtures_per_date[d] = fixtures_per_date.get(d, 0) + 1
            s_cnt = sub_counts.get(r.id, 0)
            rubbers_per_date[d] = rubbers_per_date.get(d, 0) + s_cnt
            if r.scheduled_time.time() < evening_cutoff:
                day_matches_per_date[d] = day_matches_per_date.get(d, 0) + 1
            else:
                eve_matches_per_date[d] = eve_matches_per_date.get(d, 0) + 1

    days_meta = []
    for idx, d in enumerate(unique_dates):
        count = fixtures_per_date.get(d, 0)
        rub_count = rubbers_per_date.get(d, 0)
        day_cnt = day_matches_per_date.get(d, 0)
        eve_cnt = eve_matches_per_date.get(d, 0)
        label = f"Day {idx + 1} ({d.strftime('%d %b')})"
        day_is_provisional = any(inc_d < d for inc_d in incomplete_dates)
        days_meta.append(
            {
                "date": d,
                "date_str": d.strftime("%Y-%m-%d"),
                "label": label,
                "match_count": count,
                "rubbers_count": rub_count,
                "day_session_count": day_cnt,
                "evening_session_count": eve_cnt,
                "is_active": (d == active_date),
                "is_provisional": day_is_provisional,
            }
        )

    # Discover active day's operating hours
    active_day_start = tournament.court_operating_start or "09:00"
    active_day_end = tournament.court_operating_end or "19:00"
    if active_date:
        act_sched = get_tournament_daily_schedule(tournament, [active_date]).get(active_date)
        if act_sched:
            active_day_start = act_sched["start"].strftime("%H:%M")
            active_day_end = act_sched["end"].strftime("%H:%M")

    # Active day session totals across all courts
    active_day_matches = (
        [
            m
            for m in matches
            if m.scheduled_time
            and (m.scheduled_date or m.scheduled_time.date()) == active_date
        ]
        if active_date
        else matches
    )
    total_day_session = sum(
        1
        for m in active_day_matches
        if m.scheduled_time and m.scheduled_time.time() < evening_cutoff
    )
    total_evening_session = sum(
        1
        for m in active_day_matches
        if m.scheduled_time and m.scheduled_time.time() >= evening_cutoff
    )

    total_rubbers = sum(sub_counts.values())

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
        "total_matches_scheduled": len(filtered_all),
        "total_rubbers_scheduled": total_rubbers,
        "is_provisional": is_provisional,
        "earlier_pending_count": earlier_pending_count,
        "current_day_number": current_day_number,
        "previous_day_number": previous_day_number,
        "previous_day_label": previous_day_label,
    }
