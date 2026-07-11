from app.formats.base import TournamentFormat
from app.models import db, Match, Participant, Group

class GroupStageFormat(TournamentFormat):
    name = "Group Stage + Knockout"
    description = "Round-robin group matches followed by a single elimination knockout bracket for top qualifiers."
    icon = "🎪"
    min_participants = 4

    @classmethod
    def generate(cls, category, participants):
        num_groups = category.num_groups
        teams_per_group = category.teams_per_group
        matches_per_pair = category.matches_per_team_pair or 1

        groups = []
        for i in range(num_groups):
            group = Group(
                category_id=category.id,
                name=f"Group {chr(65 + i)}"
            )
            db.session.add(group)
            db.session.flush()
            groups.append(group)

        participants_sorted = sorted(participants, key=lambda p: p.manual_seed or p.seed or 999)

        num_participants = len(participants_sorted)
        if num_groups > 0:
            base_size = num_participants // num_groups
            remainder = num_participants % num_groups
            
            # Distribute evenly but cap at teams_per_group
            target_sizes = []
            for idx in range(num_groups):
                size = base_size + (1 if idx < remainder else 0)
                if teams_per_group and size > teams_per_group:
                    size = teams_per_group
                target_sizes.append(size)
            
            # If after capping, we have extra space and remaining participants, 
            # distribute the excess to groups that haven't reached teams_per_group yet
            total_capacity = sum(target_sizes)
            if total_capacity < num_participants and teams_per_group:
                # We have more participants than the current target sizes allow.
                # Fill up remaining groups until they hit teams_per_group
                for idx in range(num_groups):
                    while target_sizes[idx] < teams_per_group and sum(target_sizes) < num_participants:
                        target_sizes[idx] += 1
            
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
                    # Tournament capacity reached, remaining participants are left unassigned
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

        matches = []
        match_number = 1

        for group in groups:
            group_participants = [p for p in participants if p.group_id == group.id]

            for i in range(len(group_participants)):
                for j in range(i + 1, len(group_participants)):
                    p1 = group_participants[i]
                    p2 = group_participants[j]

                    for match_iteration in range(matches_per_pair):
                        match = {
                            'category_id': category.id,
                            'group_id': group.id,
                            'round': match_iteration + 1,
                            'match_number': match_number,
                            'participant1_id': p1.id,
                            'participant2_id': p2.id,
                            'match_type': 'group_stage'
                        }
                        matches.append(match)
                        match_number += 1

        return matches

    @classmethod
    def advance_match(cls, match, category, winner_id=None):
        if match.match_type == 'knockout':
            from app.formats.single_elimination.logic import SingleEliminationFormat
            SingleEliminationFormat.advance_match(match, category, winner_id)

    @classmethod
    def calculate_final_rankings(cls, category):
        from app.formats.single_elimination.logic import SingleEliminationFormat
        SingleEliminationFormat.calculate_final_rankings(category)

    @staticmethod
    def calculate_group_standings(group_id):
        participants = Participant.query.filter_by(group_id=group_id).all()

        for p in participants:
            p.group_wins = 0
            p.group_losses = 0
            p.group_points = 0

        matches = Match.query.filter(Match.group_id==group_id, Match.match_type.in_(['group_stage', 'round_robin'])).all()

        for match in matches:
            if match.status == 'completed' and match.winner_id:
                winner = next((p for p in participants if p.id == match.winner_id), None)
                if match.participant1_id == match.winner_id:
                    loser_id = match.participant2_id
                else:
                    loser_id = match.participant1_id
                loser = next((p for p in participants if p.id == loser_id), None)

                if winner:
                    winner.group_wins += 1
                    try:
                        s1 = int(match.score1) if match.score1 is not None else 0
                        s2 = int(match.score2) if match.score2 is not None else 0
                        winner.group_points += s1 if match.participant1_id == winner.id else s2
                    except (ValueError, TypeError):
                        winner.group_points += 3

                if loser:
                    loser.group_losses += 1
                    try:
                        s1 = int(match.score1) if match.score1 is not None else 0
                        s2 = int(match.score2) if match.score2 is not None else 0
                        loser.group_points += s2 if match.participant1_id == winner.id else s1
                    except (ValueError, TypeError):
                        pass

        db.session.commit()

        standings = sorted(
            participants,
            key=lambda p: (-p.group_points, -p.group_wins, p.group_losses)
        )

        return standings

    @classmethod
    def generate_knockout_from_groups(cls, category):
        from app.formats.single_elimination.logic import SingleEliminationFormat

        qualifiers_per_group = category.qualifiers_per_group or 2
        groups = Group.query.filter_by(category_id=category.id).all()

        qualified = []
        non_qualified = []

        for group in groups:
            standings = cls.calculate_group_standings(group.id)
            group_qualifiers = standings[:qualifiers_per_group]
            qualified.extend(group_qualifiers)
            non_qualified.extend(standings[qualifiers_per_group:])

        if category.allow_lucky_losers and len(qualified) < 8:
            non_qualified_sorted = sorted(
                non_qualified,
                key=lambda p: (-p.group_points, -p.group_wins, p.group_losses)
            )
            slots_to_fill = 8 - len(qualified)
            lucky_losers = non_qualified_sorted[:slots_to_fill]
            qualified.extend(lucky_losers)

        for i, participant in enumerate(qualified):
            participant.seed = i + 1

        db.session.commit()

        matches = SingleEliminationFormat._generate_single_elimination(qualified, use_manual_seeding=False)

        for match in matches:
            match['category_id'] = category.id

        return matches
