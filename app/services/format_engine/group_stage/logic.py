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
                db.session.delete(eg)
        db.session.flush()

        participants_sorted = sorted(participants, key=lambda p: p.manual_seed or p.seed or 999)
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
            if match.status == 'completed' and match.winner_id:
                p1 = participant_map.get(match.participant1_id)
                p2 = participant_map.get(match.participant2_id)
                if not p1 or not p2:
                    continue

                winner = p1 if match.winner_id == p1.id else p2
                loser = p2 if match.winner_id == p1.id else p1

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
            # 1. Primary: Most wins
            if a.group_wins != b.group_wins:
                return 1 if a.group_wins > b.group_wins else -1

            # 2. Head-to-Head between a and b
            h2h = getattr(a, '_h2h', {}).get(b.id)
            if h2h is not None and h2h != 0:
                return h2h

            # 3. Games Differential
            a_diff = a.group_points - getattr(a, '_games_conceded', 0)
            b_diff = b.group_points - getattr(b, '_games_conceded', 0)
            if a_diff != b_diff:
                return 1 if a_diff > b_diff else -1

            # 4. Total Games Won (Max score)
            if a.group_points != b.group_points:
                return 1 if a.group_points > b.group_points else -1

            # 5. Fewest losses
            if a.group_losses != b.group_losses:
                return 1 if a.group_losses < b.group_losses else -1

            return 0

        standings = sorted(participants, key=cmp_to_key(compare_teams), reverse=True)
        return standings

    @classmethod
    def generate_knockout_from_groups(cls, category):
        """
        Transition from Group Stage to Knockout:
        1. Qualify top teams from each group.
        2. Draw Lucky Losers if enabled (e.g. 2 from 3rd-place teams to fill 8-bracket).
        3. Compile ALL qualifiers into a single unified leaderboard ranked by Max Score (total games).
        4. Seed bracket strictly:
           - Seed 1: Line 1 (Upper Half)
           - Seed 2: Last Line (Line 8) (Lower Half)
           - Seed 3: Lower Half (Line 5)
           - Seed 4: Upper Half (Line 4)
        """
        from app.services.format_engine.single_elimination.logic import SingleEliminationFormat

        qualifiers_per_group = category.qualifiers_per_group or 2
        groups = Group.query.filter_by(category_id=category.id).all()
        is_team_event = bool(category.max_players_per_team and category.max_players_per_team > 1)

        qualified = []
        non_qualified = []

        for group in groups:
            standings = cls.calculate_group_standings(group.id)
            group_qualifiers = standings[:qualifiers_per_group]
            qualified.extend(group_qualifiers)
            non_qualified.extend(standings[qualifiers_per_group:])

        # Lucky Loser Draw (fills up to 8 teams if 3 groups provide 6 qualifiers)
        if category.allow_lucky_losers and len(qualified) < 8:
            non_qualified_sorted = sorted(
                non_qualified,
                key=lambda p: (
                    p.group_points,
                    p.group_points - getattr(p, '_games_conceded', 0),
                    p.group_wins,
                    -p.group_losses
                ),
                reverse=True
            )
            slots_to_fill = 8 - len(qualified)
            lucky_losers = non_qualified_sorted[:slots_to_fill]
            qualified.extend(lucky_losers)

        # Unified Leaderboard Seeding: Ranked across ALL teams by Max Group Score
        unified_ranked = sorted(
            qualified,
            key=lambda p: (
                p.group_points,
                p.group_points - getattr(p, '_games_conceded', 0),
                p.group_wins,
                -p.group_losses
            ),
            reverse=True
        )

        for i, participant in enumerate(unified_ranked):
            participant.seed = i + 1

        db.session.commit()

        # Bracket placement with Seed 1 top, Seed 2 bottom, Seed 3 lower, Seed 4 upper
        matches = SingleEliminationFormat._generate_single_elimination(unified_ranked, use_manual_seeding=False)

        for match in matches:
            match['category_id'] = category.id
            if is_team_event and match.get('round') == 1:
                # Build rubbers for Round 1 fixtures
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
        Mode B: 🎲 Automatic Team Creation.
        Draws 1 player from Tier A (Captain), 1 from Tier B (VC), 1 from Tier C, 
        1 from Tier D, and 1 from Tier E into each team.
        """
        from app.domain.models import Category

        category = Category.query.get_or_404(category_id)
        tiers = PlayerCategoryTier.query.filter_by(category_id=category_id).all()

        if not tiers:
            raise ValueError("No player tiers found. Please create player tiers first.")

        tier_map = {'A': [], 'B': [], 'C': [], 'D': [], 'E': []}
        for t in tiers:
            if t.tier in tier_map:
                tier_map[t.tier].append(t)

        k = category.max_players_per_team or 5
        num_teams = len(tiers) // k
        if num_teams < 2:
            raise ValueError(f"Need at least {k * 2} players across tiers to form at least 2 teams.")

        # Check that we have enough in each tier
        for tier_letter in ['A', 'B', 'C', 'D', 'E'][:k]:
            if len(tier_map[tier_letter]) < num_teams:
                raise ValueError(f"Tier {tier_letter} has only {len(tier_map[tier_letter])} players, but {num_teams} are needed (1 per team).")

        # Shuffle each tier randomly
        for tier_letter in tier_map:
            random.shuffle(tier_map[tier_letter])

        # Delete existing teams and team members in setup mode
        existing_teams = Participant.query.filter_by(category_id=category_id).all()
        for p in existing_teams:
            db.session.delete(p)
        db.session.flush()

        created_teams = []
        for i in range(num_teams):
            captain_tier = tier_map['A'][i]
            vc_tier = tier_map['B'][i]
            c_tier = tier_map['C'][i] if len(tier_map['C']) > i else None
            d_tier = tier_map['D'][i] if len(tier_map['D']) > i else None
            e_tier = tier_map['E'][i] if len(tier_map['E']) > i else None

            team_name = f"Team {i + 1}"
            team_p = Participant(
                tournament_id=category.tournament_id,
                category_id=category.id,
                name=team_name,
                player_id=captain_tier.player_id
            )
            db.session.add(team_p)
            db.session.flush()

            # Add Captain
            db.session.add(TeamMember(
                participant_id=team_p.id,
                player_id=captain_tier.player_id,
                role='captain',
                tier='A',
                roster_order=1
            ))
            captain_tier.is_drafted = True
            captain_tier.role = 'captain'

            # Add VC
            db.session.add(TeamMember(
                participant_id=team_p.id,
                player_id=vc_tier.player_id,
                role='vice_captain',
                tier='B',
                roster_order=2
            ))
            vc_tier.is_drafted = True
            vc_tier.role = 'vice_captain'

            # Add C, D, E
            for order, (tier_letter, t_item) in enumerate([('C', c_tier), ('D', d_tier), ('E', e_tier)], start=3):
                if t_item:
                    db.session.add(TeamMember(
                        participant_id=team_p.id,
                        player_id=t_item.player_id,
                        role='member',
                        tier=tier_letter,
                        roster_order=order
                    ))
                    t_item.is_drafted = True
                    t_item.role = 'player'

            created_teams.append(team_p)

        db.session.commit()
        return created_teams
