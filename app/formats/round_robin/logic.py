from app.formats.base import TournamentFormat
from app.models import Match, Participant, db

class RoundRobinFormat(TournamentFormat):
    name = "Round Robin (League)"
    description = "Everyone plays everyone. Rankings are based on total cumulative points across all matches. Can optionally feed into a knockout bracket."
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

    @classmethod
    def calculate_final_rankings(cls, category):
        participants = Participant.query.filter_by(category_id=category.id).all()
        standings = []

        for participant in participants:
            matches = Match.query.filter(
                Match.category_id == category.id,
                Match.match_type == 'round_robin',
                Match.status == 'completed',
                db.or_(
                    Match.participant1_id == participant.id,
                    Match.participant2_id == participant.id
                )
            ).all()
            
            wins = sum(1 for m in matches if m.winner_id == participant.id)
            losses = sum(1 for m in matches if m.winner_id and m.winner_id != participant.id)
            
            points = 0
            for m in matches:
                if not m.winner_id:
                    continue
                is_p1 = m.participant1_id == participant.id
                try:
                    s1 = int(m.score1) if m.score1 is not None else 0
                    s2 = int(m.score2) if m.score2 is not None else 0
                    points += s1 if is_p1 else s2
                except (ValueError, TypeError):
                    if m.winner_id == participant.id:
                        points += 3
            
            participant.group_wins = wins
            participant.group_losses = losses
            participant.group_points = points

            standings.append({
                'participant': participant,
                'wins': wins,
                'losses': losses,
                'points': points
            })

        # Sort by points, then wins, then least losses
        standings.sort(key=lambda x: (-x['points'], -x['wins'], x['losses']))

        for i, standing in enumerate(standings):
            standing['participant'].final_rank = i + 1
