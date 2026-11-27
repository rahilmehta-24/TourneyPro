import re
from app.services.format_engine.base import TournamentFormat
from app.domain.models import Match, Participant, db


class RoundRobinFormat(TournamentFormat):
    name = "Round Robin (League)"
    description = "Everyone plays everyone. Rankings are based on matches won followed by head-to-head and mini-league tiebreakers."
    icon = "🔄"
    min_participants = 3

    @classmethod
    def generate_fixtures_circle_method(cls, participants, category=None):
        """
        Generate round-robin fixtures using the Berger / circle method.
        For N participants:
        - If N is odd, adds a dummy Bye slot so every round has a bye.
        - Rotates N-1 participants around a fixed anchor.
        - Assigns distinct round numbers 1..N-1.
        - Tags the final round with is_final_group_round=True.
        """
        n = len(participants)
        if n < 2:
            return []

        items = list(participants)
        if n % 2 != 0:
            items.append(None)  # Dummy participant for Bye

        total_participants = len(items)
        rounds_count = total_participants - 1
        half = total_participants // 2
        matches = []
        match_number = 1

        current_items = list(items)
        for r in range(rounds_count):
            round_num = r + 1
            is_final = (round_num == rounds_count)

            for i in range(half):
                p1 = current_items[i]
                p2 = current_items[total_participants - 1 - i]

                # If neither is None, create a match
                if p1 is not None and p2 is not None:
                    match_data = {
                        "round": round_num,
                        "match_number": match_number,
                        "participant1_id": p1.id,
                        "participant2_id": p2.id,
                        "bracket_type": "main",
                        "match_type": "round_robin" if (not category or category.format == "round_robin") else "group_stage",
                        "match_stage": "group",
                        "is_final_group_round": is_final,
                        "status": "pending",
                    }
                    if category:
                        match_data["category_id"] = category.id
                        if category.scoring_format:
                            match_data["scoring_format"] = category.scoring_format
                        if category.points_to_win:
                            match_data["points_to_win"] = category.points_to_win
                        if category.games_per_set:
                            match_data["games_per_set"] = category.games_per_set
                        if category.win_by_margin:
                            match_data["win_by_margin"] = category.win_by_margin
                        if category.score_cap:
                            match_data["score_cap"] = category.score_cap

                    matches.append(match_data)
                    match_number += 1

            # Rotate: current_items[0] stays, rest rotates clockwise
            current_items = [current_items[0]] + [current_items[-1]] + current_items[1:-1]

        return matches

    @classmethod
    def generate(cls, category, participants):
        return cls.generate_fixtures_circle_method(participants, category=category)

    @classmethod
    def advance_match(cls, match, category, winner_id=None):
        if match.match_type == "knockout":
            from app.services.format_engine.single_elimination.logic import (
                SingleEliminationFormat,
            )

            SingleEliminationFormat.advance_match(match, category, winner_id)

            if getattr(category, "has_third_place_match", False) and getattr(match, "match_stage", None) == "semifinal":
                tp_match = Match.query.filter_by(
                    category_id=category.id,
                    bracket_type="third_place",
                ).first()
                if tp_match:
                    loser_id = (
                        match.participant2_id
                        if winner_id == match.participant1_id
                        else match.participant1_id
                    )
                    if match.match_number % 2 == 1:
                        tp_match.participant1_id = loser_id
                    else:
                        tp_match.participant2_id = loser_id
                db.session.commit()

            final_match = Match.query.filter_by(
                category_id=category.id,
                match_type="knockout",
                match_stage="final",
            ).first()
            if final_match and final_match.status == "completed" and final_match.winner_id:
                SingleEliminationFormat.calculate_final_rankings(category)

        elif match.match_type in ["group_stage", "round_robin"]:
            if match.group_id:
                from app.services.format_engine.group_stage.logic import GroupStageFormat

                GroupStageFormat.calculate_group_standings(match.group_id)
            from app.services.leaderboard import recalculate_all_group_stats

            recalculate_all_group_stats(category.id)

    @staticmethod
    def parse_match_score(match, p_id, category=None):
        """
        Parse match score for participant p_id.
        Returns: (sets_won, sets_lost, games_won, games_lost, points_won, points_lost, is_wo)
        Supports:
        - Points-based matches (Mode A, e.g. "21-17", "25-23", "21")
        - Games-based matches (Mode B, e.g. "6-4, 4-6, [10-7]", "6-3")
        - Walkovers (e.g. "w/o", "walkover") -> credit full target to 0
        - Retirements (e.g. "ret", "default") -> credit winner to full target
        """
        is_p1 = (match.participant1_id == p_id)
        s1_raw = str(match.score1 or "").strip()
        s2_raw = str(match.score2 or "").strip()
        combined_raw = (s1_raw + " " + s2_raw).lower()

        is_wo = any(term in combined_raw for term in ["w/o", "walkover", "default"])
        is_ret = any(term in combined_raw for term in ["ret", "retired", "inj"])

        # Determine scoring format
        scoring_format = getattr(match, "scoring_format", None)
        if not scoring_format and category:
            scoring_format = getattr(category, "scoring_format", None)

        # Determine target
        if scoring_format == "points":
            target = getattr(match, "points_to_win", None) or (category.points_to_win if category else 21) or 21
        else:
            target = getattr(match, "games_per_set", None) or (category.games_per_set if category else 6) or 6

        # 1. Handle Walkover
        if is_wo:
            is_winner = (match.winner_id == p_id)
            if scoring_format == "points":
                pw = target if is_winner else 0
                pl = 0 if is_winner else target
                return (1 if is_winner else 0, 0 if is_winner else 1, 0, 0, pw, pl, True)
            else:
                gw = target if is_winner else 0
                gl = 0 if is_winner else target
                return (1 if is_winner else 0, 0 if is_winner else 1, gw, gl, gw, gl, True)

        # 2. Check if Points-based single score (e.g. "21-17", "12-8 RET" or s1="21", s2="17")
        hyphen_m = re.search(r"(\d+)\s*[-:]\s*(\d+)", s1_raw)
        if hyphen_m and (scoring_format == "points" or int(hyphen_m.group(1)) >= 10 or int(hyphen_m.group(2)) >= 10):
            p1_pts = int(hyphen_m.group(1))
            p2_pts = int(hyphen_m.group(2))
            pw = p1_pts if is_p1 else p2_pts
            pl = p2_pts if is_p1 else p1_pts

            if is_ret and match.winner_id == p_id and pw < target:
                pw = target

            is_winner = (match.winner_id == p_id) if match.winner_id else (pw > pl)
            sw = 1 if is_winner else 0
            sl = 0 if is_winner else 1
            return (sw, sl, 0, 0, pw, pl, is_ret)

        # Single numeric score in s1_raw and optional s2_raw (e.g. s1="21", s2="17")
        if (
            s1_raw.isdigit()
            and (not s2_raw or s2_raw.isdigit())
            and "," not in s1_raw
            and "-" not in s1_raw
        ):
            p1_pts = int(s1_raw)
            p2_pts = int(s2_raw) if s2_raw.isdigit() else 0
            pw = p1_pts if is_p1 else p2_pts
            pl = p2_pts if is_p1 else p1_pts

            if is_ret and match.winner_id == p_id and pw < target:
                pw = target

            is_winner = (match.winner_id == p_id) if match.winner_id else (pw > pl)
            sw = 1 if is_winner else 0
            sl = 0 if is_winner else 1
            return (sw, sl, pw if scoring_format == "games" else 0, pl if scoring_format == "games" else 0, pw, pl, is_ret)

        # 3. Tennis set scores: e.g. "6-4, 4-6, [10-7]" or "6-4"
        sets_won = 0
        sets_lost = 0
        games_won = 0
        games_lost = 0

        set_tokens = [t.strip() for t in re.split(r"[,/]+", s1_raw) if t.strip()]
        for token in set_tokens:
            m = re.search(r"\[?(\d+)[-: ](\d+)\]?", token)
            if m:
                g1, g2 = int(m.group(1)), int(m.group(2))
                gw = g1 if is_p1 else g2
                gl = g2 if is_p1 else g1
                # Super tiebreak: e.g. [10-7]
                if "[" in token or "]" in token or (g1 >= 10 and g2 >= 10):
                    if gw > gl:
                        sets_won += 1
                        games_won += 1
                    elif gl > gw:
                        sets_lost += 1
                        games_lost += 1
                else:
                    if gw > gl:
                        sets_won += 1
                    elif gl > gw:
                        sets_lost += 1
                    games_won += gw
                    games_lost += gl

        # Retirement adjustment in games
        if is_ret and match.winner_id == p_id and games_won < target and sets_won == 0:
            games_won = target
            sets_won = 1

        # Fallback if sets were not parsed from string
        if sets_won == 0 and sets_lost == 0 and match.winner_id:
            if match.winner_id == p_id:
                sets_won = 1
                games_won = target
            else:
                sets_lost = 1
                games_lost = target

        return (sets_won, sets_lost, games_won, games_lost, games_won, games_lost, is_ret)

    @classmethod
    def break_round_robin_tie(cls, tied_stats, matches, scoring_mode="games", category=None):
        """
        Recursive tiebreak procedure compliant with international lawn tennis tournament rules:
        - len == 1: resolved
        - len == 2: Head-to-Head between the two tied players
        - len >= 3: Mini-table among tied players only:
            * Mode A (points):
                1. Mini-table point difference
                2. Mini-table total points scored
            * Mode B (games):
                1. Mini-table set difference (if sets used)
                2. Mini-table game difference
                3. Mini-table total games won
            * If partially resolved into smaller subsets:
                - Subsets of size 2 resolve via Head-to-Head!
                - Subsets of size 1 are resolved.
            * If mini-table fails to separate the tie:
                - Fall back to the full group record:
                  Mode A: Overall point diff -> Overall total points -> Seed
                  Mode B: Overall set diff -> Overall game diff -> Overall total games -> Seed
        """
        if len(tied_stats) <= 1:
            return tied_stats

        tied_ids = {s["participant"].id for s in tied_stats}

        # 2-way tie: Direct Head-to-Head
        if len(tied_stats) == 2:
            p1_id = tied_stats[0]["participant"].id
            p2_id = tied_stats[1]["participant"].id
            h2h_match = next(
                (
                    m
                    for m in matches
                    if m.status == "completed"
                    and m.winner_id
                    and (
                        (m.participant1_id == p1_id and m.participant2_id == p2_id)
                        or (m.participant1_id == p2_id and m.participant2_id == p1_id)
                    )
                ),
                None,
            )

            if h2h_match:
                if h2h_match.winner_id == p1_id:
                    tied_stats[0]["tiebreak"] = "Head-to-head"
                    tied_stats[1]["tiebreak"] = "Head-to-head"
                    return [tied_stats[0], tied_stats[1]]
                elif h2h_match.winner_id == p2_id:
                    tied_stats[0]["tiebreak"] = "Head-to-head"
                    tied_stats[1]["tiebreak"] = "Head-to-head"
                    return [tied_stats[1], tied_stats[0]]

        # 3-way or more: Mini-league among tied players
        if len(tied_stats) >= 3:
            for s in tied_stats:
                s["tiebreak"] = "Mini-league"

            mini_matches = [
                m
                for m in matches
                if m.status == "completed"
                and m.winner_id
                and m.participant1_id in tied_ids
                and m.participant2_id in tied_ids
            ]

            mini_stats = {}
            for s in tied_stats:
                pid = s["participant"].id
                m_wins = 0
                m_sets_w, m_sets_l = 0, 0
                m_games_w, m_games_l = 0, 0
                m_pts_w, m_pts_l = 0, 0

                for mm in mini_matches:
                    if mm.participant1_id == pid or mm.participant2_id == pid:
                        if mm.winner_id == pid:
                            m_wins += 1
                        sw, sl, gw, gl, pw, pl, _ = cls.parse_match_score(mm, pid, category=category)
                        m_sets_w += sw
                        m_sets_l += sl
                        m_games_w += gw
                        m_games_l += gl
                        m_pts_w += pw
                        m_pts_l += pl

                mini_stats[pid] = {
                    "mini_wins": m_wins,
                    "mini_set_diff": m_sets_w - m_sets_l,
                    "mini_game_diff": m_games_w - m_games_l,
                    "mini_games_won": m_games_w,
                    "mini_pts_diff": m_pts_w - m_pts_l,
                    "mini_pts_won": m_pts_w,
                }

            # Sort tied_stats by mini-league criteria
            def mini_key(s):
                pid = s["participant"].id
                ms = mini_stats[pid]
                if scoring_mode == "points":
                    return (
                        -ms["mini_pts_diff"],
                        -ms["mini_pts_won"],
                        -s.get("point_diff", 0),
                        -s.get("points_won", s.get("points", 0)),
                        (s["participant"].manual_seed or s["participant"].seed or 999),
                    )
                else:
                    return (
                        -ms["mini_set_diff"],
                        -ms["mini_game_diff"],
                        -ms["mini_games_won"],
                        -s.get("set_diff", 0),
                        -s.get("game_diff", 0),
                        -s.get("games_won", 0),
                        (s["participant"].manual_seed or s["participant"].seed or 999),
                    )

            sorted_mini = sorted(tied_stats, key=mini_key)

            # Group into sub-buckets by primary mini-league metrics
            groups = []
            current_grp = []
            last_key = None
            for s in sorted_mini:
                pid = s["participant"].id
                ms = mini_stats[pid]
                if scoring_mode == "points":
                    key = (ms["mini_pts_diff"], ms["mini_pts_won"])
                else:
                    key = (ms["mini_set_diff"], ms["mini_game_diff"], ms["mini_games_won"])

                if last_key is None or key == last_key:
                    current_grp.append(s)
                else:
                    groups.append(current_grp)
                    current_grp = [s]
                last_key = key
            if current_grp:
                groups.append(current_grp)

            # If the mini-table successfully separated into 2+ distinct groups
            if len(groups) > 1:
                resolved = []
                for grp in groups:
                    resolved.extend(cls.break_round_robin_tie(grp, matches, scoring_mode=scoring_mode, category=category))
                return resolved

        # Fallback for remaining ties: overall full group metrics
        def fallback_key(s):
            if scoring_mode == "points":
                return (
                    -s.get("point_diff", 0),
                    -s.get("points_won", s.get("points", 0)),
                    (s["participant"].manual_seed or s["participant"].seed or 999),
                )
            else:
                return (
                    -s.get("set_diff", 0),
                    -s.get("game_diff", 0),
                    -s.get("games_won", 0),
                    (s["participant"].manual_seed or s["participant"].seed or 999),
                )

        return sorted(tied_stats, key=fallback_key)

    @classmethod
    def calculate_final_rankings(cls, category, commit=True):
        participants = Participant.query.filter_by(category_id=category.id).all()
        if not participants:
            return []

        matches = Match.query.filter(
            Match.category_id == category.id, Match.parent_match_id.is_(None)
        ).all()

        completed_matches = [m for m in matches if m.status == "completed" and m.winner_id]
        scoring_mode = getattr(category, "scoring_format", "games") or "games"

        stats_list = []
        for p in participants:
            p_matches = [
                m
                for m in completed_matches
                if m.participant1_id == p.id or m.participant2_id == p.id
            ]

            wins = sum(1 for m in p_matches if m.winner_id == p.id)
            losses = sum(1 for m in p_matches if m.winner_id != p.id)

            pts_w, pts_l = 0, 0
            sets_w, sets_l = 0, 0
            games_w, games_l = 0, 0

            for m in p_matches:
                sw, sl, gw, gl, pw, pl, _ = cls.parse_match_score(m, p.id, category=category)
                sets_w += sw
                sets_l += sl
                games_w += gw
                games_l += gl
                pts_w += pw
                pts_l += pl

            p.group_wins = wins
            p.group_losses = losses
            p.group_points = pts_w if scoring_mode == "points" else games_w
            p.group_points_conceded = pts_l if scoring_mode == "points" else games_l
            p.group_point_diff = (pts_w - pts_l) if scoring_mode == "points" else (games_w - games_l)
            p.group_sets_won = sets_w
            p.group_sets_lost = sets_l

            stats_list.append(
                {
                    "participant": p,
                    "played": len(p_matches),
                    "wins": wins,
                    "losses": losses,
                    "points": p.group_points,
                    "display_pts": wins * 3,
                    "points_won": pts_w,
                    "points_lost": pts_l,
                    "point_diff": pts_w - pts_l,
                    "sets_won": sets_w,
                    "sets_lost": sets_l,
                    "set_diff": sets_w - sets_l,
                    "games_won": games_w,
                    "games_lost": games_l,
                    "game_diff": games_w - games_l,
                    "tiebreak": "—",
                }
            )

        # Priority 1: Matches won DESC
        stats_list.sort(key=lambda s: -s["wins"])

        # Group tied participants by wins
        tied_groups = []
        cur_grp = []
        last_wins = None
        for s in stats_list:
            if last_wins is None or s["wins"] == last_wins:
                cur_grp.append(s)
            else:
                tied_groups.append(cur_grp)
                cur_grp = [s]
            last_wins = s["wins"]
        if cur_grp:
            tied_groups.append(cur_grp)

        # Resolve each tied group
        final_ordered = []
        for grp in tied_groups:
            if len(grp) == 1:
                final_ordered.append(grp[0])
            else:
                final_ordered.extend(cls.break_round_robin_tie(grp, completed_matches, scoring_mode=scoring_mode, category=category))

        # Assign final_rank
        for i, s in enumerate(final_ordered):
            s["rank"] = i + 1
            if commit:
                s["participant"].final_rank = i + 1

        if commit:
            db.session.commit()

        return final_ordered
