import re

with open('app/routes/category.py', 'r') as f:
    content = f.read()

replacement = """    participants = Participant.query.filter_by(category_id=category_id).order_by(Participant.seed).all()
    matches = Match.query.filter_by(category_id=category_id).order_by(Match.round, Match.match_number).all()

    # If tournament is still in setup, generate preview bracket on the fly
    if category.status == 'setup' and not matches and participants:
        class DummyMatch:
            def __init__(self, **kwargs):
                self.match_type = 'knockout'
                self.bracket_type = 'winners'
                self.round = 1
                self.match_number = 1
                for k, v in kwargs.items():
                    setattr(self, k, v)
                self.status = 'pending'
                self.score1 = None
                self.score2 = None
                self.winner_id = None
                self.id = 0
                
                p1_id = getattr(self, 'participant1_id', None)
                p2_id = getattr(self, 'participant2_id', None)
                self.participant1 = next((p for p in participants if p.id == p1_id), None) if p1_id else None
                self.participant2 = next((p for p in participants if p.id == p2_id), None) if p2_id else None

        dummy_data = []
        if category.format == 'single_elimination':
            dummy_data = generate_single_elimination(participants)
        elif category.format == 'double_elimination':
            dummy_data = calculate_double_elimination_rankings(category) # wait double_elim function is diff
        elif category.format == 'round_robin':
            from app.algorithms.round_robin import generate_round_robin
            dummy_data = generate_round_robin(participants)
            
        if not dummy_data and category.format == 'double_elimination':
            from app.algorithms.double_elimination import generate_double_elimination
            dummy_data = generate_double_elimination(participants)

        matches = [DummyMatch(**d) for d in dummy_data]"""

content = re.sub(r'    participants = Participant.query.filter_by\(category_id=category_id\).order_by\(Participant.seed\).all\(\)\n    matches = Match.query.filter_by\(category_id=category_id\).order_by\(Match.round, Match.match_number\).all\(\)', replacement, content)

with open('app/routes/category.py', 'w') as f:
    f.write(content)
