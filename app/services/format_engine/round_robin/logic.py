import re
from app.services.format_engine.base import TournamentFormat
from app.domain.models import Match, Participant, db

class RoundRobinFormat(TournamentFormat):
    name = "Round Robin (League)"
    description = "Everyone plays everyone. Rankings are based on matches won followed by head-to-head and mini-league tiebreakers."
    icon = "🔄"
    min_participants = 3

    @classmethod
    def generate(cls, category, participants):
        matches = []
        match_number = 1

        for i in range(len(participants)):
            for j in range(i + 1, len(participants)):
                match = {
                    'round': 1,
                    'match_number': match_number,
                    'participant1_id': participants[i].id,
                    'participant2_id': participants[j].id,
                    'bracket_type': 'main',
                    'match_type': 'round_robin'
                }
                matches.append(match)
                match_number += 1

        return matches

    @classmethod
    def advance_match(cls, match, category, winner_id=None):
        pass

    @staticmethod
    def parse_match_score(match, p_id):
        """
        Parse match score for participant p_id.
        Returns: (sets_won, sets_lost, games_won, games_lost, points_won, points_lost)
        Handles match tiebreaks like [10-7] as 1 set and 1 game.
        """
        is_p1 = (match.participant1_id == p_id)
        s1_raw = str(match.score1 or "").strip()
        s2_raw = str(match.score2 or "").strip()

        # Check walkover/retirement
        is_wo = any(term in (s1_raw + s2_raw).lower() for term in ['w/o', 'walkover', 'ret', 'default'])

        # Check if numeric single point score (e.g. "11", "5")
        if s1_raw.isdigit() and (not s2_raw or s2_raw.isdigit()) and ',' not in s1_raw and '-' not in s1_raw:
            p1_pts = int(s1_raw)
            p2_pts = int(s2_raw) if s2_raw.isdigit() else 0
            pw = p1_pts if is_p1 else p2_pts
            pl = p2_pts if is_p1 else p1_pts
            sw = 1 if match.winner_id == p_id else 0
            sl = 0 if match.winner_id == p_id else 1
            return sw, sl, pw, pl, pw, pl, is_wo

        # Tennis set scores: e.g. "6-4, 4-6, [10-7]" or "6-4, 4-6, 10-8"
        sets_won = 0
        sets_lost = 0
        games_won = 0
        games_lost = 0

        # Try parsing comma-separated sets
        set_tokens = [t.strip() for t in re.split(r'[,/]+', s1_raw) if t.strip()]
        for token in set_tokens:
            m = re.search(r'\[?(\d+)[-: ](\d+)\]?', token)
            if m:
                g1, g2 = int(m.group(1)), int(m.group(2))
                gw = g1 if is_p1 else g2
                gl = g2 if is_p1 else g1
                # Super tiebreak: e.g. [10-7] or any set where scores >= 10 and in brackets or diff >= 2
                if '[' in token or ']' in token or (g1 >= 10 or g2 >= 10):
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

        # If sets were not parsed from comma-separated string, fallback to match winner
        if sets_won == 0 and sets_lost == 0 and match.winner_id:
            if match.winner_id == p_id:
                sets_won = 1
                games_won = 6
            else:
                sets_lost = 1
                games_lost = 6

        return sets_won, sets_lost, games_won, games_lost, games_won, games_lost, is_wo

    @classmethod
    def break_round_robin_tie(cls, tied_stats, matches):
        """
        Recursive tiebreak procedure:
        - len == 1: resolved
        - len == 2: Head-to-Head between the two
        - len >= 3: Mini-league among tied players only (wins, set_diff, game_diff)
        - Fallback: overall set_diff, game_diff, seed
        """
        if len(tied_stats) <= 1:
            return tied_stats

        tied_ids = {s['participant'].id for s in tied_stats}

        # 2-way tie: Direct Head-to-Head
        if len(tied_stats) == 2:
            p1_id = tied_stats[0]['participant'].id
            p2_id = tied_stats[1]['participant'].id
            h2h_match = next((
                m for m in matches
                if m.status == 'completed' and m.winner_id and
                ((m.participant1_id == p1_id and m.participant2_id == p2_id) or
                 (m.participant1_id == p2_id and m.participant2_id == p1_id))
            ), None)

            if h2h_match:
                if h2h_match.winner_id == p1_id:
                    return [tied_stats[0], tied_stats[1]]
                elif h2h_match.winner_id == p2_id:
                    return [tied_stats[1], tied_stats[0]]

        # 3-way or more: Mini-league among tied players
        if len(tied_stats) >= 3:
            mini_matches = [
                m for m in matches
                if m.status == 'completed' and m.winner_id and
                m.participant1_id in tied_ids and m.participant2_id in tied_ids
            ]

            mini_stats = {}
            for s in tied_stats:
                pid = s['participant'].id
                m_wins = 0
                m_sets_w, m_sets_l = 0, 0
                m_games_w, m_games_l = 0, 0
                for mm in mini_matches:
                    if mm.participant1_id == pid or mm.participant2_id == pid:
                        if mm.winner_id == pid:
                            m_wins += 1
                        sw, sl, gw, gl, _, _, is_wo = cls.parse_match_score(mm, pid)
                        if not is_wo:
                            m_sets_w += sw
                            m_sets_l += sl
                            m_games_w += gw
                            m_games_l += gl

                mini_stats[pid] = {
                    'mini_wins': m_wins,
                    'mini_set_diff': m_sets_w - m_sets_l,
                    'mini_game_diff': m_games_w - m_games_l,
                }

            # Sort tied_stats by mini-league criteria
            def mini_key(s):
                pid = s['participant'].id
                ms = mini_stats[pid]
                return (
                    -ms['mini_wins'],
                    -ms['mini_set_diff'],
                    -ms['mini_game_diff'],
                    -s['set_diff'],
                    -s['game_diff'],
                    -(s['points']),
                    (s['participant'].manual_seed or s['participant'].seed or 999)
                )

            sorted_mini = sorted(tied_stats, key=mini_key)

            # Group by mini-league tuple to check if partially resolved
            groups = []
            current_grp = []
            last_key = None
            for s in sorted_mini:
                pid = s['participant'].id
                ms = mini_stats[pid]
                key = (ms['mini_wins'], ms['mini_set_diff'], ms['mini_game_diff'])
                if last_key is None or key == last_key:
                    current_grp.append(s)
                else:
                    groups.append(current_grp)
                    current_grp = [s]
                last_key = key
            if current_grp:
                groups.append(current_grp)

            if len(groups) > 1:
                resolved = []
                for grp in groups:
                    resolved.extend(cls.break_round_robin_tie(grp, matches))
                return resolved

        # Fallback for remaining ties: overall set_diff, game_diff, points, seed
        def fallback_key(s):
            return (
                -s['set_diff'],
                -s['game_diff'],
                -s['points'],
                (s['participant'].manual_seed or s['participant'].seed or 999)
            )

        return sorted(tied_stats, key=fallback_key)

    @classmethod
    def calculate_final_rankings(cls, category):
        participants = Participant.query.filter_by(category_id=category.id).all()
        if not participants:
            return

        matches = Match.query.filter(
            Match.category_id == category.id,
            Match.parent_match_id.is_(None)
        ).all()

        completed_matches = [m for m in matches if m.status == 'completed' and m.winner_id]

        stats_list = []
        for p in participants:
            p_matches = [
                m for m in completed_matches
                if m.participant1_id == p.id or m.participant2_id == p.id
            ]

            wins = sum(1 for m in p_matches if m.winner_id == p.id)
            losses = sum(1 for m in p_matches if m.winner_id != p.id)

            total_pts = 0
            sets_w, sets_l = 0, 0
            games_w, games_l = 0, 0

            for m in p_matches:
                sw, sl, gw, gl, pw, pl, is_wo = cls.parse_match_score(m, p.id)
                sets_w += sw
                sets_l += sl
                games_w += gw
                games_l += gl
                total_pts += pw

            p.group_wins = wins
            p.group_losses = losses
            p.group_points = total_pts

            stats_list.append({
                'participant': p,
                'wins': wins,
                'losses': losses,
                'points': total_pts,
                'set_diff': sets_w - sets_l,
                'game_diff': games_w - games_l,
            })

        # Group by matches won (Priority 1: Matches won DESC)
        stats_list.sort(key=lambda s: -s['wins'])

        # Group tied participants by wins
        tied_groups = []
        cur_grp = []
        last_wins = None
        for s in stats_list:
            if last_wins is None or s['wins'] == last_wins:
                cur_grp.append(s)
            else:
                tied_groups.append(cur_grp)
                cur_grp = [s]
            last_wins = s['wins']
        if cur_grp:
            tied_groups.append(cur_grp)

        # Resolve each tied group
        final_ordered = []
        for grp in tied_groups:
            final_ordered.extend(cls.break_round_robin_tie(grp, completed_matches))

        # Assign final_rank
        for i, s in enumerate(final_ordered):
            s['participant'].final_rank = i + 1

        db.session.commit()
