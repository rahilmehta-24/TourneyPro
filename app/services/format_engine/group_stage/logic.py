from functools import cmp_to_key
from datetime import datetime
import random

from app.services.format_engine.base import TournamentFormat
from app.domain.models import db, Match, Participant, Group, TeamMember, PlayerCategoryTier
from app.services.tennis_logic import calculate_team_fixture_status

class GroupStageFormat(TournamentFormat):
    name = "Group Stage + Knockout"
    description = "Round-robin group matches followed by a single elimination knockout bracket for top qualifiers."
    icon = "🎪"
    min_participants = 4

    ROUND_NAMES = {
        2: "Finals",
        4: "Semi-Finals",
        8: "Quarter-Finals",
        16: "Round of 16",
        32: "Round of 32",
    }

    @staticmethod
    def compute_target_bracket_size(num_qualifiers):
        """Return the smallest power-of-2 knockout bracket size >= num_qualifiers (min 2)."""
        if num_qualifiers <= 1:
            return 2
        return 1 << (num_qualifiers - 1).bit_length()

    @classmethod
    def compute_group_structure_options(cls, num_teams, qualifiers_per_group=2, include_degenerate=False):
        """
        Compute viable Group Stage + Knockout structure options for `num_teams` teams/entries.
        Surfaces direct uneven splits (e.g., 11 teams -> 2 groups [6, 5], 4 qualifiers, 0 LL)
        alongside balanced Lucky Loser splits (e.g., 11 teams -> 3 groups [4, 4, 3], 6 + 2 LL -> 8 QF).
        """
        if not num_teams or num_teams < 2:
            return []

        q = max(1, qualifiers_per_group or 2)
        max_groups = min(16, max(2, num_teams // q))
        raw_options = []

        for g in range(2, max_groups + 1):
            base, rem = divmod(num_teams, g)
            sizes = [base + (1 if idx < rem else 0) for idx in range(g)]
            min_size = min(sizes)
            max_size = max(sizes)
            if min_size < 2:
                continue

            is_degenerate = min_size <= q
            direct_qualifiers = g * q
            target_bracket = cls.compute_target_bracket_size(direct_qualifiers)
            extra_slots = max(0, target_bracket - direct_qualifiers)
            non_qualifiers = max(0, num_teams - direct_qualifiers)
            group_ties = sum(s * (s - 1) // 2 for s in sizes)
            knockout_ties = max(0, target_bracket - 1)
            sizes_label = " + ".join(str(s) for s in sizes)
            round_label = cls.ROUND_NAMES.get(target_bracket, f"{target_bracket}-Team Bracket")

            if extra_slots == 0:
                raw_options.append({
                    'option_id': f"g{g}_ll0",
                    'num_groups': g,
                    'group_sizes': sizes,
                    'sizes_label': sizes_label,
                    'is_uneven': len(set(sizes)) > 1,
                    'is_degenerate': is_degenerate,
                    'qualifiers_per_group': q,
                    'direct_qualifiers': direct_qualifiers,
                    'allow_lucky_losers': False,
                    'lucky_losers_needed': 0,
                    'byes_count': 0,
                    'target_bracket': target_bracket,
                    'knockout_label': round_label,
                    'group_ties': group_ties,
                    'knockout_ties': knockout_ties,
                    'total_ties': group_ties + knockout_ties,
                    'max_group_size': max_size,
                    'min_group_size': min_size,
                    'title': f"{g} Groups ({sizes_label}) — Direct Top {q}/Group",
                    'summary': f"{direct_qualifiers} qualifiers → {target_bracket}-Team {round_label} (No Lucky Losers)",
                    'badge': "Even Split • Direct" if len(set(sizes)) == 1 else "Uneven Split • No Lucky Losers",
                    'is_recommended': False,
                })
            else:
                # Option with Lucky Losers when enough non-qualifiers exist across groups
                if non_qualifiers >= extra_slots and not is_degenerate:
                    raw_options.append({
                        'option_id': f"g{g}_ll{extra_slots}",
                        'num_groups': g,
                        'group_sizes': sizes,
                        'sizes_label': sizes_label,
                        'is_uneven': len(set(sizes)) > 1,
                        'is_degenerate': is_degenerate,
                        'qualifiers_per_group': q,
                        'direct_qualifiers': direct_qualifiers,
                        'allow_lucky_losers': True,
                        'lucky_losers_needed': extra_slots,
                        'byes_count': 0,
                        'target_bracket': target_bracket,
                        'knockout_label': round_label,
                        'group_ties': group_ties,
                        'knockout_ties': knockout_ties,
                        'total_ties': group_ties + knockout_ties,
                        'max_group_size': max_size,
                        'min_group_size': min_size,
                        'title': f"{g} Groups ({sizes_label}) + {extra_slots} Lucky Loser{'s' if extra_slots > 1 else ''}",
                        'summary': f"{direct_qualifiers} direct + {extra_slots} Lucky Loser{'s' if extra_slots > 1 else ''} → {target_bracket}-Team {round_label}",
                        'badge': "Recommended • Balanced + Lucky Losers",
                        'is_recommended': False,
                    })

                # Alternative without Lucky Losers (R1 Byes in knockout)
                raw_options.append({
                    'option_id': f"g{g}_bye{extra_slots}",
                    'num_groups': g,
                    'group_sizes': sizes,
                    'sizes_label': sizes_label,
                    'is_uneven': len(set(sizes)) > 1,
                    'is_degenerate': is_degenerate,
                    'qualifiers_per_group': q,
                    'direct_qualifiers': direct_qualifiers,
                    'allow_lucky_losers': False,
                    'lucky_losers_needed': 0,
                    'byes_count': extra_slots,
                    'target_bracket': target_bracket,
                    'knockout_label': round_label,
                    'group_ties': group_ties,
                    'knockout_ties': knockout_ties,
                    'total_ties': group_ties + knockout_ties,
                    'max_group_size': max_size,
                    'min_group_size': min_size,
                    'title': f"{g} Groups ({sizes_label}) + {extra_slots} Knockout Bye{'s' if extra_slots > 1 else ''}",
                    'summary': f"{direct_qualifiers} direct qualifiers + {extra_slots} R1 Bye{'s' if extra_slots > 1 else ''} → {target_bracket}-Team {round_label}",
                    'badge': "With Round-1 Byes",
                    'is_recommended': False,
                })

        non_degenerate = [opt for opt in raw_options if not opt['is_degenerate']]
        options = non_degenerate if (non_degenerate and not include_degenerate) else raw_options

        # Mark recommendations: prefer exact balanced split with size <= 4, or balanced Lucky Loser split with fewest ties
        if options:
            exact_even = [o for o in options if not o['is_uneven'] and o['lucky_losers_needed'] == 0 and o['byes_count'] == 0]
            ll_balanced = [o for o in options if o['allow_lucky_losers'] and o['max_group_size'] <= 5]
            direct_any = [o for o in options if o['lucky_losers_needed'] == 0 and o['byes_count'] == 0]

            if exact_even and exact_even[0]['max_group_size'] <= 4:
                exact_even[0]['is_recommended'] = True
                exact_even[0]['badge'] = "Recommended • Clean Even Split"
            elif ll_balanced:
                # Pick Lucky Loser split with max_group_size <= 4 or smallest tie count
                ll_balanced.sort(key=lambda o: (o['max_group_size'], o['lucky_losers_needed'], o['total_ties']))
                ll_balanced[0]['is_recommended'] = True
                if direct_any:
                    direct_any[0]['badge'] = "Direct Option • No Lucky Losers"
            elif direct_any:
                direct_any[0]['is_recommended'] = True
                direct_any[0]['badge'] = "Recommended • Direct Split"

        return options

    @staticmethod
    def _build_group_target_sizes(num_participants, num_groups, teams_per_group=None):
        """Return balanced group sizes summing to num_participants across num_groups."""
        if num_groups <= 0:
            return []
        base_size, remainder = divmod(num_participants, num_groups)
        target_sizes = []
        remaining = num_participants
        for idx in range(num_groups):
            if teams_per_group:
                taken = min(remaining, teams_per_group)
                target_sizes.append(taken)
                remaining -= taken
            else:
                size = base_size + (1 if idx < remainder else 0)
                target_sizes.append(size)
                remaining -= size
        return target_sizes

    @classmethod
    def _assign_groups_snake(cls, participants, groups, teams_per_group=None):
        """Distribute sorted participants across `groups` using balanced snake seeding."""
        num_groups = len(groups)
        if num_groups <= 0 or not participants:
            return

        participants_sorted = sorted(
            participants,
            key=lambda p: (p.manual_seed or p.seed or 999, p.id or 0)
        )
        num_participants = len(participants_sorted)
        target_sizes = cls._build_group_target_sizes(num_participants, num_groups, teams_per_group=teams_per_group)

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

    @classmethod
    def generate(cls, category, participants):
        """
        Generate round-robin fixtures and 3-rubber child matches (Singles + 2 Doubles)
        for team tournaments.
        """
        num_groups = category.num_groups or 2
        teams_per_group = category.teams_per_group
        matches_per_pair = category.matches_per_team_pair or 1
        is_team_event = bool(category.max_players_per_team and category.max_players_per_team > 1)

        # 1. Reuse existing groups if already configured with timings, or create new ones
        existing_groups = Group.query.filter_by(category_id=category.id).order_by(Group.id).all()
        groups = []
        for i in range(num_groups):
            g_name = f"Group {chr(65 + i)}"
            matched_g = next((g for g in existing_groups if g.name == g_name), None)
            if matched_g:
                groups.append(matched_g)
            else:
                new_g = Group(category_id=category.id, name=g_name)
                db.session.add(new_g)
                db.session.flush()
                groups.append(new_g)

        # Remove extra existing groups if num_groups decreased
        for eg in existing_groups:
            if eg not in groups:
                for p in participants:
                    if p.group_id == eg.id:
                        p.group_id = None
                db.session.delete(eg)
        db.session.flush()

        # Preserve organizer's explicit valid group assignments if everyone is already assigned;
        # otherwise distribute fairly via balanced snake seeding.
        valid_group_ids = {g.id for g in groups}
        all_preassigned = bool(participants) and all(
            p.group_id in valid_group_ids for p in participants
        )
        if not all_preassigned:
            cls._assign_groups_snake(participants, groups, teams_per_group=teams_per_group)

        db.session.commit()

        # Delete empty groups
        active_groups = []
        for group in groups:
            group_participants = [p for p in participants if p.group_id == group.id]
            if len(group_participants) == 0:
                db.session.delete(group)
            else:
                active_groups.append(group)
        db.session.commit()

        matches = []
        match_number = 1

        for group in active_groups:
            group_participants = [p for p in participants if p.group_id == group.id]

            for i in range(len(group_participants)):
                for j in range(i + 1, len(group_participants)):
                    p1 = group_participants[i]
                    p2 = group_participants[j]

                    for match_iteration in range(matches_per_pair):
                        parent_match = {
                            'category_id': category.id,
                            'group_id': group.id,
                            'round': match_iteration + 1,
                            'match_number': match_number,
                            'participant1_id': p1.id,
                            'participant2_id': p2.id,
                            'match_type': 'group_stage',
                            'status': 'pending'
                        }

                        if is_team_event:
                            sub_rubbers = cls._build_team_rubbers(
                                category=category,
                                group_id=group.id,
                                round_num=match_iteration + 1,
                                match_number=match_number,
                                p1=p1,
                                p2=p2,
                                match_type='group_stage'
                            )
                            parent_match['sub_matches'] = sub_rubbers

                        matches.append(parent_match)
                        match_number += 1

        return matches

    @classmethod
    def _build_team_rubbers(cls, category, group_id, round_num, match_number, p1, p2, match_type='group_stage', auto_allot=False):
        """
        Build 3 rubbers for a team fixture:
        - Rubber 1: Singles
        - Rubber 2: Doubles 1
        - Rubber 3: Doubles 2

        Fair Play Guarantee:
        By default (auto_allot=False), player IDs are left unassigned (None), awaiting
        captains' submitted nomination slips to prevent rigged or arbitrary assignments.
        The organizer officially allots the players based on captains' slips in the draw.
        """
        r1_p1_1 = None
        r1_p2_1 = None
        r2_p1_1 = None
        r2_p1_2 = None
        r2_p2_1 = None
        r2_p2_2 = None
        r3_p1_1 = None
        r3_p1_2 = None
        r3_p2_1 = None
        r3_p2_2 = None

        if auto_allot:
            p1_m = sorted(p1.team_members, key=lambda m: m.roster_order or 99) if p1 and hasattr(p1, 'team_members') else []
            p2_m = sorted(p2.team_members, key=lambda m: m.roster_order or 99) if p2 and hasattr(p2, 'team_members') else []

            # Rubber 1: Singles
            r1_p1_1 = p1_m[0].player_id if len(p1_m) >= 1 else (p1.player_id if p1 else None)
            r1_p2_1 = p2_m[0].player_id if len(p2_m) >= 1 else (p2.player_id if p2 else None)

            # Rubber 2: Doubles 1
            r2_p1_1 = p1_m[1].player_id if len(p1_m) >= 2 else None
            r2_p1_2 = p1_m[2].player_id if len(p1_m) >= 3 else None
            r2_p2_1 = p2_m[1].player_id if len(p2_m) >= 2 else None
            r2_p2_2 = p2_m[2].player_id if len(p2_m) >= 3 else None

            # Rubber 3: Doubles 2
            r3_p1_1 = p1_m[3].player_id if len(p1_m) >= 4 else None
            r3_p1_2 = p1_m[4].player_id if len(p1_m) >= 5 else None
            r3_p2_1 = p2_m[3].player_id if len(p2_m) >= 4 else None
            r3_p2_2 = p2_m[4].player_id if len(p2_m) >= 5 else None

        return [
            {
                'category_id': category.id,
                'group_id': group_id,
                'round': round_num,
                'match_number': match_number,
                'participant1_id': p1.id if p1 else None,
                'participant2_id': p2.id if p2 else None,
                'match_type': match_type,
                'rubber_type': 'singles',
                'rubber_number': 1,
                'p1_player1_id': r1_p1_1,
                'p2_player1_id': r1_p2_1,
                'status': 'pending'
            },
            {
                'category_id': category.id,
                'group_id': group_id,
                'round': round_num,
                'match_number': match_number,
                'participant1_id': p1.id if p1 else None,
                'participant2_id': p2.id if p2 else None,
                'match_type': match_type,
                'rubber_type': 'doubles_1',
                'rubber_number': 2,
                'p1_player1_id': r2_p1_1,
                'p1_player2_id': r2_p1_2,
                'p2_player1_id': r2_p2_1,
                'p2_player2_id': r2_p2_2,
                'status': 'pending'
            },
            {
                'category_id': category.id,
                'group_id': group_id,
                'round': round_num,
                'match_number': match_number,
                'participant1_id': p1.id if p1 else None,
                'participant2_id': p2.id if p2 else None,
                'match_type': match_type,
                'rubber_type': 'doubles_2',
                'rubber_number': 3,
                'p1_player1_id': r3_p1_1,
                'p1_player2_id': r3_p1_2,
                'p2_player1_id': r3_p2_1,
                'p2_player2_id': r3_p2_2,
                'status': 'pending'
            }
        ]

    @classmethod
    def advance_match(cls, match, category, winner_id=None):
        """
        Handle match and rubber completion:
        - If sub-rubber completed: recalculate parent fixture score and advance parent if decided.
        - If knockout parent completed: advance to next round in knockout bracket.
        - If group match completed: recalculate group standings.
        """
        if match.parent_match_id:
            parent = Match.query.get(match.parent_match_id)
            if parent:
                rubbers = parent.sub_matches
                status_res = calculate_team_fixture_status(rubbers, total_games=category.total_games or 7)
                parent.score1 = status_res['summary_score1']
                parent.score2 = status_res['summary_score2']

                if status_res['is_decided']:
                    parent.status = 'completed'
                    parent.winner_id = parent.participant1_id if status_res['winner_indicator'] == 1 else parent.participant2_id
                    parent.completed_at = datetime.utcnow()

                    if parent.match_type == 'knockout':
                        from app.services.format_engine.single_elimination.logic import SingleEliminationFormat
                        SingleEliminationFormat.advance_match(parent, category, parent.winner_id)
                        cls._propagate_knockout_team_rubbers(parent, category)
                    elif parent.match_type in ['group_stage', 'round_robin']:
                        cls.calculate_group_standings(parent.group_id)
                else:
                    parent.status = 'in_progress'

                db.session.commit()
                return

        if match.match_type == 'knockout':
            from app.services.format_engine.single_elimination.logic import SingleEliminationFormat
            SingleEliminationFormat.advance_match(match, category, winner_id)
            cls._propagate_knockout_team_rubbers(match, category)
        elif match.match_type in ['group_stage', 'round_robin'] and match.group_id:
            cls.calculate_group_standings(match.group_id)

    @classmethod
    def _propagate_knockout_team_rubbers(cls, parent_match, category):
        """
        When a parent knockout match advances a winner into next_match,
        populate participant and roster IDs on the next_match's rubbers.
        """
        is_team_event = bool(category.max_players_per_team and category.max_players_per_team > 1)
        if not is_team_event or not parent_match.winner_id:
            return

        next_round = parent_match.round + 1
        next_match_number = (parent_match.match_number + 1) // 2

        next_match = Match.query.filter_by(
            category_id=category.id,
            round=next_round,
            match_number=next_match_number,
            bracket_type=parent_match.bracket_type,
            parent_match_id=None
        ).first()

        if not next_match:
            return

        winner_participant = Participant.query.get(parent_match.winner_id)
        is_p1 = (parent_match.match_number % 2 == 1)

        # Check existing rubbers on next_match
        rubbers = next_match.sub_matches
        if not rubbers:
            # Create the 3 rubbers if not yet created
            sub_rubbers_data = cls._build_team_rubbers(
                category=category,
                group_id=None,
                round_num=next_round,
                match_number=next_match_number,
                p1=next_match.participant1,
                p2=next_match.participant2,
                match_type='knockout'
            )
            for s_data in sub_rubbers_data:
                s_data['parent_match_id'] = next_match.id
                sub_match = Match(**s_data, tournament_id=category.tournament_id)
                db.session.add(sub_match)
            db.session.flush()
        else:
            # Update winner participant and roster on existing rubbers
            w_members = sorted(winner_participant.team_members, key=lambda m: m.roster_order or 99) if winner_participant else []
            for r in rubbers:
                if is_p1:
                    r.participant1_id = parent_match.winner_id
                    if r.rubber_number == 1:
                        r.p1_player1_id = w_members[0].player_id if len(w_members) >= 1 else winner_participant.player_id
                    elif r.rubber_number == 2:
                        r.p1_player1_id = w_members[1].player_id if len(w_members) >= 2 else None
                        r.p1_player2_id = w_members[2].player_id if len(w_members) >= 3 else None
                    elif r.rubber_number == 3:
                        r.p1_player1_id = w_members[3].player_id if len(w_members) >= 4 else None
                        r.p1_player2_id = w_members[4].player_id if len(w_members) >= 5 else None
                else:
                    r.participant2_id = parent_match.winner_id
                    if r.rubber_number == 1:
                        r.p2_player1_id = w_members[0].player_id if len(w_members) >= 1 else winner_participant.player_id
                    elif r.rubber_number == 2:
                        r.p2_player1_id = w_members[1].player_id if len(w_members) >= 2 else None
                        r.p2_player2_id = w_members[2].player_id if len(w_members) >= 3 else None
                    elif r.rubber_number == 3:
                        r.p2_player1_id = w_members[3].player_id if len(w_members) >= 4 else None
                        r.p2_player2_id = w_members[4].player_id if len(w_members) >= 5 else None

        db.session.commit()

    @classmethod
    def calculate_final_rankings(cls, category):
        from app.services.format_engine.single_elimination.logic import SingleEliminationFormat
        SingleEliminationFormat.calculate_final_rankings(category)

    @staticmethod
    def calculate_group_standings(group_id):
        """
        Calculate group standings with Head-to-Head as primary tiebreaker.
        Standings criteria:
        1. Fixtures won (group_wins)
        2. Head-to-head match result between tied teams
        3. Games Differential (games won - games conceded)
        4. Total Games Won (group_points)
        5. Fewest losses
        """
        participants = Participant.query.filter_by(group_id=group_id).all()
        participant_map = {p.id: p for p in participants}

        for p in participants:
            p.group_wins = 0
            p.group_losses = 0
            p.group_points = 0
            p._games_conceded = 0
            p._h2h = {}

        # Look at completed parent fixtures in this group
        matches = Match.query.filter(
            Match.group_id == group_id,
            Match.match_type.in_(['group_stage', 'round_robin']),
            Match.parent_match_id.is_(None)
        ).all()

        for match in matches:
            winner_id = match.winner_id
            if not winner_id and match.score1 is not None and match.score2 is not None:
                try:
                    s1 = int(match.score1)
                    s2 = int(match.score2)
                    if s1 > s2:
                        winner_id = match.participant1_id
                    elif s2 > s1:
                        winner_id = match.participant2_id
                except (ValueError, TypeError):
                    pass

            # Also check sub_matches (rubbers) if match.score1 is not populated
            if not winner_id and match.sub_matches:
                p1_total = 0
                p2_total = 0
                all_have_scores = True
                for sm in match.sub_matches:
                    if sm.score1 is not None and sm.score2 is not None:
                        try:
                            # Parse single game score e.g. "6" or format like "6-1"
                            p1_games = int(str(sm.score1).split('-')[0]) if sm.score1 else 0
                            p2_games = int(str(sm.score2).split('-')[0]) if sm.score2 else 0
                            p1_total += p1_games
                            p2_total += p2_games
                        except (ValueError, TypeError):
                            all_have_scores = False
                    else:
                        all_have_scores = False
                if all_have_scores and (p1_total > 0 or p2_total > 0):
                    match.score1 = str(p1_total)
                    match.score2 = str(p2_total)
                    if p1_total > p2_total:
                        winner_id = match.participant1_id
                    elif p2_total > p1_total:
                        winner_id = match.participant2_id

            if (match.status == 'completed' or (match.score1 is not None and match.score2 is not None)) and winner_id:
                p1 = participant_map.get(match.participant1_id)
                p2 = participant_map.get(match.participant2_id)
                if not p1 or not p2:
                    continue

                winner = p1 if winner_id == p1.id else p2
                loser = p2 if winner_id == p1.id else p1

                winner.group_wins += 1
                loser.group_losses += 1

                try:
                    s1 = int(match.score1) if match.score1 is not None else 0
                    s2 = int(match.score2) if match.score2 is not None else 0
                except (ValueError, TypeError):
                    s1 = 3 if winner.id == match.participant1_id else 0
                    s2 = 3 if winner.id == match.participant2_id else 0

                p1.group_points += s1
                p1._games_conceded += s2
                p2.group_points += s2
                p2._games_conceded += s1

                # Record head-to-head outcome
                p1._h2h[p2.id] = 1 if winner.id == p1.id else -1
                p2._h2h[p1.id] = 1 if winner.id == p2.id else -1

        db.session.commit()

        def compare_teams(a, b):
            # 1. Primary: Most fixture matches won
            if a.group_wins != b.group_wins:
                return 1 if a.group_wins > b.group_wins else -1

            # 2. Total Games Won across all group matches (Organizer Directive)
            if a.group_points != b.group_points:
                return 1 if a.group_points > b.group_points else -1

            # 3. Head-to-Head between a and b (decides rank if total games won are equal)
            h2h = getattr(a, '_h2h', {}).get(b.id)
            if h2h is not None and h2h != 0:
                return h2h

            # 4. Games Differential (Games Won - Games Conceded)
            a_diff = a.group_points - getattr(a, '_games_conceded', 0)
            b_diff = b.group_points - getattr(b, '_games_conceded', 0)
            if a_diff != b_diff:
                return 1 if a_diff > b_diff else -1

            # 5. Fewest losses
            if a.group_losses != b.group_losses:
                return 1 if a.group_losses < b.group_losses else -1

            return 0

        standings = sorted(participants, key=cmp_to_key(compare_teams), reverse=True)
        group_obj = Group.query.get(group_id)
        group_label = group_obj.name if group_obj else f"Group {group_id}"
        group_size = len(participants)
        for rank_idx, p in enumerate(standings, start=1):
            p._matches_played = (p.group_wins or 0) + (p.group_losses or 0)
            p._group_size = group_size
            p._group_rank = rank_idx
            p._group_name = group_label
            diff = (p.group_points or 0) - getattr(p, '_games_conceded', 0)
            mp = p._matches_played
            p._win_rate = round((p.group_wins or 0) / mp, 4) if mp > 0 else 0.0
            p._avg_diff = round(diff / mp, 2) if mp > 0 else 0.0
            p._avg_points = round((p.group_points or 0) / mp, 2) if mp > 0 else 0.0
            p._game_diff = diff
        return standings

    @staticmethod
    def _cross_group_sort_key(participant, is_uneven_groups=False, include_group_rank=False):
        """
        Return comparable sort key across groups.
        When group sizes differ (e.g., 4+4+3), normalizes win rate, differential, and points per tie played.
        When include_group_rank=True, prioritizes finishing rank inside the group (e.g., 3rd before 4th).
        """
        pts = participant.group_points or 0
        wins = participant.group_wins or 0
        losses = participant.group_losses or 0
        conceded = getattr(participant, '_games_conceded', 0)
        diff = pts - conceded
        mp = getattr(participant, '_matches_played', wins + losses)

        if is_uneven_groups and mp > 0:
            metrics = (
                round(wins / mp, 6),
                round(diff / mp, 6),
                round(pts / mp, 6),
                pts,
                wins,
                -losses,
            )
        elif is_uneven_groups:
            metrics = (0.0, 0.0, 0.0, pts, wins, -losses)
        else:
            metrics = (pts, diff, wins, -losses)

        if include_group_rank:
            rank_score = -getattr(participant, '_group_rank', 999)
            return (rank_score, *metrics)
        return metrics

    @classmethod
    def get_knockout_qualification_preview(cls, category):
        """
        Inspect finalized/current group standings and compute direct qualifiers,
        knockout target bracket size, Lucky Loser slots, and sorted LL candidates.
        """
        qualifiers_per_group = category.qualifiers_per_group or 2
        groups = Group.query.filter_by(category_id=category.id).order_by(Group.id).all()

        direct_qualifiers = []
        non_qualifiers = []
        group_sizes = []

        for group in groups:
            standings = cls.calculate_group_standings(group.id)
            group_sizes.append(len(standings))
            direct_qualifiers.extend(standings[:qualifiers_per_group])
            non_qualifiers.extend(standings[qualifiers_per_group:])

        is_uneven = len(set(group_sizes)) > 1
        direct_count = len(direct_qualifiers)
        target_bracket = cls.compute_target_bracket_size(direct_count)
        extra_needed = max(0, target_bracket - direct_count)

        candidates_sorted = sorted(
            non_qualifiers,
            key=lambda p: cls._cross_group_sort_key(
                p,
                is_uneven_groups=is_uneven,
                include_group_rank=True,
            ),
            reverse=True,
        )

        if category.allow_lucky_losers and extra_needed > 0 and candidates_sorted:
            slots_to_fill = min(len(candidates_sorted), extra_needed)
            byes_count = max(0, extra_needed - slots_to_fill)
        else:
            slots_to_fill = 0
            byes_count = extra_needed

        recommended_ll_ids = [p.id for p in candidates_sorted[:slots_to_fill]]

        return {
            'groups': groups,
            'group_sizes': group_sizes,
            'is_uneven_groups': is_uneven,
            'qualifiers_per_group': qualifiers_per_group,
            'direct_qualifiers': direct_qualifiers,
            'lucky_loser_candidates': candidates_sorted,
            'recommended_ll_ids': recommended_ll_ids,
            'target_bracket': target_bracket,
            'slots_to_fill': slots_to_fill,
            'byes_count': byes_count,
        }

    @staticmethod
    def _avoid_same_group_r1_rematches(matches, participant_map):
        """
        Swap Round 1 opponents when two teams from the same group meet in Round 1
        (e.g., Group Winner vs Lucky Loser from the same group). Preserves Seed 1
        and Seed 2 anchor slots whenever an alternative swap resolves the clash.
        """
        r1_matches = [
            m for m in matches
            if m.get('round') == 1 and m.get('participant1_id') and m.get('participant2_id')
        ]
        if len(r1_matches) < 2:
            return

        anchor_p1_id = r1_matches[0].get('participant1_id')
        anchor_p2_id = r1_matches[-1].get('participant2_id')

        def group_of(pid):
            p = participant_map.get(pid)
            return p.group_id if p else None

        def seed_of(pid):
            p = participant_map.get(pid)
            return (p.seed if p and p.seed else 999)

        def is_same_group(m):
            g1 = group_of(m.get('participant1_id'))
            g2 = group_of(m.get('participant2_id'))
            return g1 is not None and g1 == g2

        # Try resolving each colliding R1 match using lowest-cost valid swaps
        for m in r1_matches:
            if not is_same_group(m):
                continue

            best_swap = None
            best_cost = None

            # Prefer moving the lower-seeded team in `m`, then either team in partner `other`
            m_slots = ['participant2_id', 'participant1_id']
            if seed_of(m['participant1_id']) > seed_of(m['participant2_id']):
                m_slots = ['participant1_id', 'participant2_id']

            for slot_a in m_slots:
                pid_a = m[slot_a]
                is_anchor_a = (m is r1_matches[0] and slot_a == 'participant1_id' and pid_a == anchor_p1_id) or (
                    m is r1_matches[-1] and slot_a == 'participant2_id' and pid_a == anchor_p2_id
                )

                for other in r1_matches:
                    if other is m:
                        continue
                    other_slots = ['participant2_id', 'participant1_id']
                    if seed_of(other['participant1_id']) > seed_of(other['participant2_id']):
                        other_slots = ['participant1_id', 'participant2_id']

                    for slot_b in other_slots:
                        pid_b = other[slot_b]
                        is_anchor_b = (other is r1_matches[0] and slot_b == 'participant1_id' and pid_b == anchor_p1_id) or (
                            other is r1_matches[-1] and slot_b == 'participant2_id' and pid_b == anchor_p2_id
                        )

                        # Test swap
                        m[slot_a], other[slot_b] = pid_b, pid_a
                        valid = not is_same_group(m) and not is_same_group(other)
                        m[slot_a], other[slot_b] = pid_a, pid_b

                        if not valid:
                            continue

                        anchor_penalty = (1000 if is_anchor_a else 0) + (1000 if is_anchor_b else 0)
                        seed_delta = abs(seed_of(pid_a) - seed_of(pid_b))
                        # Strongly prefer swapping two lower-half/slot-2 positions cleanly
                        slot_penalty = 0 if (slot_a == 'participant2_id' and slot_b == 'participant2_id') else 10
                        cost = anchor_penalty + slot_penalty + seed_delta
                        if best_cost is None or cost < best_cost:
                            best_cost = cost
                            best_swap = (other, slot_a, slot_b)

            if best_swap is not None:
                other, slot_a, slot_b = best_swap
                m[slot_a], other[slot_b] = other[slot_b], m[slot_a]

    @classmethod
    def generate_knockout_from_groups(cls, category, lucky_loser_ids=None):
        """
        Transition from Group Stage to Knockout:
        1. Qualify top `qualifiers_per_group` teams from each group.
        2. Fill remaining spots up to next power-of-2 bracket when Lucky Losers enabled:
           - Uses organizer-selected `lucky_loser_ids` (from manual Chit Draw) if provided,
           - Otherwise selects top normalized Lucky Loser candidates across uneven/even groups.
        3. Compile ALL qualifiers into a unified leaderboard (per-tie normalized if groups are uneven).
        4. Seed bracket strictly and swap Round 1 pairings if needed to avoid same-group rematches.
        """
        from app.services.format_engine.single_elimination.logic import SingleEliminationFormat

        is_team_event = bool(category.max_players_per_team and category.max_players_per_team > 1)
        preview = cls.get_knockout_qualification_preview(category)

        qualified = list(preview['direct_qualifiers'])
        slots_to_fill = preview['slots_to_fill']
        is_uneven = preview['is_uneven_groups']

        if category.allow_lucky_losers and slots_to_fill > 0:
            candidates_by_id = {p.id: p for p in preview['lucky_loser_candidates']}
            selected_lls = []
            if lucky_loser_ids is not None:
                seen_ids = set()
                for ll_id in lucky_loser_ids:
                    if ll_id in candidates_by_id and ll_id not in seen_ids:
                        selected_lls.append(candidates_by_id[ll_id])
                        seen_ids.add(ll_id)
                    if len(selected_lls) == slots_to_fill:
                        break
            if not selected_lls:
                selected_lls = preview['lucky_loser_candidates'][:slots_to_fill]

            for ll in selected_lls:
                ll._is_lucky_loser = True
            qualified.extend(selected_lls)

        # Unified Leaderboard Seeding across ALL qualifiers
        unified_ranked = sorted(
            qualified,
            key=lambda p: cls._cross_group_sort_key(
                p,
                is_uneven_groups=is_uneven,
                include_group_rank=False,
            ),
            reverse=True,
        )

        participant_map = {}
        for i, participant in enumerate(unified_ranked):
            participant.seed = i + 1
            participant_map[participant.id] = participant

        db.session.commit()

        # Bracket placement with Seed 1 top, Seed 2 bottom, Seed 3 lower, Seed 4 upper
        matches = SingleEliminationFormat._generate_single_elimination(unified_ranked, use_manual_seeding=False)

        # Avoid immediate Round-1 group-stage rematches when multiple groups exist
        if len(preview['groups']) >= 2:
            cls._avoid_same_group_r1_rematches(matches, participant_map)

        for match in matches:
            match['category_id'] = category.id
            if is_team_event and match.get('round') == 1:
                # Build rubbers for Round 1 fixtures AFTER rematch-avoidance finalizes pairings
                p1_obj = Participant.query.get(match['participant1_id']) if match.get('participant1_id') else None
                p2_obj = Participant.query.get(match['participant2_id']) if match.get('participant2_id') else None
                match['sub_matches'] = cls._build_team_rubbers(
                    category=category,
                    group_id=None,
                    round_num=1,
                    match_number=match['match_number'],
                    p1=p1_obj,
                    p2=p2_obj,
                    match_type='knockout'
                )

        return matches

    @classmethod
    def auto_create_teams(cls, category_id):
        """
        Mode B: Automatic Team Creation.
        Draws 1 player per Skill Tier (A..E/H based on K) into each balanced squad
        and assigns teams to groups using balanced snake seeding.
        """
        from app.domain.models import Category

        category = Category.query.get_or_404(category_id)
        tiers = PlayerCategoryTier.query.filter_by(category_id=category_id).all()

        if not tiers:
            raise ValueError("No player tiers found. Please create player tiers first.")

        k = category.max_players_per_team or 5
        active_tiers = list('ABCDEFGH'[:k])
        tier_map = {letter: [] for letter in active_tiers}
        for t in tiers:
            if t.tier in tier_map:
                tier_map[t.tier].append(t)

        num_teams = len(tiers) // k
        if num_teams < 2:
            raise ValueError(f"Need at least {k * 2} players across tiers to form at least 2 teams.")

        for tier_letter in active_tiers:
            if len(tier_map[tier_letter]) < num_teams:
                raise ValueError(
                    f"Tier {tier_letter} has only {len(tier_map[tier_letter])} players, "
                    f"but {num_teams} are needed (1 per team)."
                )

        for tier_letter in tier_map:
            random.shuffle(tier_map[tier_letter])

        # Delete existing teams and team members in setup mode
        existing_teams = Participant.query.filter_by(category_id=category_id).all()
        for p in existing_teams:
            db.session.delete(p)
        db.session.flush()

        cat_groups = Group.query.filter_by(category_id=category_id).order_by(Group.id).all()

        created_teams = []
        for i in range(num_teams):
            captain_tier = tier_map['A'][i]
            team_name = f"Team {i + 1}"
            team_p = Participant(
                tournament_id=category.tournament_id,
                category_id=category.id,
                name=team_name,
                player_id=captain_tier.player_id,
                group_id=None,
            )
            db.session.add(team_p)
            db.session.flush()

            for order, tier_letter in enumerate(active_tiers, start=1):
                t_item = tier_map[tier_letter][i]
                role = 'captain' if order == 1 else ('vice_captain' if order == 2 else 'member')
                tier_role = role if order <= 2 else 'player'
                db.session.add(TeamMember(
                    participant_id=team_p.id,
                    player_id=t_item.player_id,
                    role=role,
                    tier=tier_letter,
                    roster_order=order,
                ))
                t_item.is_drafted = True
                t_item.role = tier_role

            created_teams.append(team_p)

        # Distribute newly created teams fairly using the unified snake-seeding order
        if cat_groups:
            cls._assign_groups_snake(created_teams, cat_groups, teams_per_group=category.teams_per_group)

        db.session.commit()
        return created_teams
