import functools
import random
from app.domain.models import db, Match, Participant, Group
from app.services.format_engine.base import TournamentFormat


class GroupStageFormat(TournamentFormat):
    name = "Group Stage + Knockout"
    description = "Round-robin group matches followed by a single elimination knockout bracket for top qualifiers."
    icon = "🎪"
    min_participants = 4

    @classmethod
    def generate(cls, category, participants):
        num_groups = category.num_groups or 1
        teams_per_group = category.teams_per_group
        matches_per_pair = category.matches_per_team_pair or 1

        # Check if participants has teams
        teams_exist = any(getattr(p, 'is_team', False) for p in participants)
        active_participants = [p for p in participants if p.is_team] if teams_exist else participants

        groups = []
        for i in range(num_groups):
            group = Group(
                category_id=category.id,
                name=f"Group {chr(65 + i)}"
            )
            db.session.add(group)
            db.session.flush()
            groups.append(group)

        participants_sorted = sorted(active_participants, key=lambda p: p.manual_seed or p.seed or 999)

        num_participants = len(participants_sorted)
        if num_groups > 0:
            base_size = num_participants // num_groups
            remainder = num_participants % num_groups

            target_sizes = []
            remaining = num_participants
            for idx in range(num_groups):
                if teams_per_group:
                    if remaining >= teams_per_group:
                        target_sizes.append(teams_per_group)
                        remaining -= teams_per_group
                    else:
                        target_sizes.append(remaining)
                        remaining = 0
                else:
                    size = base_size + (1 if idx < remainder else 0)
                    target_sizes.append(size)
                    remaining -= size

            group_counts = [0] * num_groups

            snake_order = []
            for round_num in range(num_participants):
                if round_num % 2 == 0:
                    snake_order.extend(range(num_groups))
                else:
                    snake_order.extend(reversed(range(num_groups)))

            snake_idx = 0
            assigned_count = 0
            total_capacity = sum(target_sizes)

            for participant in participants_sorted:
                if assigned_count >= total_capacity:
                    break

                while snake_idx < len(snake_order):
                    candidate_group = snake_order[snake_idx]
                    snake_idx += 1
                    if group_counts[candidate_group] < target_sizes[candidate_group]:
                        participant.group_id = groups[candidate_group].id
                        group_counts[candidate_group] += 1
                        assigned_count += 1
                        break

        db.session.commit()

        # Delete empty groups
        active_groups = []
        for group in groups:
            group_participants = [p for p in active_participants if p.group_id == group.id]
            if len(group_participants) == 0:
                db.session.delete(group)
            else:
                active_groups.append(group)
        db.session.commit()

        matches = []
        match_number = 1
        total_games_setting = category.total_games or 7

        for group in active_groups:
            group_participants = [p for p in active_participants if p.group_id == group.id]

            for i in range(len(group_participants)):
                for j in range(i + 1, len(group_participants)):
                    p1 = group_participants[i]
                    p2 = group_participants[j]

                    for match_iteration in range(matches_per_pair):
                        parent_tie = {
                            'category_id': category.id,
                            'group_id': group.id,
                            'round': match_iteration + 1,
                            'match_number': match_number,
                            'participant1_id': p1.id,
                            'participant2_id': p2.id,
                            'match_type': 'group_stage',
                            'scoring_format': 'games',
                            'total_games': total_games_setting,
                            'child_rubbers': [
                                {
                                    'round': match_iteration + 1,
                                    'match_number': 1,
                                    'rubber_number': 1,
                                    'rubber_type': 'singles',
                                    'participant1_id': p1.id,
                                    'participant2_id': p2.id,
                                    'match_type': 'group_stage',
                                    'scoring_format': 'games',
                                    'total_games': total_games_setting
                                },
                                {
                                    'round': match_iteration + 1,
                                    'match_number': 2,
                                    'rubber_number': 2,
                                    'rubber_type': 'doubles_1',
                                    'participant1_id': p1.id,
                                    'participant2_id': p2.id,
                                    'match_type': 'group_stage',
                                    'scoring_format': 'games',
                                    'total_games': total_games_setting
                                },
                                {
                                    'round': match_iteration + 1,
                                    'match_number': 3,
                                    'rubber_number': 3,
                                    'rubber_type': 'doubles_2',
                                    'participant1_id': p1.id,
                                    'participant2_id': p2.id,
                                    'match_type': 'group_stage',
                                    'scoring_format': 'games',
                                    'total_games': total_games_setting
                                }
                            ]
                        }
                        matches.append(parent_tie)
                        match_number += 1

        return matches

    @classmethod
    def advance_match(cls, match, category, winner_id=None):
        """Advances winner in knockout stage, keeping rubbers synchronized."""
        if match.match_type != 'knockout':
            return

        winner_id = winner_id or match.winner_id
        if not winner_id:
            return

        # Find next round match in bracket
        # QF (round 1) -> SF (round 2) -> Final (round 3)
        current_round = match.round
        next_round = current_round + 1

        # Determine target match number in next round
        # Match 1, 2 feed into Match 5 (SF 1)
        # Match 3, 4 feed into Match 6 (SF 2)
        # Match 5, 6 feed into Match 7 (Final)
        all_knockout_matches = Match.query.filter_by(
            category_id=category.id,
            match_type='knockout',
            parent_match_id=None
        ).order_by(Match.round, Match.match_number).all()

        next_round_matches = [m for m in all_knockout_matches if m.round == next_round]
        if not next_round_matches:
            return

        current_round_matches = [m for m in all_knockout_matches if m.round == current_round]
        try:
            match_idx = current_round_matches.index(match)
        except ValueError:
            return

        target_match_idx = match_idx // 2
        is_p1 = (match_idx % 2 == 0)

        if target_match_idx < len(next_round_matches):
            target_match = next_round_matches[target_match_idx]
            if is_p1:
                target_match.participant1_id = winner_id
            else:
                target_match.participant2_id = winner_id

            # Also update participant IDs on child rubbers of the target tie
            sub_rubbers = Match.query.filter_by(parent_match_id=target_match.id).all()
            for rubber in sub_rubbers:
                if is_p1:
                    rubber.participant1_id = winner_id
                else:
                    rubber.participant2_id = winner_id

            db.session.commit()

    @classmethod
    def calculate_final_rankings(cls, category):
        from app.services.format_engine.single_elimination.logic import SingleEliminationFormat
        SingleEliminationFormat.calculate_final_rankings(category)

    @staticmethod
    def _parse_rubber_games(score_str):
        """Parses games won from a scoreline like '4-3(5)' or '6-1'."""
        if not score_str:
            return 0, 0
        try:
            parts = str(score_str).split('-')
            if len(parts) >= 2:
                g1_part = parts[0].strip()
                g2_part = parts[1].split('(')[0].strip()
                return int(g1_part), int(g2_part)
        except (ValueError, IndexError):
            pass
        return 0, 0

    @classmethod
    def calculate_group_standings(cls, group_id):
        all_participants = Participant.query.filter_by(group_id=group_id).all()
        # If teams exist, evaluate standings on teams only
        has_teams = any(p.is_team for p in all_participants)
        participants = [p for p in all_participants if p.is_team] if has_teams else all_participants

        # Reset counters
        for p in participants:
            p.group_wins = 0      # Ties won
            p.group_losses = 0    # Ties lost
            p.group_points = 0    # Total games won across all rubbers
            p.rubbers_won = 0
            p.rubbers_lost = 0
            p.games_won = 0
            p.games_lost = 0
            p.ties_played = 0

        # Query parent ties in this group
        parent_ties = Match.query.filter(
            Match.group_id == group_id,
            Match.parent_match_id.is_(None),
            Match.match_type.in_(['group_stage', 'round_robin', 'doubles_round_robin'])
        ).all()

        for tie in parent_ties:
            p1 = next((p for p in participants if p.id == tie.participant1_id), None)
            p2 = next((p for p in participants if p.id == tie.participant2_id), None)
            if not p1 or not p2:
                continue

            sub_rubbers = Match.query.filter_by(parent_match_id=tie.id).all()

            if sub_rubbers:
                tie_p1_rubbers = 0
                tie_p2_rubbers = 0
                tie_p1_games = 0
                tie_p2_games = 0

                for r in sub_rubbers:
                    if r.score1:
                        g1, g2 = cls._parse_rubber_games(r.score1)
                        tie_p1_games += g1
                        tie_p2_games += g2
                        p1.games_won += g1
                        p1.games_lost += g2
                        p2.games_won += g2
                        p2.games_lost += g1

                    if r.status == 'completed' and r.winner_id:
                        if r.winner_id == p1.id:
                            tie_p1_rubbers += 1
                            p1.rubbers_won += 1
                            p2.rubbers_lost += 1
                        elif r.winner_id == p2.id:
                            tie_p2_rubbers += 1
                            p2.rubbers_won += 1
                            p1.rubbers_lost += 1

                # Update tie completed state if all rubbers completed or winner decided
                if tie_p1_rubbers >= 2 or tie_p2_rubbers >= 2:
                    if tie_p1_rubbers > tie_p2_rubbers:
                        tie.winner_id = p1.id
                    else:
                        tie.winner_id = p2.id

                    if all(r.status == 'completed' for r in sub_rubbers):
                        tie.status = 'completed'

                tie.score1 = f"{tie_p1_rubbers}-{tie_p2_rubbers} ({tie_p1_games}g)"
                tie.score2 = f"{tie_p2_rubbers}-{tie_p1_rubbers} ({tie_p2_games}g)"

                if tie.status == 'completed' and tie.winner_id:
                    p1.ties_played += 1
                    p2.ties_played += 1
                    if tie.winner_id == p1.id:
                        p1.group_wins += 1
                        p2.group_losses += 1
                    else:
                        p2.group_wins += 1
                        p1.group_losses += 1

            else:
                # Legacy single match scoring
                if tie.score1 and tie.score2:
                    try:
                        s1 = int(tie.score1.split('-')[0].split('(')[0])
                        s2 = int(tie.score2.split('-')[0].split('(')[0])
                        p1.games_won += s1
                        p1.games_lost += s2
                        p2.games_won += s2
                        p2.games_lost += s1
                    except (ValueError, IndexError):
                        pass

                if tie.status == 'completed' and tie.winner_id:
                    p1.ties_played += 1
                    p2.ties_played += 1
                    if tie.winner_id == p1.id:
                        p1.group_wins += 1
                        p2.group_losses += 1
                    else:
                        p2.group_wins += 1
                        p1.group_losses += 1

        # Points equal total games won
        for p in participants:
            p.group_points = p.games_won
            p.games_diff = p.games_won - p.games_lost
            p.rubbers_diff = p.rubbers_won - p.rubbers_lost

        db.session.commit()

        # Head-to-Head Comparator
        completed_ties = [m for m in parent_ties if m.status == 'completed' and m.winner_id]

        def compare_teams(t1, t2):
            # 1. Primary: Total Points (Total Games Won)
            if t1.group_points != t2.group_points:
                return 1 if t1.group_points > t2.group_points else -1

            # 2. Tied on points: Head-to-Head Result
            h2h = next((m for m in completed_ties if (
                (m.participant1_id == t1.id and m.participant2_id == t2.id) or
                (m.participant1_id == t2.id and m.participant2_id == t1.id)
            )), None)
            if h2h and h2h.winner_id:
                if h2h.winner_id == t1.id:
                    return 1
                elif h2h.winner_id == t2.id:
                    return -1

            # 3. Rubbers difference
            if t1.rubbers_diff != t2.rubbers_diff:
                return 1 if t1.rubbers_diff > t2.rubbers_diff else -1

            # 4. Ties won
            if t1.group_wins != t2.group_wins:
                return 1 if t1.group_wins > t2.group_wins else -1

            # 5. Games difference
            if t1.games_diff != t2.games_diff:
                return 1 if t1.games_diff > t2.games_diff else -1

            return 0

        standings = sorted(
            participants,
            key=functools.cmp_to_key(compare_teams),
            reverse=True
        )

        return standings

    @classmethod
    def generate_knockout_from_groups(cls, category, selected_lucky_loser_ids=None):
        """
        Generates 8-team knockout bracket from group qualifiers:
        - Top 2 teams from each group qualify automatically.
        - Lucky Losers chosen from 3rd placed teams.
        - Teams ranked 1 to 8 by group points (total games won).
        - Bracket Placement:
            Line 1: Seed #1 (Top Half Top)
            Line 8: Seed #2 (Bottom Half Bottom)
            Line 4: Seed #3 (Top Half Bottom)
            Line 5: Seed #4 (Bottom Half Top)
            Lines 2, 3, 6, 7: Random draw of Ranks 5, 6, 7, 8.
        """
        groups = Group.query.filter_by(category_id=category.id).all()
        qualifiers_per_group = category.qualifiers_per_group or 2

        automatic_qualifiers = []
        third_placed_teams = []

        for group in groups:
            standings = cls.calculate_group_standings(group.id)
            if len(standings) >= qualifiers_per_group:
                automatic_qualifiers.extend(standings[:qualifiers_per_group])
            else:
                automatic_qualifiers.extend(standings)

            if len(standings) > qualifiers_per_group:
                third_placed_teams.append(standings[qualifiers_per_group])

        # Lucky losers selection
        lucky_losers = []
        slots_needed = 8 - len(automatic_qualifiers)

        if slots_needed > 0 and category.allow_lucky_losers:
            if selected_lucky_loser_ids:
                for ll_id in selected_lucky_loser_ids:
                    match_p = Participant.query.get(int(ll_id))
                    if match_p and match_p not in automatic_qualifiers and match_p not in lucky_losers:
                        lucky_losers.append(match_p)
            else:
                # Default to top 3rd-placed teams by group points
                sorted_3rd = sorted(third_placed_teams, key=lambda t: (-t.group_points, -t.group_wins))
                lucky_losers = sorted_3rd[:slots_needed]

        all_knockout_teams = automatic_qualifiers + lucky_losers

        if len(all_knockout_teams) < 4:
            raise ValueError(f"Need at least 4 qualifying teams for knockout stage (found {len(all_knockout_teams)}).")

        # Rank all qualifiers strictly by group points (games won)
        all_knockout_teams.sort(key=lambda t: (
            -getattr(t, 'group_points', 0),
            -getattr(t, 'rubbers_diff', 0),
            -t.group_wins
        ))

        # Handle 8-team bracket
        if len(all_knockout_teams) >= 8:
            top_8 = all_knockout_teams[:8]
            seed1 = top_8[0]
            seed2 = top_8[1]
            seed3 = top_8[2]
            seed4 = top_8[3]

            seed1.seed = 1
            seed2.seed = 2
            seed3.seed = 3
            seed4.seed = 4

            # Ranks 5-8 are drawn randomly into vacant spots
            unseeded = top_8[4:8]
            random.shuffle(unseeded)

            for i, p in enumerate(unseeded):
                p.seed = 5 + i

            db.session.commit()

            # 8-Line Placement
            # Line 1: Seed 1
            # Line 2: unseeded[0]
            # Line 3: unseeded[1]
            # Line 4: Seed 3
            # Line 5: Seed 4
            # Line 6: unseeded[2]
            # Line 7: unseeded[3]
            # Line 8: Seed 2
            line1, line2 = seed1, unseeded[0]
            line3, line4 = unseeded[1], seed3
            line5, line6 = seed4, unseeded[2]
            line7, line8 = unseeded[3], seed2

            total_games_setting = category.total_games or 7

            def make_rubber_data(r_num, r_type, p1_id, p2_id, rd, mn):
                return {
                    'round': rd,
                    'match_number': mn,
                    'rubber_number': r_num,
                    'rubber_type': r_type,
                    'participant1_id': p1_id,
                    'participant2_id': p2_id,
                    'match_type': 'knockout',
                    'scoring_format': 'games',
                    'total_games': total_games_setting
                }

            qf_pairings = [
                (line1, line2, 1),
                (line3, line4, 2),
                (line5, line6, 3),
                (line7, line8, 4)
            ]

            matches_data = []

            # 1. Quarter-Finals (Round 1)
            for p1, p2, mn in qf_pairings:
                matches_data.append({
                    'category_id': category.id,
                    'round': 1,
                    'match_number': mn,
                    'participant1_id': p1.id if p1 else None,
                    'participant2_id': p2.id if p2 else None,
                    'match_type': 'knockout',
                    'scoring_format': 'games',
                    'total_games': total_games_setting,
                    'child_rubbers': [
                        make_rubber_data(1, 'singles', p1.id if p1 else None, p2.id if p2 else None, 1, 1),
                        make_rubber_data(2, 'doubles_1', p1.id if p1 else None, p2.id if p2 else None, 1, 2),
                        make_rubber_data(3, 'doubles_2', p1.id if p1 else None, p2.id if p2 else None, 1, 3)
                    ]
                })

            # 2. Semi-Finals (Round 2)
            matches_data.append({
                'category_id': category.id,
                'round': 2,
                'match_number': 5,
                'participant1_id': None,
                'participant2_id': None,
                'match_type': 'knockout',
                'scoring_format': 'games',
                'total_games': total_games_setting,
                'child_rubbers': [
                    make_rubber_data(1, 'singles', None, None, 2, 1),
                    make_rubber_data(2, 'doubles_1', None, None, 2, 2),
                    make_rubber_data(3, 'doubles_2', None, None, 2, 3)
                ]
            })
            matches_data.append({
                'category_id': category.id,
                'round': 2,
                'match_number': 6,
                'participant1_id': None,
                'participant2_id': None,
                'match_type': 'knockout',
                'scoring_format': 'games',
                'total_games': total_games_setting,
                'child_rubbers': [
                    make_rubber_data(1, 'singles', None, None, 2, 1),
                    make_rubber_data(2, 'doubles_1', None, None, 2, 2),
                    make_rubber_data(3, 'doubles_2', None, None, 2, 3)
                ]
            })

            # 3. Final (Round 3)
            matches_data.append({
                'category_id': category.id,
                'round': 3,
                'match_number': 7,
                'participant1_id': None,
                'participant2_id': None,
                'match_type': 'knockout',
                'scoring_format': 'games',
                'total_games': total_games_setting,
                'child_rubbers': [
                    make_rubber_data(1, 'singles', None, None, 3, 1),
                    make_rubber_data(2, 'doubles_1', None, None, 3, 2),
                    make_rubber_data(3, 'doubles_2', None, None, 3, 3)
                ]
            })

            return matches_data

        else:
            # 4-Team Bracket (Semi-Finals -> Final)
            top_4 = all_knockout_teams[:4]
            s1 = top_4[0]
            s2 = top_4[1]
            s1.seed = 1
            s2.seed = 2
            unseeded = top_4[2:4]
            random.shuffle(unseeded)

            s1.seed = 1
            unseeded[0].seed = 4
            unseeded[1].seed = 3
            s2.seed = 2
            db.session.commit()

            total_games_setting = category.total_games or 7

            def make_rubber_data(r_num, r_type, p1_id, p2_id, rd, mn):
                return {
                    'round': rd,
                    'match_number': mn,
                    'rubber_number': r_num,
                    'rubber_type': r_type,
                    'participant1_id': p1_id,
                    'participant2_id': p2_id,
                    'match_type': 'knockout',
                    'scoring_format': 'games',
                    'total_games': total_games_setting
                }

            return [
                # SF 1: Seed 1 vs Seed 4
                {
                    'category_id': category.id,
                    'round': 1,
                    'match_number': 1,
                    'participant1_id': s1.id,
                    'participant2_id': unseeded[0].id,
                    'match_type': 'knockout',
                    'scoring_format': 'games',
                    'total_games': total_games_setting,
                    'child_rubbers': [
                        make_rubber_data(1, 'singles', s1.id, unseeded[0].id, 1, 1),
                        make_rubber_data(2, 'doubles_1', s1.id, unseeded[0].id, 1, 2),
                        make_rubber_data(3, 'doubles_2', s1.id, unseeded[0].id, 1, 3)
                    ]
                },
                # SF 2: Seed 3 vs Seed 2
                {
                    'category_id': category.id,
                    'round': 1,
                    'match_number': 2,
                    'participant1_id': unseeded[1].id,
                    'participant2_id': s2.id,
                    'match_type': 'knockout',
                    'scoring_format': 'games',
                    'total_games': total_games_setting,
                    'child_rubbers': [
                        make_rubber_data(1, 'singles', unseeded[1].id, s2.id, 1, 1),
                        make_rubber_data(2, 'doubles_1', unseeded[1].id, s2.id, 1, 2),
                        make_rubber_data(3, 'doubles_2', unseeded[1].id, s2.id, 1, 3)
                    ]
                },
                # Final
                {
                    'category_id': category.id,
                    'round': 2,
                    'match_number': 3,
                    'participant1_id': None,
                    'participant2_id': None,
                    'match_type': 'knockout',
                    'scoring_format': 'games',
                    'total_games': total_games_setting,
                    'child_rubbers': [
                        make_rubber_data(1, 'singles', None, None, 2, 1),
                        make_rubber_data(2, 'doubles_1', None, None, 2, 2),
                        make_rubber_data(3, 'doubles_2', None, None, 2, 3)
                    ]
                }
            ]
