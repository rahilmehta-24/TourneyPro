import os
import tempfile
import unittest
from app import create_app
from app.domain.models import db, Tournament, Category, Participant, Match
from app.services.format_engine.single_elimination.logic import SingleEliminationFormat
from app.services.format_engine.double_elimination.logic import DoubleEliminationFormat
from app.services.format_engine.round_robin.logic import RoundRobinFormat
from app.services.format_engine.doubles_round_robin.logic import DoublesRoundRobinFormat

class FormatRulesAlignmentTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix='.db')
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = 'test-secret'
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{cls.db_path}'
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            WTF_CSRF_ENABLED = False
            UPLOAD_FOLDER = tempfile.mkdtemp()

        cls.app = create_app(TestConfig)
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.app_context.pop()
        if os.path.exists(cls.db_path):
            os.unlink(cls.db_path)

    def setUp(self):
        db.session.begin_nested()

    def tearDown(self):
        db.session.rollback()

    def test_round_robin_ranking_prioritizes_wins_over_points(self):
        """
        Test that a player with MORE MATCH WINS outranks a player with MORE POINTS.
        Player A: 2 wins, 23 points
        Player B: 1 win, 60 points
        Player A must be ranked #1, Player B ranked #2.
        """
        t = Tournament(name="RR Test", url_slug="rr-test-1", status="in_progress")
        db.session.add(t)
        db.session.flush()

        cat = Category(tournament_id=t.id, name="RR League", format="round_robin", status="in_progress")
        db.session.add(cat)
        db.session.flush()

        pA = Participant(tournament_id=t.id, category_id=cat.id, name="Player A")
        pB = Participant(tournament_id=t.id, category_id=cat.id, name="Player B")
        pC = Participant(tournament_id=t.id, category_id=cat.id, name="Player C")
        db.session.add_all([pA, pB, pC])
        db.session.commit()

        m1 = Match(
            tournament_id=t.id, category_id=cat.id, round=1, match_number=1,
            participant1_id=pA.id, participant2_id=pB.id, winner_id=pA.id,
            score1="6-4, 4-6, [10-8]", score2="4-6, 6-4, 8-10", status="completed"
        )
        m2 = Match(
            tournament_id=t.id, category_id=cat.id, round=1, match_number=2,
            participant1_id=pA.id, participant2_id=pC.id, winner_id=pA.id,
            score1="6-0, 6-0", score2="0-6, 0-6", status="completed"
        )
        m3 = Match(
            tournament_id=t.id, category_id=cat.id, round=1, match_number=3,
            participant1_id=pB.id, participant2_id=pC.id, winner_id=pB.id,
            score1="50", score2="0", status="completed"
        )
        db.session.add_all([m1, m2, m3])
        db.session.commit()

        RoundRobinFormat.calculate_final_rankings(cat)

        db.session.refresh(pA)
        db.session.refresh(pB)
        db.session.refresh(pC)

        self.assertEqual(pA.group_wins, 2)
        self.assertEqual(pB.group_wins, 1)
        self.assertEqual(pC.group_wins, 0)
        self.assertEqual(pA.final_rank, 1)
        self.assertEqual(pB.final_rank, 2)
        self.assertEqual(pC.final_rank, 3)

    def test_round_robin_2way_tie_head_to_head(self):
        """
        Test that a 2-way tie in wins is resolved by Head-to-Head match result.
        """
        t = Tournament(name="RR H2H Test", url_slug="rr-h2h-test", status="in_progress")
        db.session.add(t)
        db.session.flush()

        cat = Category(tournament_id=t.id, name="RR H2H", format="round_robin", status="in_progress")
        db.session.add(cat)
        db.session.flush()

        p1 = Participant(tournament_id=t.id, category_id=cat.id, name="Player 1")
        p2 = Participant(tournament_id=t.id, category_id=cat.id, name="Player 2")
        p3 = Participant(tournament_id=t.id, category_id=cat.id, name="Player 3")
        p4 = Participant(tournament_id=t.id, category_id=cat.id, name="Player 4")
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        m1 = Match(
            tournament_id=t.id, category_id=cat.id, round=1, match_number=1,
            participant1_id=p1.id, participant2_id=p2.id, winner_id=p1.id,
            score1="6-4, 6-4", status="completed"
        )
        m2 = Match(
            tournament_id=t.id, category_id=cat.id, round=1, match_number=2,
            participant1_id=p1.id, participant2_id=p3.id, winner_id=p1.id,
            score1="6-2, 6-2", status="completed"
        )
        m3 = Match(
            tournament_id=t.id, category_id=cat.id, round=1, match_number=3,
            participant1_id=p1.id, participant2_id=p4.id, winner_id=p4.id,
            score1="4-6, 4-6", status="completed"
        )
        m4 = Match(
            tournament_id=t.id, category_id=cat.id, round=1, match_number=4,
            participant1_id=p2.id, participant2_id=p3.id, winner_id=p2.id,
            score1="6-0, 6-0", status="completed"
        )
        m5 = Match(
            tournament_id=t.id, category_id=cat.id, round=1, match_number=5,
            participant1_id=p2.id, participant2_id=p4.id, winner_id=p2.id,
            score1="6-0, 6-0", status="completed"
        )
        m6 = Match(
            tournament_id=t.id, category_id=cat.id, round=1, match_number=6,
            participant1_id=p3.id, participant2_id=p4.id, winner_id=p3.id,
            score1="6-3, 6-3", status="completed"
        )
        db.session.add_all([m1, m2, m3, m4, m5, m6])
        db.session.commit()

        RoundRobinFormat.calculate_final_rankings(cat)

        db.session.refresh(p1)
        db.session.refresh(p2)

        self.assertEqual(p1.group_wins, 2)
        self.assertEqual(p2.group_wins, 2)
        self.assertTrue(p1.final_rank < p2.final_rank)

    def test_single_elimination_extended_rank_bands(self):
        """
        Test Single Elimination assigns rank 1 (champion), 2 (finalist),
        3 (semi-finalists), and 5 (quarter-finalists).
        """
        t = Tournament(name="SE Test", url_slug="se-test-1", status="in_progress")
        db.session.add(t)
        db.session.flush()

        cat = Category(tournament_id=t.id, name="SE Draw", format="single_elimination", status="in_progress")
        db.session.add(cat)
        db.session.flush()

        participants = [
            Participant(tournament_id=t.id, category_id=cat.id, name=f"Player {i+1}", manual_seed=i+1)
            for i in range(8)
        ]
        db.session.add_all(participants)
        db.session.commit()

        matches_data = SingleEliminationFormat.generate(cat, participants)
        matches = []
        for md in matches_data:
            md['category_id'] = cat.id
            m = Match(**md, tournament_id=t.id)
            db.session.add(m)
            matches.append(m)
        db.session.commit()

        # Play Round 1 (QF, 4 matches)
        r1 = [m for m in matches if m.round == 1]
        for m in r1:
            m.winner_id = m.participant1_id
            m.status = "completed"
            SingleEliminationFormat.advance_match(m, cat, m.winner_id)
        db.session.commit()

        # Play Round 2 (SF, 2 matches)
        r2 = Match.query.filter_by(category_id=cat.id, round=2).all()
        for m in r2:
            m.winner_id = m.participant1_id
            m.status = "completed"
            SingleEliminationFormat.advance_match(m, cat, m.winner_id)
        db.session.commit()

        # Play Round 3 (Final, 1 match)
        final_m = Match.query.filter_by(category_id=cat.id, round=3).first()
        final_m.winner_id = final_m.participant1_id
        final_m.status = "completed"
        db.session.commit()

        SingleEliminationFormat.calculate_final_rankings(cat)

        ranks = {p.name: p.final_rank for p in Participant.query.filter_by(category_id=cat.id).all()}

        self.assertEqual(ranks['Player 1'], 1)
        sf_losers = [p.final_rank for p in participants if p.final_rank == 3]
        self.assertEqual(len(sf_losers), 2)
        qf_losers = [p.final_rank for p in participants if p.final_rank == 5]
        self.assertEqual(len(qf_losers), 4)

    def test_double_elimination_mirrored_mapping(self):
        """
        Test Double Elimination uses mirrored mapping on even Winners rounds.
        Winners Round 2 Match 1 loser should drop to Losers Round 2 Match 2.
        """
        t = Tournament(name="DE Test", url_slug="de-test-1", status="in_progress")
        db.session.add(t)
        db.session.flush()

        cat = Category(tournament_id=t.id, name="DE Draw", format="double_elimination", status="in_progress")
        db.session.add(cat)
        db.session.flush()

        participants = [
            Participant(tournament_id=t.id, category_id=cat.id, name=f"Player {i+1}", manual_seed=i+1)
            for i in range(8)
        ]
        db.session.add_all(participants)
        db.session.commit()

        matches_data = DoubleEliminationFormat.generate(cat, participants)
        for md in matches_data:
            md['category_id'] = cat.id
            m = Match(**md, tournament_id=t.id)
            db.session.add(m)
        db.session.commit()

        w_r2_m1 = Match.query.filter_by(category_id=cat.id, bracket_type='winners', round=2, match_number=1).first()
        w_r2_m1.participant1_id = participants[0].id
        w_r2_m1.participant2_id = participants[1].id
        w_r2_m1.winner_id = participants[0].id
        w_r2_m1.status = "completed"

        DoubleEliminationFormat.advance_match(w_r2_m1, cat, participants[0].id)
        db.session.commit()

        lr2_m2 = Match.query.filter_by(category_id=cat.id, bracket_type='losers', round=2, match_number=2).first()
        self.assertIsNotNone(lr2_m2)
        self.assertEqual(lr2_m2.participant1_id, participants[1].id)

    def test_doubles_round_robin_min_participants(self):
        """Verify Doubles Round Robin minimum participants is 3 pairs."""
        self.assertEqual(DoublesRoundRobinFormat.min_participants, 3)
