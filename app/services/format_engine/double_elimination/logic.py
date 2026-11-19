import math
from datetime import datetime
from app.services.format_engine.base import TournamentFormat
from app.domain.models import Match, Participant, db

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

                    # Check if the other slot was a bye -> auto-advance loser
                    if target_match.participant1_id and target_match.score2 == 'Bye':
                        target_match.status = 'completed'
                        target_match.winner_id = target_match.participant1_id
                        cls.advance_match(target_match, category, target_match.participant1_id)
                    elif target_match.participant2_id and target_match.score1 == 'Bye':
                        target_match.status = 'completed'
                        target_match.winner_id = target_match.participant2_id
                        cls.advance_match(target_match, category, target_match.participant2_id)
            else:
                target_round = 2 * match.round - 2
                w_matches_in_r = [m for m in winners_matches if m.round == match.round]
                n = len(w_matches_in_r)

                # Anti-rematch mirrored mapping on even Winners rounds (Section 2.2 of DOUBLE_ELIMINATION.md)
                if match.round % 2 == 0 and n > 1:
                    target_match_number = n + 1 - match.match_number
                else:
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

        if grand_finals and grand_finals.status == 'completed' and grand_finals.winner_id and grand_finals.score1 != 'N/A':
            winner = Participant.query.get(grand_finals.winner_id)
            runner_up_id = grand_finals.participant2_id if grand_finals.participant1_id == grand_finals.winner_id else grand_finals.participant1_id
            runner_up = Participant.query.get(runner_up_id) if runner_up_id else None
        else:
            grand_finals = Match.query.filter_by(
                category_id=category.id,
                bracket_type='grand_finals',
                match_number=1
            ).first()

            if not grand_finals or not grand_finals.winner_id:
                return

            winner = Participant.query.get(grand_finals.winner_id)
            runner_up_id = grand_finals.participant2_id if grand_finals.participant1_id == grand_finals.winner_id else grand_finals.participant1_id
            runner_up = Participant.query.get(runner_up_id) if runner_up_id else None

        if winner:
            winner.final_rank = 1
        if runner_up:
            runner_up.final_rank = 2

        ranked_ids = {p.id for p in [winner, runner_up] if p}

        # Full elimination-order final rankings by iterating backward through Losers rounds
        losers_matches = Match.query.filter_by(
            category_id=category.id,
            bracket_type='losers'
        ).all()

        if not losers_matches:
            db.session.commit()
            return

        max_losers_round = max(m.round for m in losers_matches)
        current_rank = 3

        for r in range(max_losers_round, 0, -1):
            r_matches = [m for m in losers_matches if m.round == r and m.status == 'completed' and m.winner_id]
            r_losers = []
            for m in r_matches:
                if m.score1 == 'Void' or m.score2 == 'Void':
                    continue
                lid = m.participant2_id if m.participant1_id == m.winner_id else m.participant1_id
                if lid and lid not in ranked_ids:
                    loser = Participant.query.get(lid)
                    if loser:
                        r_losers.append(loser)
                        ranked_ids.add(lid)

            if r_losers:
                for loser_p in r_losers:
                    loser_p.final_rank = current_rank
                current_rank += len(r_losers)

        db.session.commit()

    @staticmethod
    def _generate_double_elimination(participants, use_manual_seeding=True):
        from app.services.format_engine.single_elimination.logic import SingleEliminationFormat
        winners_matches = SingleEliminationFormat._generate_single_elimination(participants, use_manual_seeding)

        for match in winners_matches:
            match['bracket_type'] = 'winners'

        num_participants = len(participants)
        num_rounds_winners = math.ceil(math.log2(num_participants))
        losers_matches = []

        # Identify which Winners Round 1 matches had byes (i.e. no loser will be produced)
        w1_byes = {
            m['match_number']
            for m in winners_matches
            if m['round'] == 1 and (m['participant1_id'] is None or m['participant2_id'] is None)
        }

        num_first_round_losers = len([m for m in winners_matches if m['round'] == 1])

        for i in range(0, num_first_round_losers, 2):
            match_num = (i // 2) + 1
            feed1 = 2 * match_num - 1
            feed2 = 2 * match_num
            has_feed1_bye = feed1 in w1_byes
            has_feed2_bye = feed2 in w1_byes

            status = 'pending'
            score1 = None
            score2 = None
            if has_feed1_bye and has_feed2_bye:
                status = 'completed'
                score1 = 'Void'
                score2 = 'Void'
            elif has_feed1_bye:
                score1 = 'Bye'
            elif has_feed2_bye:
                score2 = 'Bye'

            match = {
                'round': 1,
                'match_number': match_num,
                'participant1_id': None,
                'participant2_id': None,
                'bracket_type': 'losers',
                'match_type': 'knockout',
                'status': status,
                'score1': score1,
                'score2': score2,
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
