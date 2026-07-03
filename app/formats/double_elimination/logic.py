import math
from app.formats.base import TournamentFormat
from app.models import Match, Participant

class DoubleEliminationFormat(TournamentFormat):
    name = "Double Elimination"
    description = "Players are eliminated after losing two matches. Features a winners bracket and a losers bracket."
    icon = "⚔️"
    min_participants = 3

    @classmethod
    def generate(cls, category, participants):
        return cls._generate_double_elimination(participants, use_manual_seeding=True)

    @classmethod
    def advance_match(cls, match, category, winner_id=None):
        from datetime import datetime
        loser_id = match.participant1_id if match.participant1_id != winner_id else match.participant2_id

        winners_matches = Match.query.filter_by(category_id=category.id, bracket_type='winners').all()
        num_rounds_winners = max(m.round for m in winners_matches) if winners_matches else 0

        if match.bracket_type == 'winners':
            next_round = match.round + 1
            next_match_number = (match.match_number + 1) // 2

            next_match = Match.query.filter_by(
                category_id=category.id,
                round=next_round,
                match_number=next_match_number,
                bracket_type='winners'
            ).first()

            if next_match:
                if match.match_number % 2 == 1:
                    next_match.participant1_id = winner_id
                else:
                    next_match.participant2_id = winner_id
            else:
                gf_match = Match.query.filter_by(
                    category_id=category.id,
                    bracket_type='grand_finals',
                    match_number=1
                ).first()
                if gf_match:
                    gf_match.participant1_id = winner_id

            if match.round == 1:
                target_round = 1
                target_match_number = (match.match_number - 1) // 2 + 1
                target_match = Match.query.filter_by(
                    category_id=category.id,
                    round=target_round,
                    match_number=target_match_number,
                    bracket_type='losers'
                ).first()
                if target_match:
                    if match.match_number % 2 == 1:
                        target_match.participant1_id = loser_id
                    else:
                        target_match.participant2_id = loser_id
            else:
                target_round = 2 * match.round - 2
                target_match_number = match.match_number
                target_match = Match.query.filter_by(
                    category_id=category.id,
                    round=target_round,
                    match_number=target_match_number,
                    bracket_type='losers'
                ).first()
                if target_match:
                    target_match.participant1_id = loser_id

        elif match.bracket_type == 'losers':
            max_losers_round = 2 * num_rounds_winners - 2 if num_rounds_winners >= 2 else 0

            if match.round == max_losers_round:
                gf_match = Match.query.filter_by(
                    category_id=category.id,
                    bracket_type='grand_finals',
                    match_number=1
                ).first()
                if gf_match:
                    gf_match.participant2_id = winner_id
            else:
                if match.round % 2 == 1:
                    target_round = match.round + 1
                    target_match_number = match.match_number
                    target_match = Match.query.filter_by(
                        category_id=category.id,
                        round=target_round,
                        match_number=target_match_number,
                        bracket_type='losers'
                    ).first()
                    if target_match:
                        target_match.participant2_id = winner_id
                else:
                    target_round = match.round + 1
                    target_match_number = (match.match_number + 1) // 2
                    target_match = Match.query.filter_by(
                        category_id=category.id,
                        round=target_round,
                        match_number=target_match_number,
                        bracket_type='losers'
                    ).first()
                    if target_match:
                        if match.match_number % 2 == 1:
                            target_match.participant1_id = winner_id
                        else:
                            target_match.participant2_id = winner_id

        elif match.bracket_type == 'grand_finals':
            if match.match_number == 1:
                if winner_id == match.participant1_id:
                    match2 = Match.query.filter_by(
                        category_id=category.id,
                        bracket_type='grand_finals',
                        match_number=2
                    ).first()
                    if match2:
                        match2.status = 'completed'
                        match2.score1 = 'N/A'
                        match2.score2 = 'N/A'
                        match2.completed_at = datetime.utcnow()
                else:
                    match2 = Match.query.filter_by(
                        category_id=category.id,
                        bracket_type='grand_finals',
                        match_number=2
                    ).first()
                    if match2:
                        match2.participant1_id = match.participant1_id
                        match2.participant2_id = match.participant2_id
                        match2.status = 'pending'

    @classmethod
    def calculate_final_rankings(cls, category):
        grand_finals = Match.query.filter_by(
            category_id=category.id,
            bracket_type='grand_finals',
            match_number=2
        ).first()

        if grand_finals and grand_finals.status == 'completed' and grand_finals.winner_id:
            winner = Participant.query.get(grand_finals.winner_id)
            if grand_finals.participant1_id == grand_finals.winner_id:
                runner_up_id = grand_finals.participant2_id
            else:
                runner_up_id = grand_finals.participant1_id
            runner_up = Participant.query.get(runner_up_id)
        else:
            grand_finals = Match.query.filter_by(
                category_id=category.id,
                bracket_type='grand_finals',
                match_number=1
            ).first()

            if not grand_finals or not grand_finals.winner_id:
                return

            winner = Participant.query.get(grand_finals.winner_id)
            if grand_finals.participant1_id == grand_finals.winner_id:
                runner_up_id = grand_finals.participant2_id
            else:
                runner_up_id = grand_finals.participant1_id
            runner_up = Participant.query.get(runner_up_id)

        winners_final = Match.query.filter_by(
            category_id=category.id,
            bracket_type='winners'
        ).order_by(Match.round.desc()).first()

        losers_final = Match.query.filter_by(
            category_id=category.id,
            bracket_type='losers'
        ).order_by(Match.round.desc()).first()

        semi_finalists = []

        for m in [winners_final, losers_final]:
            if m and m.winner_id:
                if m.participant1_id == m.winner_id:
                    loser_id = m.participant2_id
                else:
                    loser_id = m.participant1_id

                if loser_id:
                    loser = Participant.query.get(loser_id)
                    if loser and loser.id != runner_up.id:
                        semi_finalists.append(loser)

        if winner:
            winner.final_rank = 1
        if runner_up:
            runner_up.final_rank = 2
        for sf in semi_finalists:
            sf.final_rank = 3

    @staticmethod
    def _generate_double_elimination(participants, use_manual_seeding=True):
        from app.formats.single_elimination.logic import SingleEliminationFormat
        winners_matches = SingleEliminationFormat._generate_single_elimination(participants, use_manual_seeding)

        for match in winners_matches:
            match['bracket_type'] = 'winners'

        num_participants = len(participants)
        num_rounds_winners = math.ceil(math.log2(num_participants))
        losers_matches = []

        num_first_round_losers = len([m for m in winners_matches if m['round'] == 1])

        for i in range(0, num_first_round_losers, 2):
            match = {
                'round': 1,
                'match_number': (i // 2) + 1,
                'participant1_id': None,
                'participant2_id': None,
                'bracket_type': 'losers',
                'match_type': 'knockout'
            }
            losers_matches.append(match)

        current_losers_round = 2

        for winners_round in range(2, num_rounds_winners + 1):
            num_new_losers = len([m for m in winners_matches if m['round'] == winners_round])
            for i in range(num_new_losers):
                match = {
                    'round': current_losers_round,
                    'match_number': i + 1,
                    'participant1_id': None,
                    'participant2_id': None,
                    'bracket_type': 'losers',
                    'match_type': 'knockout'
                }
                losers_matches.append(match)
            current_losers_round += 1

            if current_losers_round < (2 * num_rounds_winners):
                num_matches = len([m for m in losers_matches if m['round'] == current_losers_round - 1]) // 2
                for i in range(num_matches):
                    match = {
                        'round': current_losers_round,
                        'match_number': i + 1,
                        'participant1_id': None,
                        'participant2_id': None,
                        'bracket_type': 'losers',
                        'match_type': 'knockout'
                    }
                    losers_matches.append(match)
                current_losers_round += 1

        grand_finals = {
            'round': num_rounds_winners + 1,
            'match_number': 1,
            'participant1_id': None,
            'participant2_id': None,
            'bracket_type': 'grand_finals',
            'match_type': 'knockout'
        }
        grand_finals_reset = {
            'round': num_rounds_winners + 1,
            'match_number': 2,
            'participant1_id': None,
            'participant2_id': None,
            'bracket_type': 'grand_finals',
            'match_type': 'knockout'
        }

        return winners_matches + losers_matches + [grand_finals, grand_finals_reset]
