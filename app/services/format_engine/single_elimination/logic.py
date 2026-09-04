import math
from app.formats.base import TournamentFormat
from app.models import Match, Participant

class SingleEliminationFormat(TournamentFormat):
    name = "Knockout (Single Elimination)"
    description = "Classic bracket tournament where losing a match eliminates the participant. Supports both Singles and Doubles formats."
    icon = "🏆"
    min_participants = 2

    @classmethod
    def generate(cls, category, participants):
        return cls._generate_single_elimination(participants, use_manual_seeding=True)
        
    @classmethod
    def advance_match(cls, match, category, winner_id=None):
        next_round = match.round + 1
        next_match_number = (match.match_number + 1) // 2

        next_match = Match.query.filter_by(
            category_id=category.id,
            round=next_round,
            match_number=next_match_number,
            bracket_type=match.bracket_type
        ).first()

        if next_match:
            if match.match_number % 2 == 1:
                next_match.participant1_id = winner_id
            else:
                next_match.participant2_id = winner_id

    @classmethod
    def calculate_final_rankings(cls, category):
        final_match = Match.query.filter_by(
            category_id=category.id,
            match_type='knockout'
        ).order_by(Match.round.desc()).first()

        if not final_match or not final_match.winner_id:
            return

        winner = Participant.query.get(final_match.winner_id)

        if final_match.participant1_id == final_match.winner_id:
            runner_up_id = final_match.participant2_id
        else:
            runner_up_id = final_match.participant1_id
        runner_up = Participant.query.get(runner_up_id)

        semi_final_round = final_match.round - 1
        semi_final_matches = Match.query.filter_by(
            category_id=category.id,
            round=semi_final_round,
            match_type='knockout'
        ).all()

        semi_finalists = []
        for match in semi_final_matches:
            if match.winner_id:
                if match.participant1_id == match.winner_id:
                    loser_id = match.participant2_id
                else:
                    loser_id = match.participant1_id

                if loser_id:
                    loser = Participant.query.get(loser_id)
                    semi_finalists.append(loser)

        if winner:
            winner.final_rank = 1
        if runner_up:
            runner_up.final_rank = 2
        for i, sf in enumerate(semi_finalists):
            sf.final_rank = 3

    @staticmethod
    def _generate_single_elimination(participants, use_manual_seeding=True):
        num_participants = len(participants)

        if num_participants < 2:
            return []

        num_rounds = math.ceil(math.log2(num_participants))
        bracket_size = 2 ** num_rounds
        num_byes = bracket_size - num_participants

        if use_manual_seeding:
            participants_sorted = sorted(
                participants,
                key=lambda p: p.manual_seed if p.manual_seed else (p.seed if p.seed else 999)
            )
        else:
            participants_sorted = sorted(
                participants,
                key=lambda p: p.seed if p.seed else 999
            )

        for i, p in enumerate(participants_sorted):
            if not p.seed:
                p.seed = i + 1

        seeding_order = SingleEliminationFormat._generate_seeding_order(bracket_size)

        participant_slots = [None] * bracket_size

        for participant in participants_sorted:
            seed = participant.manual_seed if participant.manual_seed else participant.seed
            try:
                slot_index = seeding_order.index(seed)
                participant_slots[slot_index] = participant
            except ValueError:
                continue

        matches = []
        match_number = 1

        for i in range(0, bracket_size, 2):
            p1 = participant_slots[i]
            p2 = participant_slots[i + 1]

            if p1 or p2:
                match = {
                    'round': 1,
                    'match_number': match_number,
                    'participant1_id': p1.id if p1 else None,
                    'participant2_id': p2.id if p2 else None,
                    'bracket_type': 'main',
                    'match_type': 'knockout'
                }
                matches.append(match)
                match_number += 1

        current_round_matches = len(matches)

        for round_num in range(2, num_rounds + 1):
            next_round_matches = current_round_matches // 2

            for match_num in range(next_round_matches):
                match = {
                    'round': round_num,
                    'match_number': match_num + 1,
                    'participant1_id': None,
                    'participant2_id': None,
                    'bracket_type': 'main',
                    'match_type': 'knockout'
                }
                matches.append(match)

            current_round_matches = next_round_matches

        for match in matches:
            if match['round'] == 1:
                has_bye = (match['participant1_id'] is None) != (match['participant2_id'] is None)

                if has_bye:
                    bye_winner_id = match['participant1_id'] if match['participant1_id'] else match['participant2_id']
                    next_round = 2
                    next_match_number = (match['match_number'] + 1) // 2

                    for next_match in matches:
                        if next_match['round'] == next_round and next_match['match_number'] == next_match_number:
                            if match['match_number'] % 2 == 1:
                                next_match['participant1_id'] = bye_winner_id
                            else:
                                next_match['participant2_id'] = bye_winner_id

                            match['winner_id'] = bye_winner_id
                            match['status'] = 'completed'
                            match['score1'] = 'Bye' if match['participant2_id'] is None else ''
                            match['score2'] = 'Bye' if match['participant1_id'] is None else ''
                            break

        return matches

    @staticmethod
    def _generate_seeding_order(bracket_size):
        if bracket_size == 2:
            return [1, 2]

        previous_round = SingleEliminationFormat._generate_seeding_order(bracket_size // 2)
        seeding = []

        half_idx = len(previous_round) // 2
        top_half = previous_round[:half_idx]
        bottom_half = previous_round[half_idx:]

        for seed in top_half:
            seeding.append(seed)
            seeding.append(bracket_size + 1 - seed)

        for seed in bottom_half:
            seeding.append(bracket_size + 1 - seed)
            seeding.append(seed)

        return seeding
